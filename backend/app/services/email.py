"""
Email Service — Phase 5
========================
Sends transactional emails via AWS SES.
Falls back to console logging in development.

Templates:
  - Welcome / email verification
  - Password reset
  - Alert notification digest
  - API key created notification
  - Billing / invoice (Phase 5)
"""
import structlog
from datetime import datetime, timezone
from typing import Optional
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# ── Base templates ────────────────────────────────────────────────────────────

def _html_wrapper(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 0; background: #f4f4f4; font-family: 'Helvetica Neue', Arial, sans-serif; }}
    .container {{ max-width: 560px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .header {{ background: #0a0c10; padding: 32px 40px; text-align: center; }}
    .logo {{ display: inline-block; background: #00d4aa; color: #000; font-weight: bold; font-size: 18px; font-family: monospace; width: 48px; height: 48px; line-height: 48px; border-radius: 10px; margin-bottom: 12px; }}
    .header h1 {{ color: #e8ecf2; font-size: 20px; font-weight: 600; margin: 0; }}
    .body {{ padding: 40px; color: #333; line-height: 1.6; }}
    .body p {{ margin: 0 0 16px; font-size: 15px; }}
    .btn {{ display: inline-block; background: #00d4aa; color: #000; font-weight: bold; font-size: 14px; padding: 14px 32px; border-radius: 8px; text-decoration: none; margin: 8px 0 24px; }}
    .code {{ background: #f4f4f4; border-left: 4px solid #00d4aa; padding: 12px 16px; font-family: monospace; font-size: 16px; border-radius: 4px; margin: 16px 0; letter-spacing: 2px; }}
    .footer {{ background: #f9f9f9; padding: 24px 40px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
    .footer a {{ color: #00d4aa; text-decoration: none; }}
    .warning {{ background: #fff8e8; border: 1px solid #f5a623; border-radius: 8px; padding: 12px 16px; margin: 16px 0; font-size: 13px; color: #856404; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">R∧</div>
      <h1>RegulAI</h1>
    </div>
    <div class="body">{body}</div>
    <div class="footer">
      <p>RegulAI · Global Regulatory Compliance AI</p>
      <p><a href="{{unsubscribe_url}}">Unsubscribe</a> · <a href="https://regulai.app/privacy">Privacy Policy</a></p>
      <p style="margin-top:8px;font-size:11px;color:#ccc;">
        This email was sent to {{recipient_email}}. If you did not expect this, please ignore it.
      </p>
    </div>
  </div>
</body>
</html>"""


# ── Email sender ──────────────────────────────────────────────────────────────

async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send an email. Uses SES in production, logs to console in dev.
    Returns True on success.
    """
    if not settings.is_production:
        # Dev: log to console instead of sending
        logger.info(
            "email_dev_mode",
            to=to,
            subject=subject,
            preview=html_body[:200].replace("\n", " ").replace("  ", " "),
        )
        return True

    ses_region = getattr(settings, "SES_REGION", settings.AWS_REGION)
    ses_from = getattr(settings, "SES_FROM_EMAIL", "noreply@regulai.app")

    try:
        import boto3
        ses = boto3.client("ses", region_name=ses_region)

        body = {"Html": {"Data": html_body, "Charset": "UTF-8"}}
        if text_body:
            body["Text"] = {"Data": text_body, "Charset": "UTF-8"}

        ses.send_email(
            Source=f"RegulAI <{ses_from}>",
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        )
        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", to=to, subject=subject, error=str(e))
        return False


# ── Email templates ───────────────────────────────────────────────────────────

async def send_welcome_email(email: str, full_name: str, tenant_name: str) -> bool:
    body = _html_wrapper("Welcome to RegulAI", f"""
<p>Hi {full_name},</p>
<p>Welcome to <strong>RegulAI</strong> — your AI-powered global regulatory compliance platform.</p>
<p>Your workspace <strong>{tenant_name}</strong> is ready. You can now:</p>
<ul style="margin:0 0 16px;padding-left:20px;font-size:15px;">
  <li>Ask compliance questions across 110 countries and 5 regulatory domains</li>
  <li>Run multi-jurisdiction gap assessments</li>
  <li>Draft regulatory dossiers and submissions</li>
  <li>Track regulatory alerts and changes</li>
</ul>
<p><a href="https://app.regulai.app" class="btn">Open RegulAI →</a></p>
<p>If you have questions, reply to this email or contact <a href="mailto:support@regulai.app">support@regulai.app</a>.</p>
""")
    return await send_email(email, "Welcome to RegulAI", body)


async def send_password_reset_email(email: str, full_name: str, reset_token: str) -> bool:
    reset_url = f"https://app.regulai.app/reset-password?token={reset_token}"
    body = _html_wrapper("Reset your RegulAI password", f"""
<p>Hi {full_name},</p>
<p>We received a request to reset your RegulAI password. Click the button below to set a new password.</p>
<p><a href="{reset_url}" class="btn">Reset Password →</a></p>
<div class="warning">
  ⚠ This link expires in <strong>1 hour</strong>. If you did not request a password reset, ignore this email — your account is safe.
</div>
<p>If the button doesn't work, copy and paste this URL:</p>
<p style="font-size:12px;color:#666;word-break:break-all;">{reset_url}</p>
""")
    return await send_email(email, "Reset your RegulAI password", body)


async def send_invite_email(
    email: str,
    full_name: str,
    tenant_name: str,
    temporary_password: str,
    invited_by: str,
) -> bool:
    body = _html_wrapper("You've been invited to RegulAI", f"""
<p>Hi {full_name},</p>
<p><strong>{invited_by}</strong> has invited you to join <strong>{tenant_name}</strong> on RegulAI.</p>
<p>Sign in with your temporary password:</p>
<div class="code">{temporary_password}</div>
<p><a href="https://app.regulai.app/login" class="btn">Sign in →</a></p>
<div class="warning">
  ⚠ You will be prompted to change your password on first login. Keep this email confidential.
</div>
<p>Your email: <strong>{email}</strong></p>
""")
    return await send_email(email, f"You've been invited to {tenant_name} on RegulAI", body)


async def send_verification_email(email: str, full_name: str, token: str) -> bool:
    verify_url = f"https://app.regulai.app/verify-email?token={token}"
    body = _html_wrapper("Verify your email address", f"""
<p>Hi {full_name},</p>
<p>Please verify your email address to complete your RegulAI account setup.</p>
<p><a href="{verify_url}" class="btn">Verify Email →</a></p>
<p>This link expires in 24 hours.</p>
""")
    return await send_email(email, "Verify your RegulAI email address", body)


async def send_alert_digest_email(
    email: str,
    full_name: str,
    alerts: list[dict],
    period: str = "weekly",
) -> bool:
    alert_items = "".join(
        f"""<div style="border-left:3px solid {'#ff4757' if a.get('severity')=='critical' else '#f5a623' if a.get('severity')=='high' else '#00d4aa'};padding:10px 16px;margin:8px 0;background:#f9f9f9;border-radius:4px;">
          <strong style="font-size:14px;">{a.get('title','Alert')}</strong><br>
          <span style="font-size:12px;color:#666;">{a.get('jurisdiction','').upper()} · {a.get('domain','').capitalize()} · {a.get('severity','').upper()}</span><br>
          <span style="font-size:13px;color:#333;">{a.get('summary','')[:200]}</span>
        </div>"""
        for a in alerts[:10]
    )
    body = _html_wrapper(f"Your {period} regulatory alert digest", f"""
<p>Hi {full_name},</p>
<p>Here are your <strong>{len(alerts)} regulatory alert{'s' if len(alerts) != 1 else ''}</strong> for this {period}:</p>
{alert_items}
{"<p><em>… and more. Log in to see all alerts.</em></p>" if len(alerts) > 10 else ""}
<p><a href="https://app.regulai.app/alerts" class="btn">View All Alerts →</a></p>
""")
    return await send_email(email, f"Your {period} regulatory digest — {len(alerts)} update{'s' if len(alerts)!=1 else ''}", body)


async def send_api_key_created_email(
    email: str,
    full_name: str,
    key_name: str,
    key_prefix: str,
) -> bool:
    body = _html_wrapper("API key created", f"""
<p>Hi {full_name},</p>
<p>A new API key was created for your RegulAI account:</p>
<div class="code">{key_prefix}••••••••</div>
<p><strong>Name:</strong> {key_name}</p>
<div class="warning">
  ⚠ If you did not create this API key, revoke it immediately in <a href="https://app.regulai.app/settings">Settings → API Keys</a> and contact support.
</div>
""")
    return await send_email(email, "New API key created on RegulAI", body)
