"""
Secrets Manager
===============
Loads secrets from AWS Secrets Manager in production.
Falls back to environment variables / .env in development.

Usage:
  In config.py, call load_secrets() at startup to populate
  environment variables from Secrets Manager before Settings() reads them.

AWS Secrets Manager secrets are stored as JSON:
  {
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "OPENAI_API_KEY": "sk-...",
    "SECRET_KEY": "...",
    "DATABASE_URL": "postgresql+asyncpg://...",
    "REDIS_URL": "redis://..."
  }

Environment variable: SECRETS_MANAGER_ARN or SECRETS_MANAGER_SECRET_NAME
"""
import os
import json
import structlog

logger = structlog.get_logger()

# Secrets that should NEVER be in .env files in production
REQUIRED_PRODUCTION_SECRETS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
]


def load_secrets_from_aws() -> dict:
    """
    Fetch secrets from AWS Secrets Manager.
    Returns dict of key-value pairs to inject into environment.
    """
    secret_name = os.environ.get("SECRETS_MANAGER_SECRET_NAME")
    secret_arn = os.environ.get("SECRETS_MANAGER_ARN")
    identifier = secret_arn or secret_name

    if not identifier:
        return {}

    try:
        import boto3
        from botocore.exceptions import ClientError

        region = os.environ.get("AWS_REGION", "ap-south-1")
        client = boto3.client("secretsmanager", region_name=region)

        response = client.get_secret_value(SecretId=identifier)
        secret_string = response.get("SecretString", "{}")
        secrets = json.loads(secret_string)

        logger.info("secrets_loaded_from_aws", count=len(secrets), source=identifier)
        return secrets

    except ImportError:
        logger.warning("boto3_not_installed", msg="Install boto3 for AWS Secrets Manager support")
        return {}
    except Exception as e:
        logger.error("secrets_load_failed", error=str(e), identifier=identifier)
        raise RuntimeError(f"Failed to load secrets from AWS Secrets Manager: {e}") from e


def load_secrets_from_doppler() -> dict:
    """
    Alternative: load from Doppler CLI (doppler run -- python app)
    Doppler injects secrets as environment variables automatically.
    This is a no-op — Doppler handles injection transparently.
    """
    return {}


def load_secrets() -> None:
    """
    Load secrets into environment variables at application startup.
    Call this BEFORE creating the Settings() instance.

    Priority:
      1. AWS Secrets Manager (production)
      2. Doppler (if DOPPLER_TOKEN set)
      3. Environment variables / .env file (development)
    """
    environment = os.environ.get("ENVIRONMENT", "development")

    if environment == "production":
        secrets = load_secrets_from_aws()
        if secrets:
            for key, value in secrets.items():
                os.environ[key] = str(value)
            logger.info("production_secrets_injected", count=len(secrets))
        else:
            # In production, fail loudly if secrets can't be loaded
            # UNLESS all required secrets are already in environment
            missing = [k for k in REQUIRED_PRODUCTION_SECRETS if not os.environ.get(k)]
            if missing:
                raise RuntimeError(
                    f"Production secrets not found. Missing: {missing}. "
                    f"Set SECRETS_MANAGER_SECRET_NAME or SECRETS_MANAGER_ARN."
                )
            logger.info("production_secrets_from_env", msg="Using environment variables directly")
    else:
        # Development: use .env file (already handled by pydantic-settings)
        logger.info("development_mode", msg="Using .env file for secrets")

        # Warn if using default SECRET_KEY
        if os.environ.get("SECRET_KEY", "") in ("", "change-me-in-production"):
            logger.warning(
                "insecure_secret_key",
                msg="SECRET_KEY is not set or is using default value. Set a strong random key."
            )


def validate_production_secrets() -> list[str]:
    """
    Returns list of missing required secrets.
    Call after load_secrets() to validate everything is present.
    """
    return [k for k in REQUIRED_PRODUCTION_SECRETS if not os.environ.get(k)]
