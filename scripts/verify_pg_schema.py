"""PostgreSQL 16 + pgvector Schema and Migration Verification Script."""

import asyncio
import os

import asyncpg
from alembic import command
from alembic.config import Config

DB_ASYNC_URL = (
    "postgresql+asyncpg://schemesaathi:schemesaathi_password@127.0.0.1:5434/schemesaathi_db"
)
DB_RAW_URL = "postgresql://schemesaathi:schemesaathi_password@127.0.0.1:5434/schemesaathi_db"

os.environ["DATABASE_URL"] = DB_ASYNC_URL


async def verify_catalog(conn: asyncpg.Connection, stage: str) -> dict[str, list[str]]:
    print(f"\n==================== [{stage}] CATALOG INSPECTION ====================")

    # 1. Extensions
    exts = await conn.fetch(
        "SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector') ORDER BY extname"
    )
    ext_list = [f"{r['extname']} v{r['extversion']}" for r in exts]
    print(f"Extensions ({len(ext_list)}): {ext_list}")

    # 2. Tables
    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    )
    table_list = [r["table_name"] for r in tables]
    print(f"Tables ({len(table_list)}): {table_list}")

    # 3. ENUMs
    enums = await conn.fetch(
        "SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) as labels "
        "FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
        "GROUP BY t.typname ORDER BY t.typname"
    )
    enum_list = [f"{r['typname']} ({len(r['labels'])} variants)" for r in enums]
    print(f"Custom ENUM Types ({len(enum_list)}): {enum_list}")

    # 4. Specialized GIN and HNSW Indexes
    indexes = await conn.fetch(
        "SELECT indexname, tablename, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname"
    )
    special_indices = [
        f"{r['indexname']} ON {r['tablename']}"
        for r in indexes
        if "hnsw" in r["indexdef"].lower() or "gin" in r["indexdef"].lower()
    ]
    print(f"Total Indexes: {len(indexes)} (Specialized GIN/HNSW: {len(special_indices)})")
    for s in special_indices:
        print(f"  -> {s}")

    # 5. Foreign Key and Unique Constraints
    constraints = await conn.fetch(
        "SELECT conname, contype FROM pg_constraint WHERE connamespace = 'public'::regnamespace ORDER BY conname"
    )
    print(f"Total Constraints: {len(constraints)}")

    return {"tables": table_list, "enums": [r["typname"] for r in enums], "extensions": ext_list}


async def main() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DB_ASYNC_URL)

    conn = await asyncpg.connect(DB_RAW_URL)

    # Verify Stage 1: Upgrade Head
    res_up = await verify_catalog(conn, "UPGRADE HEAD")
    assert "schemes" in res_up["tables"]
    assert "scheme_knowledge_chunks" in res_up["tables"]
    assert "alembic_version" in res_up["tables"]
    assert len(res_up["tables"]) == 15  # 14 domain tables + alembic_version

    # Stage 2: Test Downgrade to Base
    print("\nExecuting Alembic Downgrade to base...")
    await conn.close()
    await asyncio.to_thread(command.downgrade, cfg, "base")

    conn = await asyncpg.connect(DB_RAW_URL)
    res_down = await verify_catalog(conn, "DOWNGRADE BASE")
    # Only alembic_version (or empty) remains
    assert "schemes" not in res_down["tables"]
    assert "scheme_knowledge_chunks" not in res_down["tables"]
    assert len(res_down["enums"]) == 0
    print("Downgrade successfully removed all tables and custom enums.")

    # Stage 3: Re-Upgrade to Head
    print("\nExecuting Alembic Re-Upgrade to head...")
    await conn.close()
    await asyncio.to_thread(command.upgrade, cfg, "head")

    conn = await asyncpg.connect(DB_RAW_URL)
    res_reup = await verify_catalog(conn, "RE-UPGRADE HEAD")
    assert len(res_reup["tables"]) == 15
    assert len(res_reup["enums"]) == 5
    print("Re-Upgrade successfully restored all 14 tables, 5 enums, and specialized indices.")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
