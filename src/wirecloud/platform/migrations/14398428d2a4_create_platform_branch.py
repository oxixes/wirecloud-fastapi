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
depends_on: Union[str, Sequence[str], None] = '42a7145c4074'


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
    op.create_index('wirecloud_constant_concept_idx', 'wirecloud_constant', ['concept'], unique=True,
                    postgresql_ops={'concept': 'varchar_pattern_ops'})

    # Create the wirecloud_market table
    op.create_table(
        'wirecloud_market',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('public', sa.Boolean, nullable=False),
        sa.Column('options', sa.Text, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('auth_user.id', deferrable=True,
                                                       initially="DEFERRED", ondelete='CASCADE',
                                                       onupdate='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'name', name='unique_market_name_user')
    )

    # Create index on the wirecloud_market table for the user_id column
    op.create_index('wirecloud_market_user_id_idx', 'wirecloud_market', ['user_id'])

    # Create the wirecloud_marketuserdata table
    op.create_table(
        'wirecloud_marketuserdata',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('value', sa.String(250), nullable=False),
        sa.Column('market_id', sa.Integer, sa.ForeignKey('wirecloud_market.id', deferrable=True,
                                                         initially="DEFERRED", ondelete='CASCADE',
                                                         onupdate='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('auth_user.id', deferrable=True,
                                                       initially="DEFERRED", ondelete='CASCADE',
                                                       onupdate='CASCADE'), nullable=False),
        sa.UniqueConstraint('market_id', 'user_id', 'name', name='unique_marketuserdata_name_user_market')
    )

    # Create indexes on the wirecloud_marketuserdata table for the market_id and the user_id column
    op.create_index('wirecloud_marketuserdata_market_id_idx', 'wirecloud_marketuserdata', ['market_id'])
    op.create_index('wirecloud_marketuserdata_user_id_idx', 'wirecloud_marketuserdata', ['user_id'])

    # Create the wirecloud_workspace table
    op.create_table(
        'wirecloud_workspace',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('name', sa.String(30), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('creation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('searchable', sa.Boolean, nullable=False),
        sa.Column('public', sa.Boolean, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('longdescription', sa.Text, nullable=False),
        sa.Column('forcedValues', sa.Text, nullable=False),
        sa.Column('wiringStatus', sa.Text, nullable=False),
        sa.Column('creator_id', sa.Integer,
                  sa.ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),
        sa.Column('requireauth', sa.Boolean, nullable=False),

        sa.UniqueConstraint('creator_id', 'name', name='unique_workspace_name_creator')
    )


    # Create indexes on the wirecloud_workspace table for the creator_id column
    op.create_index('wirecloud_workspace_creator_id_idx', 'wirecloud_workspace', ['creator_id'])

    # Create the wirecloud_userworkspace table
    op.create_table(
        'wirecloud_userworkspace',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('user_id', sa.Integer,
                  sa.ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Integer,
                  sa.ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),
        sa.Column('accesslevel', sa.SmallInteger, nullable=False),

        sa.UniqueConstraint('workspace_id', 'user_id',
                            name='unique_userworkspace_user_workspace')
    )

    # Create indexes on the wirecloud_userworkspace table for the user_id and the workspace_id column
    op.create_index('wirecloud_userworkspace_user_id_idx', 'wirecloud_userworkspace', ['user_id'])
    op.create_index('wirecloud_userworkspace_workspace_id_idx', 'wirecloud_userworkspace', ['workspace_id'])

    # Create the wirecloud_tab table
    op.create_table(
        'wirecloud_tab',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('name', sa.String(30), nullable=False),
        sa.Column('title', sa.String(30), nullable=False),
        sa.Column('visible', sa.Boolean, nullable=False),
        sa.Column('position', sa.Integer, nullable=True),
        sa.Column('workspace_id', sa.Integer,
                  sa.ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),

        sa.UniqueConstraint('name', 'workspace_id', name='unique_tab_workspace_name')
    )

    # Create indexes on the wirecloud_tab table for the workspace_id column
    op.create_index('wirecloud_tab_workspace_id_idx', 'wirecloud_tab', ['workspace_id'])

    # Create the wirecloud_workspace_groups table
    op.create_table(
        'wirecloud_workspace_groups',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('workspace_id', sa.Integer,
                  sa.ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),
        sa.Column('group_id', sa.Integer,
                  sa.ForeignKey('auth_group.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                onupdate='CASCADE'), nullable=False),

        sa.UniqueConstraint('workspace_id', 'group_id', name='unique_workspace_groups_group_workspace')
    )

    # Create indexes on the wirecloud_workspace_groups table for the workspace_id and the group_id column
    op.create_index('wirecloud_workspace_groups_workspace_id_idx', 'wirecloud_workspace_groups', ['workspace_id'])
    op.create_index('wirecloud_workspace_groups_group_id_idx', 'wirecloud_workspace_groups', ['group_id'])


def downgrade() -> None:
    # Drop the tables created in the upgrade method
    op.drop_table('wirecloud_workspace_groups')
    op.drop_table('wirecloud_tab')
    op.drop_table('wirecloud_userworkspace')
    op.drop_table('wirecloud_workspace')
    op.drop_table('wirecloud_marketuserdata')
    op.drop_table('wirecloud_market')
    op.drop_table('wirecloud_constant')
