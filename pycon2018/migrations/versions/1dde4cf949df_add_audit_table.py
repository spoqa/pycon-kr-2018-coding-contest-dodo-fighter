"""Add audit table

Revision ID: 1dde4cf949df
Revises: ced919e42d8b
Create Date: 2018-08-18 10:00:18.637325

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils.types.uuid import UUIDType


# revision identifiers, used by Alembic.
revision = '1dde4cf949df'
down_revision = 'ced919e42d8b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('user_id', UUIDType(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_created_at'), 'audit', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_audit_created_at'), table_name='audit')
    op.drop_table('audit')

