"""Unit Tests for Document Storage Backend."""

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.core.errors import StorageError
from src.core.storage import LocalStorageBackend


@pytest.mark.asyncio
async def test_storage_atomic_write_and_read_back(tmp_path: Path) -> None:
    """Verify atomic write, persistence, and read-back verification."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    test_data = b"%PDF-1.4 Official Manipur Scholarship Guidelines Content %%EOF"
    expected_hash = hashlib.sha256(test_data).hexdigest()
    rel_path = f"documents/{expected_hash[:2]}/{expected_hash}.pdf"

    # 1. Store
    stored_path = await backend.store(rel_path, test_data)
    assert Path(stored_path).exists()
    assert Path(stored_path).is_file()

    # 2. Retrieve
    retrieved = await backend.retrieve(rel_path)
    assert retrieved == test_data
    assert hashlib.sha256(retrieved).hexdigest() == expected_hash

    # 3. Exists
    assert await backend.exists(rel_path) is True


@pytest.mark.asyncio
async def test_storage_immutability_and_idempotency(tmp_path: Path) -> None:
    """Verify stored originals cannot be overwritten with different content."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    data1 = b"%PDF-1.4 Version 1 Content %%EOF"
    rel_path = "documents/test/immutable.pdf"

    # Store first time
    await backend.store(rel_path, data1)

    # Re-storing identical bytes is idempotent
    path2 = await backend.store(rel_path, data1)
    assert Path(path2).exists()

    # Attempting to overwrite with conflicting bytes raises StorageError
    data2 = b"%PDF-1.4 Conflicting Version 2 Content %%EOF"
    with pytest.raises(StorageError, match="Storage conflict"):
        await backend.store(rel_path, data2)

    # Verify original bytes remain unmodified
    assert await backend.retrieve(rel_path) == data1


@pytest.mark.asyncio
async def test_storage_directory_traversal_prevention(tmp_path: Path) -> None:
    """Verify directory traversal attempts outside storage root are blocked."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    malicious_path = "../../../etc/cron.d/malicious.pdf"

    with pytest.raises(StorageError, match="Path traversal"):
        await backend.store(malicious_path, b"%PDF-1.4 Test %%EOF")


@pytest.mark.asyncio
async def test_storage_cleanup_on_verification_failure(tmp_path: Path) -> None:
    """Verify that if read-back verification fails, no orphan file is left."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    test_data = b"%PDF-1.4 Corrupted Test %%EOF"
    rel_path = "documents/test/corrupted.pdf"

    # Mock hashlib.sha256 to simulate read-back mismatch on second call
    real_sha256 = hashlib.sha256

    call_count = 0

    def mock_sha256(data: bytes = b"") -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # read-back check
            mock_obj = real_sha256(b"corrupted_different_bytes")
            return mock_obj
        return real_sha256(data)

    with (
        patch("src.core.storage.hashlib.sha256", side_effect=mock_sha256),
        pytest.raises(StorageError, match="Read-back hash verification failed"),
    ):
        await backend.store(rel_path, test_data)

    # Verify target file does not exist (cleaned up)
    target = tmp_path / rel_path
    assert not target.exists()


@pytest.mark.asyncio
async def test_storage_retrieve_nonexistent_and_delete(tmp_path: Path) -> None:
    """Verify retrieve on non-existent object raises StorageError, and delete removes file."""
    backend = LocalStorageBackend(base_dir=tmp_path)

    with pytest.raises(StorageError, match="File not found"):
        await backend.retrieve("documents/nonexistent.pdf")

    # Store and delete
    await backend.store("documents/to_delete.pdf", b"%PDF-1.4 Delete me %%EOF")
    assert await backend.exists("documents/to_delete.pdf") is True

    await backend.delete("documents/to_delete.pdf")
    assert await backend.exists("documents/to_delete.pdf") is False
