"""Add officer assignments and user designation."""
from alembic import op
import sqlalchemy as sa

from database.types import GUID

revision = "0002_officer_assignments"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "designation" not in {column["name"] for column in inspector.get_columns("users")}:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("designation", sa.String(length=120), nullable=True))
    if not inspector.has_table("officer_assignments"):
        op.create_table(
            "officer_assignments",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("officer_id", GUID(), nullable=False),
            sa.Column("department", sa.String(length=40), nullable=False),
            sa.Column("property_id", GUID(), nullable=False),
            sa.Column("assigned_by", GUID(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["officer_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("officer_id", "department", "property_id", name="uq_officer_assignment"),
        )
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("officer_assignments")}
    for name, column in [("ix_officer_assignments_officer_id", "officer_id"), ("ix_officer_assignments_department", "department"), ("ix_officer_assignments_property_id", "property_id")]:
        if name not in indexes:
            op.create_index(name, "officer_assignments", [column])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("officer_assignments"):
        op.drop_table("officer_assignments")
    if inspector.has_table("users") and "designation" in {column["name"] for column in inspector.get_columns("users")}:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("designation")