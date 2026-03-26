"""
Document Storage Service
=========================
Handles tenant-isolated document storage.
  - Production: AWS S3 with tenant-scoped paths + presigned URLs
  - Development: Local filesystem with tenant-scoped directories

S3 path structure:  documents/{tenant_id}/{document_id}/{filename}
                    ─────────────────────────────────────────────
                    ↑ No cross-tenant access is possible at S3 level.
                    Even if someone guesses another tenant's document_id,
                    their tenant_id prefix will not match, and the presigned
                    URL will not grant access.

Security properties:
  1. Tenant isolation enforced at S3 key prefix level
  2. Presigned URLs expire (default 3600s) — no permanent links
  3. Bucket policy blocks public access entirely
  4. S3 server-side encryption (SSE-S3 or SSE-KMS) at rest
  5. Bucket versioning enabled — accidental deletes are recoverable
"""
import os
import uuid
import structlog
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class DocumentStorageService:
    """
    Tenant-isolated document storage.
    Transparently switches between S3 (production) and local (development).
    """

    # ── S3 operations ─────────────────────────────────────────────────────────

    def _get_s3_client(self):
        try:
            import boto3
            return boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
            )
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")

    async def upload_to_s3(
        self,
        file: UploadFile,
        tenant_id: str,
        document_id: str,
    ) -> Tuple[str, int]:
        """
        Upload a file to S3 with tenant-scoped path.
        Returns (s3_key, file_size_bytes).
        """
        s3_key = settings.get_s3_document_key(
            tenant_id=tenant_id,
            document_id=document_id,
            filename=file.filename or "document",
        )

        content = await file.read()
        file_size = len(content)

        # Enforce upload size limit
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB} MB",
            )

        s3 = self._get_s3_client()
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
            # Server-side encryption
            ServerSideEncryption="AES256",
            # Metadata for audit trail
            Metadata={
                "tenant-id": tenant_id,
                "document-id": document_id,
                "original-filename": file.filename or "unknown",
            },
        )

        logger.info(
            "document_uploaded_s3",
            tenant_id=tenant_id,
            document_id=document_id,
            s3_key=s3_key,
            size_bytes=file_size,
        )

        return s3_key, file_size

    def get_presigned_url(
        self,
        s3_key: str,
        tenant_id: str,
        expiry_seconds: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for secure document download.
        Validates that the key belongs to the requesting tenant.
        """
        # CRITICAL: Verify the key starts with the tenant's prefix
        expected_prefix = f"{settings.AWS_S3_BUCKET_PREFIX}/{tenant_id}/"
        if not s3_key.startswith(expected_prefix):
            logger.error(
                "cross_tenant_access_attempt",
                s3_key=s3_key,
                tenant_id=tenant_id,
                expected_prefix=expected_prefix,
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: document does not belong to your organisation",
            )

        s3 = self._get_s3_client()
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )
        return url

    async def delete_from_s3(self, s3_key: str, tenant_id: str) -> None:
        """Delete a document from S3 (for GDPR right-to-erasure)."""
        # Verify tenant ownership before deletion
        expected_prefix = f"{settings.AWS_S3_BUCKET_PREFIX}/{tenant_id}/"
        if not s3_key.startswith(expected_prefix):
            raise HTTPException(status_code=403, detail="Access denied")

        s3 = self._get_s3_client()
        s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
        logger.info("document_deleted_s3", s3_key=s3_key, tenant_id=tenant_id)

    async def delete_all_tenant_documents(self, tenant_id: str) -> int:
        """
        Delete ALL documents for a tenant.
        Called during GDPR right-to-erasure / tenant offboarding.
        Returns count of objects deleted.
        """
        prefix = f"{settings.AWS_S3_BUCKET_PREFIX}/{tenant_id}/"
        s3 = self._get_s3_client()

        deleted = 0
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
            objects = page.get("Contents", [])
            if objects:
                s3.delete_objects(
                    Bucket=settings.AWS_S3_BUCKET,
                    Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
                )
                deleted += len(objects)

        logger.info("tenant_documents_deleted", tenant_id=tenant_id, count=deleted)
        return deleted

    # ── Local filesystem operations (development) ─────────────────────────────

    async def save_local(
        self,
        file: UploadFile,
        tenant_id: str,
        document_id: str,
    ) -> Tuple[str, int]:
        """Save document to local filesystem with tenant isolation."""
        tenant_dir = Path(settings.UPLOAD_DIR) / tenant_id / document_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = "".join(
            c if c.isalnum() or c in (".", "-", "_") else "_"
            for c in (file.filename or "document")
        )
        local_path = tenant_dir / safe_filename

        content = await file.read()
        file_size = len(content)

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB} MB",
            )

        with open(local_path, "wb") as f:
            f.write(content)

        logger.info(
            "document_saved_local",
            path=str(local_path),
            tenant_id=tenant_id,
            size=file_size,
        )

        return str(local_path), file_size

    def get_local_path(self, file_path: str, tenant_id: str) -> Path:
        """Get local file path, validating it belongs to the tenant."""
        path = Path(file_path)
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        tenant_root = (upload_root / tenant_id).resolve()

        # Ensure the path is within the tenant's directory (prevent path traversal)
        try:
            path.resolve().relative_to(tenant_root)
        except ValueError:
            logger.error(
                "path_traversal_attempt",
                file_path=file_path,
                tenant_id=tenant_id,
            )
            raise HTTPException(status_code=403, detail="Access denied")

        return path

    # ── Unified interface (dispatches to S3 or local) ─────────────────────────

    async def store(
        self,
        file: UploadFile,
        tenant_id: str,
        document_id: Optional[str] = None,
    ) -> Tuple[str, int]:
        """Store a document. Returns (file_path_or_s3_key, file_size_bytes)."""
        doc_id = document_id or str(uuid.uuid4())

        if settings.use_s3:
            return await self.upload_to_s3(file, tenant_id, doc_id)
        else:
            return await self.save_local(file, tenant_id, doc_id)

    def get_file_bytes(self, file_path: str, tenant_id: str) -> bytes:
        """Read file bytes — handles both S3 and local."""
        if settings.use_s3:
            s3 = self._get_s3_client()
            # Verify tenant ownership
            expected_prefix = f"{settings.AWS_S3_BUCKET_PREFIX}/{tenant_id}/"
            if not file_path.startswith(expected_prefix):
                raise HTTPException(status_code=403, detail="Access denied")
            response = s3.get_object(Bucket=settings.AWS_S3_BUCKET, Key=file_path)
            return response["Body"].read()
        else:
            local_path = self.get_local_path(file_path, tenant_id)
            return local_path.read_bytes()


# Singleton
storage = DocumentStorageService()
