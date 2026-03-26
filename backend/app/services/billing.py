"""
Billing Service — Phase 5 (Stripe)
====================================
Manages SaaS subscriptions using Stripe.

Plans:
  starter   — 500 queries/day, 1 user, $49/month
  growth    — 2000 queries/day, 5 users, $149/month
  business  — 10000 queries/day, 20 users, $499/month
  enterprise — unlimited, custom users, custom pricing

Integration points:
  - POST /billing/checkout    — create Stripe checkout session
  - POST /billing/portal      — Stripe customer portal (manage subscription)
  - POST /billing/webhook     — Stripe webhook handler
  - GET  /billing/usage       — current usage vs limits
  - GET  /billing/subscription — current plan details
"""
import structlog
from typing import Optional
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly_usd": 49,
        "query_limit_per_day": 500,
        "max_users": 1,
        "max_documents": 10,
        "features": ["AI Query", "Gap Assessment", "Reference Data", "Email alerts"],
        "stripe_price_id": "price_starter_monthly",
    },
    "growth": {
        "name": "Growth",
        "price_monthly_usd": 149,
        "query_limit_per_day": 2000,
        "max_users": 5,
        "max_documents": 50,
        "features": ["Everything in Starter", "Dossier Drafting", "API Access", "Priority support"],
        "stripe_price_id": "price_growth_monthly",
    },
    "business": {
        "name": "Business",
        "price_monthly_usd": 499,
        "query_limit_per_day": 10000,
        "max_users": 20,
        "max_documents": 500,
        "features": ["Everything in Growth", "Custom jurisdiction packs", "SSO (Auth0)", "SLA guarantee"],
        "stripe_price_id": "price_business_monthly",
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly_usd": None,  # Custom pricing
        "query_limit_per_day": 999999,
        "max_users": 999999,
        "max_documents": 999999,
        "features": ["Unlimited queries", "Unlimited users", "Private deployment option", "Dedicated CSM"],
        "stripe_price_id": "price_enterprise_monthly",
    },
}


def get_stripe():
    """Get Stripe client — lazy init."""
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")
    try:
        import stripe
        stripe.api_key = stripe_key
        return stripe
    except ImportError:
        raise RuntimeError("stripe not installed — pip install stripe")


async def create_checkout_session(
    tenant_id: str,
    user_email: str,
    plan_slug: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Stripe Checkout session for a new subscription."""
    plan = PLANS.get(plan_slug)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_slug}")

    try:
        stripe = get_stripe()
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=user_email,
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id, "plan": plan_slug},
            subscription_data={
                "metadata": {"tenant_id": tenant_id, "plan": plan_slug},
                "trial_period_days": 14,   # 14-day free trial
            },
        )
        logger.info("checkout_created", tenant_id=tenant_id, plan=plan_slug)
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error("checkout_failed", error=str(e))
        raise


async def create_billing_portal_session(
    stripe_customer_id: str,
    return_url: str,
) -> str:
    """Create a Stripe Customer Portal session for subscription management."""
    stripe = get_stripe()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Handle Stripe webhook events.
    Called by POST /billing/webhook.
    """
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured")

    stripe = get_stripe()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("stripe_webhook", event_type=event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(data)

    return {"received": True, "event_type": event_type}


async def _handle_checkout_completed(session: dict):
    """Activate subscription after successful checkout."""
    from app.db.database import AsyncSessionLocal
    from app.db.models import Tenant
    from sqlalchemy import select, text
    import uuid

    tenant_id = session.get("metadata", {}).get("tenant_id")
    plan_slug = session.get("metadata", {}).get("plan", "starter")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not tenant_id:
        return

    plan = PLANS.get(plan_slug, PLANS["starter"])

    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.bypass_rls', 'on', TRUE)"))
        result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
        tenant = result.scalar_one_or_none()
        if tenant:
            tenant.query_limit_per_day = plan["query_limit_per_day"]
            settings_dict = tenant.settings or {}
            settings_dict.update({
                "plan": plan_slug,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "billing_status": "active",
            })
            tenant.settings = settings_dict
            await db.commit()
            logger.info("subscription_activated", tenant_id=tenant_id, plan=plan_slug)


async def _handle_subscription_updated(subscription: dict):
    """Update plan limits when subscription changes."""
    tenant_id = subscription.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return
    # Update tenant limits based on new plan
    logger.info("subscription_updated", tenant_id=tenant_id, status=subscription.get("status"))


async def _handle_subscription_cancelled(subscription: dict):
    """Downgrade to free tier on cancellation."""
    tenant_id = subscription.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return
    logger.info("subscription_cancelled", tenant_id=tenant_id)
    # Reset to free limits


async def _handle_payment_failed(invoice: dict):
    """Notify tenant of payment failure."""
    logger.warning("payment_failed", customer=invoice.get("customer"))
    # Send payment failure email


async def _handle_invoice_paid(invoice: dict):
    """Log successful payment."""
    logger.info("invoice_paid", amount=invoice.get("amount_paid"), customer=invoice.get("customer"))
