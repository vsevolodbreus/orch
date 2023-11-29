"""Specifies how migrations are to be run."""

import alembic
import orch.database as database

if alembic.context.is_offline_mode():
    database.run_migrations_offline()
else:
    database.run_migrations_online()
