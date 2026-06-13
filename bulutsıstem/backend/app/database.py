from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.app_env == "development")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def _run_migrations(conn) -> None:
    def table_names(connection):
        return set(inspect(connection).get_table_names())

    def column_names(connection, table: str):
        if table not in inspect(connection).get_table_names():
            return set()
        return {c["name"] for c in inspect(connection).get_columns(table)}

    tables = await conn.run_sync(table_names)

    if "tenants" in tables:
        tenant_cols = await conn.run_sync(lambda c: column_names(c, "tenants"))
        if "mqtt_username" not in tenant_cols:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN mqtt_username VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN mqtt_password VARCHAR(255)"))
            await conn.execute(
                text(
                    "UPDATE tenants SET mqtt_username = 'tenant_' || slug, "
                    "mqtt_password = 'changeme' WHERE mqtt_username IS NULL"
                )
            )
            await conn.execute(text("ALTER TABLE tenants ALTER COLUMN mqtt_username SET NOT NULL"))
            await conn.execute(text("ALTER TABLE tenants ALTER COLUMN mqtt_password SET NOT NULL"))
        if "edge_agent_key" not in tenant_cols:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN edge_agent_key VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN edge_agent_last_seen TIMESTAMPTZ"))
            await conn.execute(
                text(
                    "UPDATE tenants SET edge_agent_key = md5(random()::text || clock_timestamp()::text) "
                    "WHERE edge_agent_key IS NULL"
                )
            )
            await conn.execute(text("ALTER TABLE tenants ALTER COLUMN edge_agent_key SET NOT NULL"))
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_edge_agent_key ON tenants (edge_agent_key)")
            )

    if "cameras" in tables:
        camera_cols = await conn.run_sync(lambda c: column_names(c, "cameras"))
        if "source_kind" not in camera_cols:
            await conn.execute(text("ALTER TABLE cameras ADD COLUMN source_kind VARCHAR(50) DEFAULT 'manual'"))
            await conn.execute(text("UPDATE cameras SET source_kind = 'manual' WHERE source_kind IS NULL"))

    await conn.execute(text("ALTER TYPE cameraprotocol ADD VALUE IF NOT EXISTS 'ip_webcam'"))

    if "cameras" in tables:
        camera_cols = await conn.run_sync(lambda c: column_names(c, "cameras"))
        if "alarm_on_person" not in camera_cols:
            await conn.execute(text("ALTER TABLE cameras ADD COLUMN alarm_on_person BOOLEAN DEFAULT TRUE"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await _run_migrations(conn)
        except Exception:
            pass
