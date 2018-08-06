"""Remove not nullable constraint on match.p1_id and match.p2_id

Revision ID: ced919e42d8b
Revises: 647570a7ae16
Create Date: 2018-08-03 18:38:02.927992

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ced919e42d8b'
down_revision = '647570a7ae16'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('match', 'p1_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)
    op.alter_column('match', 'p2_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)


def downgrade():
    op.alter_column('match', 'p2_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)
    op.alter_column('match', 'p1_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)
