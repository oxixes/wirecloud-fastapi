from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context

from src.wirecloud.database import get_db_url
from settings import INSTALLED_APPS
from os import path

import asyncio

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Set the database URL
config.set_main_option("sqlalchemy.url", get_db_url())

# Set the versions directories. Each installed app can have its own versions directory called 'migrations', which we
# need to add to the Alembic configuration.
versions_directories = []
for app in INSTALLED_APPS:
    versions_directory = path.join(path.dirname(path.dirname(__file__)), app.replace('.', '/'), 'migrations')
    versions_directories.append(versions_directory)

# https://github.com/sqlalchemy/alembic/issues/570#issuecomment-498269649
context.script.__dict__.pop('_version_locations', None)
context.script.version_locations = versions_directories


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        def run_migrations(conn) -> None:
            context.configure(connection=conn, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()

        await connection.run_sync(run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
