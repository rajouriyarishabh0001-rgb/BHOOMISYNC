"""Create the BHOOMISYNC normalized schema.

The model metadata is the single source of truth for both PostgreSQL/PostGIS and
SQLite development. Alembic owns this operation in deployed environments.
"""
from alembic import op

from database.base import Base
from models import core, sources

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
