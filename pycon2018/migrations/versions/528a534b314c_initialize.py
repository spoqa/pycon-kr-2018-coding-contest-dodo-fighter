"""Initialize

Revision ID: 528a534b314c
Revises: 
Create Date: 2018-07-27 12:58:28.107352

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.types import UUIDType

# revision identifiers, used by Alembic.
revision = '528a534b314c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('avatar', sa.String(length=256), nullable=True),
        sa.Column('display_name', sa.Unicode(length=128), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('moderator', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table(
        'tournament',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('begin_at', sa.DateTime(), nullable=False),
        sa.Column('finish_at', sa.DateTime(), nullable=False),
        sa.Column('final_match_id', UUIDType()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'submission',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('tournament_id', UUIDType(), nullable=False),
        sa.Column('user_id', UUIDType(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournament.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'user_id', name='uc_submission')
    )
    op.create_table(
        'tournament_match_set',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('tournament_id', UUIDType(), nullable=False),
        sa.Column('final_match_id', UUIDType()),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournament.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'tournament_match_set_item',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('tournament_match_set_id', UUIDType(), nullable=False),
        sa.Column('submission_id', UUIDType(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submission.id'], ),
        sa.ForeignKeyConstraint(['tournament_match_set_id'], ['tournament_match_set.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id')
    )
    op.create_table(
        'match',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('p1_id', UUIDType(), nullable=False),
        sa.Column('p1_parent_id', UUIDType(), nullable=True),
        sa.Column('p2_id', UUIDType(), nullable=False),
        sa.Column('p2_parent_id', UUIDType(), nullable=True),
        sa.Column('winner_id', UUIDType(), nullable=True),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('match_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('disclosed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['p1_id'], ['tournament_match_set_item.id'], ),
        sa.ForeignKeyConstraint(['p1_parent_id'], ['match.id'], ),
        sa.ForeignKeyConstraint(['p2_id'], ['tournament_match_set_item.id'], ),
        sa.ForeignKeyConstraint(['p2_parent_id'], ['match.id'], ),
        sa.ForeignKeyConstraint(['winner_id'], ['tournament_match_set_item.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_foreign_key(
        'fk_tournament_final_match_id', 'tournament', 'match',
        ['final_match_id'], ['id']
    )
    op.create_foreign_key(
        'fk_tournament_match_set_final_match_id', 'tournament_match_set',
        'match', ['final_match_id'], ['id']
    )


def downgrade():
    op.drop_table('match')
    op.drop_table('tournament_match_set_item')
    op.drop_table('tournament_match_set')
    op.drop_table('submission')
    op.drop_table('tournament')
    op.drop_table('user')
