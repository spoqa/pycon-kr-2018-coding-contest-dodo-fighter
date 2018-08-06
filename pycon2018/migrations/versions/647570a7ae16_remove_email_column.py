"""Remove email column

Revision ID: 647570a7ae16
Revises: 528a534b314c
Create Date: 2018-08-03 10:46:27.070426

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '647570a7ae16'
down_revision = '528a534b314c'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('user_email_key', 'user', type_='unique')
    op.create_unique_constraint(None, 'user', ['display_name'])
    op.drop_column('user', 'email')


def downgrade():
    op.add_column('user', sa.Column('email', sa.VARCHAR(length=128),
                                    autoincrement=False, nullable=False))
    op.drop_constraint(None, 'user', type_='unique')
    op.create_unique_constraint('user_email_key', 'user', ['email'])
