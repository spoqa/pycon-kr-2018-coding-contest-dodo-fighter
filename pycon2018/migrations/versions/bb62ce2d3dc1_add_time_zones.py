"""Add time zones

Revision ID: bb62ce2d3dc1
Revises: 1dde4cf949df
Create Date: 2018-08-19 11:15:10.599279

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import DateTime


# revision identifiers, used by Alembic.
revision = 'bb62ce2d3dc1'
down_revision = '1dde4cf949df'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('tournament', 'begin_at', type_=DateTime(timezone=True))
    op.alter_column('tournament', 'finish_at', type_=DateTime(timezone=True))
    op.alter_column('audit', 'created_at', type_=DateTime(timezone=True))
    op.alter_column('submission', 'created_at', type_=DateTime(timezone=True))


def downgrade():
    op.alter_column('tournament', 'begin_at', type_=DateTime(timezone=False))
    op.alter_column('tournament', 'finish_at', type_=DateTime(timezone=False))
    op.alter_column('audit', 'created_at', type_=DateTime(timezone=False))
    op.alter_column('submission', 'created_at', type_=DateTime(timezone=False))

