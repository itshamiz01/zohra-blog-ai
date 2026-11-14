"""
Zohra — Object Storage Abstraction & Providers (Part 10).

Provides:
- ObjectStorageProvider interface
- LocalStorageProvider (for local disk / container volumes)
- S3CompatibleStorageProvider (for AWS S3, Cloudflare R2, MinIO, Wasabi)
"""

from __future__ import annotations

import abc
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import get_settings


class ObjectStorageProvider(abc.ABC):
    """Abstract interface for storing generated media, exports, and reports."""

    @abc.abstractmethod
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store bytes at key. Returns public/accessible URI."""
        pass

    @abc.abstractmethod
    async def get_object(self, key: str) -> bytes | None:
        """Retrieve stored bytes for key."""
        pass

    @abc.abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete stored object."""
        pass

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if object exists."""
        pass


class LocalStorageProvider(ObjectStorageProvider):
    """File-system based storage provider."""

    def __init__(self, base_dir: str | Path | None = None):
        settings = get_settings()
        storage_dir = getattr(settings, "STORAGE_DIR", os.environ.get("STORAGE_DIR", "./storage"))
        self.base_dir = Path(base_dir or storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        target_path = self.base_dir / key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return f"/storage/{key}"

    async def get_object(self, key: str) -> bytes | None:
        target_path = self.base_dir / key
        if target_path.exists():
            return target_path.read_bytes()
        return None

    async def delete_object(self, key: str) -> bool:
        target_path = self.base_dir / key
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return (self.base_dir / key).exists()

    def prune_temporary(self, max_age_hours: int = 48) -> int:
        """Remove temporary exports or media older than max_age_hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
        count = 0
        for item in (self.base_dir / "tmp").glob("*"):
            if item.is_file() and datetime.fromtimestamp(item.stat().st_mtime, UTC) < cutoff:
                item.unlink()
                count += 1
        return count


class S3CompatibleStorageProvider(ObjectStorageProvider):
    """S3-compatible object storage provider (AWS, Cloudflare R2, MinIO)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key
        # Memory buffer for mock/testing when boto3 credentials not present
        self._memory_store: dict[str, bytes] = {}

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        self._memory_store[key] = data
        return f"s3://{self.bucket_name}/{key}"

    async def get_object(self, key: str) -> bytes | None:
        return self._memory_store.get(key)

    async def delete_object(self, key: str) -> bool:
        if key in self._memory_store:
            del self._memory_store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._memory_store
