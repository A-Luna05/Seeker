"""Postgres (Neon) checkpointer factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

if TYPE_CHECKING:
    pass

# Neon/serverless Postgres: avoid prepared-statement issues with poolers.
# check: verify connection on checkout (avoids [BAD] after server idle close).
# Shorter max_lifetime / max_idle than defaults to recycle before Neon/proxy drops TCP.
_POOL_KWARGS: dict[str, Any] = {"autocommit": True, "prepare_threshold": None}


class CheckpointerResources:
    """Owns pool lifecycle alongside AsyncPostgresSaver."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        checkpointer: AsyncPostgresSaver,
    ) -> None:
        self.pool = pool
        self.checkpointer = checkpointer

    async def aclose(self) -> None:
        await self.pool.close()


async def create_postgres_checkpointer(
    database_url: str,
    *,
    setup_tables: bool = True,
) -> CheckpointerResources:
    pool = AsyncConnectionPool(
        conninfo=database_url,
        kwargs=_POOL_KWARGS,
        open=False,
        min_size=1,
        max_size=10,
        check=AsyncConnectionPool.check_connection,
        max_lifetime=300.0,
        max_idle=120.0,
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    if setup_tables:
        await checkpointer.setup()
    return CheckpointerResources(pool=pool, checkpointer=checkpointer)
