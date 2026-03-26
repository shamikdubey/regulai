"""
Billing Endpoints — Phase 5
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from app.db.database import get_db
from app.db.models import User, Tenant, QueryLog
from app.services.auth_service import get_current_user, require_admin
from app.services.billing import PLANS, create_checkout_session, create_billing_portal_session, handle_webhook
from app.core.config import get_settings

router = APIRouter(prefix="/billing", tags=["Billing"])
settings = get_settings()


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = "https://app.regulai.app/billing/success"
    cancel_url: str = "https://app.regulai.app/settings"


@router.get("/plans")
async def list_plans():
    """Return all available plans — public endpoint for pricing page."""
    return {
        slug: {
            "slug": slug,
            "name": plan["name"],
            "price_monthly_usd": plan["price_monthly_usd"],
            "query_limit_per_day": plan["query_limit_per_day"],
            "max_users": plan["max_users"],
            "features": plan["features"],
            "trial_days": 14,
        }
        for slug, plan in PLANS.items()
    }


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(require_admin),
):
    """Create a Stripe checkout session to start or upgrade a subscription."""
    if not settings.ENABLE_BILLING:
        raise HTTPException(503, "Billing not enabled")
    try:
        result = await create_checkout_session(
            tenant_id=str(user.tenant_id),
            user_email=user.email,
            plan_slug=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Billing error: {e}")


@router.post("/portal")
async def billing_portal(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Open Stripe Customer Portal to manage subscription."""
    if not settings.ENABLE_BILLING:
        raise HTTPException(503, "Billing not enabled")

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    stripe_customer_id = (tenant.settings or {}).get("stripe_customer_id")

    if not stripe_customer_id:
        raise HTTPException(400, "No Stripe subscription found. Please subscribe first.")

    url = await create_billing_portal_session(
        stripe_customer_id=stripe_customer_id,
        return_url="https://app.regulai.app/settings",
    )
    return {"portal_url": url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
):
    """Receive Stripe webhook events."""
    payload = await request.body()
    try:
        result = await handle_webhook(payload, stripe_signature)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/usage")
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current usage statistics vs plan limits."""
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()

    # Today's query count
    today_q = await db.execute(
        text("""SELECT COUNT(*) FROM query_logs
                WHERE tenant_id = :tid AND created_at::date = CURRENT_DATE"""),
        {"tid": str(user.tenant_id)},
    )
    today_queries = today_q.scalar() or 0

    # This month's query count
    month_q = await db.execute(
        text("""SELECT COUNT(*) FROM query_logs
                WHERE tenant_id = :tid
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())"""),
        {"tid": str(user.tenant_id)},
    )
    month_queries = month_q.scalar() or 0

    # Document count
    doc_q = await db.execute(
        text("SELECT COUNT(*) FROM documents WHERE tenant_id = :tid"),
        {"tid": str(user.tenant_id)},
    )
    doc_count = doc_q.scalar() or 0

    # User count
    user_q = await db.execute(
        text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid AND is_active = true"),
        {"tid": str(user.tenant_id)},
    )
    user_count = user_q.scalar() or 0

    plan_slug = (tenant.settings or {}).get("plan", "starter")
    plan = PLANS.get(plan_slug, PLANS["starter"])

    return {
        "plan": plan_slug,
        "billing_status": (tenant.settings or {}).get("billing_status", "trial"),
        "usage": {
            "queries_today": today_queries,
            "queries_limit_per_day": tenant.query_limit_per_day,
            "queries_today_pct": round(today_queries / max(tenant.query_limit_per_day, 1) * 100),
            "queries_this_month": month_queries,
            "documents": doc_count,
            "documents_limit": plan.get("max_documents", 999),
            "users": user_count,
            "users_limit": plan.get("max_users", 999),
        },
    }


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Current subscription details."""
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    s = tenant.settings or {}
    plan_slug = s.get("plan", "trial")
    plan = PLANS.get(plan_slug, {})

    return {
        "plan": plan_slug,
        "plan_name": plan.get("name", "Trial"),
        "status": s.get("billing_status", "trial"),
        "stripe_subscription_id": s.get("stripe_subscription_id"),
        "features": plan.get("features", []),
        "limits": {
            "queries_per_day": tenant.query_limit_per_day,
            "max_users": plan.get("max_users"),
            "max_documents": plan.get("max_documents"),
        },
    }
