"""Create platform branch

Revision ID: 14398428d2a4
Revises:
Create Date: 2024-07-02 02:42:48.853730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14398428d2a4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('platform',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The following tables are based on what Django creates (some changes have been made).
    # This is done to maintain compatibility with the old WireCloud database schema and
    # facilitate the migration of the old data to the new schema.

    # Create the wirecloud_constant table
    op.create_table(
        'wirecloud_constant',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('concept', sa.String(255), nullable=False, unique=True),
        sa.Column('value', sa.String(256), nullable=False),
    )

    # Create an index on the wirecloud_constant table for the concept column (varchar_pattern_ops)
    op.create_index('wirecloud_constant_concept_idx', 'wirecloud_constant', ['concept'], unique=True, postgresql_ops={'concept': 'varchar_pattern_ops'})


def downgrade() -> None:
    # Drop the tables created in the upgrade method
    op.drop_table('wirecloud_constant')
