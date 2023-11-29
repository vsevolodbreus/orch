"""Initial tables

Revision ID: c9066a753b93
Create Date: 2020-06-15 15:50:36.060398
"""

import sqlalchemy as sql
import sqlalchemy.dialects.postgresql as psql

from alembic import op

revision = "c9066a753b93"
down_revision = None
branch_labels = None
depends_on = None


status_codes = ("PENDING", "SUCCESS", "FAILURE", "BLOCKED")
task_status = psql.ENUM(*status_codes, name="task_status")


def upgrade():
    """Add flow, task tables."""
    op.create_table(
        "flows",
        sql.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sql.Column("name", sql.String, nullable=False, index=True),
        sql.Column(
            "created_at",
            sql.DateTime(),
            nullable=False,
            server_default=sql.text("now()"),
            index=True,
        ),
        sql.Column("args", psql.JSONB, nullable=False, server_default="{}"),
        sql.Column("priority", sql.Integer, nullable=False, index=True),
        sql.Column("webhook_url", sql.String, nullable=True),
    )

    op.create_table(
        "tasks",
        sql.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sql.Column("flow_id", psql.UUID, nullable=False, index=True),
        sql.Column("name", sql.String, nullable=False, index=True),
        sql.Column(
            "status",
            sql.Enum(*status_codes, name="task_status", create_type=False),
            nullable=False,
            server_default="SUCCESS",
        ),
        sql.Column("started_at", sql.DateTime(), nullable=True, index=True),
        sql.Column(
            "updated_at",
            sql.DateTime(),
            nullable=False,
            server_default=sql.text("now()"),
            index=True,
        ),
        sql.Column("finished_at", sql.DateTime(), nullable=True, index=True),
        sql.Column("args", psql.JSONB, nullable=False, server_default="{}"),
        sql.Column("output", psql.JSONB, nullable=False, server_default="{}"),
        sql.Column("ordering", sql.Integer, nullable=False, index=True),
    )

    op.create_foreign_key(None, "tasks", "flows", ["flow_id"], ["id"])
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)

    # TODO: fix adding task_status data type twice upon init
    try:
        task_status.create(op.get_bind())
    except:
        pass


def downgrade():
    """Drop flow, task tables"""
    op.drop_table("tasks")
    op.drop_table("flows")
    task_status.drop(op.get_bind())
