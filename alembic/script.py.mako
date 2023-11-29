"""${message}.

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sql
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    """TODO: Add description here."""
    ${upgrades if upgrades else "pass"}


def downgrade():
    """TODO: Add description here."""
    ${downgrades if downgrades else "pass"}
