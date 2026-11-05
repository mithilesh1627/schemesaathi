"""Storage Abstraction and Local Filesystem Implementation."""

import hashlib
import os
import uuid
from pathlib import Path
from typing import Protocol

from src.core.config import settings
from src.core.errors import StorageError
from src.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(Protocol):
    """Storage interface for immutable policy document artifacts."""

    async def store(self, rel_path: str, data: bytes) -> str:
        """Store bytes atomically at rel_path and verify SHA-256 upon read-back.

        Returns the resolved storage path.
        Raises StorageError if storage or verification fails.
        """
        ...

    async def retrieve(self, rel_path: str) -> bytes:
        """Retrieve stored bytes for rel_path.

        Raises StorageError if file does not exist.
        """
        ...

    async def exists(self, rel_path: str) -> bool:
        """Check if an object exists at rel_path."""
        ...

    async def delete(self, rel_path: str) -> None:
        """Delete object at rel_path if it exists."""
        ...


class LocalStorageBackend:
    """Local filesystem storage backend with atomic writes and read-back verification."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_BASE_DIR).resolve()

    def _resolve_safe_path(self, rel_path: str) -> Path:
        """Resolve rel_path ensuring no directory traversal outside base_dir."""
        clean_rel = Path(rel_path)
        if clean_rel.is_absolute():
            clean_rel = Path(*clean_rel.parts[1:])
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise StorageError(f"Path traversal attempt detected: {rel_path}")
        return target

    async def store(self, rel_path: str, data: bytes) -> str:
        """Persist data atomically, verifying read-back SHA-256 before returning.

        Originals are immutable: if file already exists with identical bytes, it is retained.
        If file exists with conflicting bytes, an error is raised.
        Atomic write uses a sibling temp file + rename to prevent partial writes.
        """
        target = self._resolve_safe_path(rel_path)
        expected_hash = hashlib.sha256(data).hexdigest()

        # Check immutability
        if target.exists():
            existing_data = target.read_bytes()
            existing_hash = hashlib.sha256(existing_data).hexdigest()
            if existing_hash == expected_hash:
                logger.info("Storage object already exists with identical hash: %s", rel_path)
                return str(target)
            raise StorageError(
                f"Storage conflict: file at {rel_path} already exists with different content."
            )

        # Ensure parent directories exist
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Failed to create directory {target.parent}: {exc}") from exc

        # Create temporary file in the same directory (guarantees same filesystem for atomic rename)
        tmp_target = target.with_name(f"{target.name}.tmp.{uuid.uuid4().hex}")
        try:
            with open(tmp_target, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename / replace
            tmp_target.replace(target)

            # Read-back verification
            read_back_data = target.read_bytes()
            read_back_hash = hashlib.sha256(read_back_data).hexdigest()
            if read_back_hash != expected_hash:
                target.unlink(missing_ok=True)
                raise StorageError(
                    f"Read-back hash verification failed for {rel_path}. "
                    f"Expected {expected_hash}, got {read_back_hash}."
                )

            logger.info(
                "Stored and verified document artifact: %s (bytes=%d, sha256=%s)",
                rel_path,
                len(data),
                expected_hash,
            )
            return str(target)
        except Exception as exc:
            # Clean up temporary or corrupted target file so no orphan remains
            if tmp_target.exists():
                tmp_target.unlink(missing_ok=True)
            if target.exists():
                target.unlink(missing_ok=True)
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Storage write failed for {rel_path}: {exc}") from exc

    async def retrieve(self, rel_path: str) -> bytes:
        target = self._resolve_safe_path(rel_path)
        if not target.exists():
            raise StorageError(f"File not found in storage: {rel_path}")
        return target.read_bytes()

    async def exists(self, rel_path: str) -> bool:
        target = self._resolve_safe_path(rel_path)
        return target.exists()

    async def delete(self, rel_path: str) -> None:
        target = self._resolve_safe_path(rel_path)
        if target.exists():
            target.unlink(missing_ok=True)


_default_storage_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    """Return default storage backend singleton."""
    global _default_storage_backend
    if _default_storage_backend is None:
        _default_storage_backend = LocalStorageBackend()
    return _default_storage_backend
