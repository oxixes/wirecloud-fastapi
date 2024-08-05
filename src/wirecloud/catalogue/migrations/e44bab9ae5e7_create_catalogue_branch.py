"""create catalogue branch

Revision ID: e44bab9ae5e7
Revises: 
Create Date: 2024-08-01 01:25:04.246470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e44bab9ae5e7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('catalogue',)
depends_on: Union[str, Sequence[str], None] = '42a7145c4074'


def upgrade() -> None:
    # The following tables are based on what Django creates (some changes have been made).
    # This is done to maintain compatibility with the old WireCloud database schema and
    # facilitate the migration of the old data to the new schema.

    # Create the catalogue_catalogueresource table
    op.create_table(
        'catalogue_catalogueresource',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('vendor', sa.String(250), nullable=False),
        sa.Column('short_name', sa.String(250), nullable=False),
        sa.Column('version', sa.String(150), nullable=False),
        sa.Column('type', sa.SmallInteger, nullable=False),
        sa.Column('public', sa.Boolean, nullable=False),
        sa.Column('creation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('template_uri', sa.String(200), nullable=False),
        sa.Column('popularity', sa.Numeric(2, 1), nullable=False),
        sa.Column('json_description', sa.Text, nullable=False),
        sa.Column('creator_id', sa.Integer, sa.ForeignKey('auth_user.id', ondelete='CASCADE', onupdate='CASCADE',
                                                          deferrable=True, initially="DEFERRED")),

        sa.UniqueConstraint('short_name', 'vendor', 'version', name='unique_catalogue_resource')
    )

    # Create index on the catalogue_catalogueresource table for the creator_id column
    op.create_index('catalogue_catalogueresource_creator_id_idx', 'catalogue_catalogueresource', ['creator_id'])

    # Create the catalogue_catalogueresource_users table
    op.create_table(
        'catalogue_catalogueresource_users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('catalogueresource_id', sa.Integer, sa.ForeignKey('catalogue_catalogueresource.id',
                                                                    ondelete='CASCADE', onupdate='CASCADE',
                                                                    deferrable=True, initially="DEFERRED"),
                  nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('auth_user.id', ondelete='CASCADE', onupdate='CASCADE',
                                                       deferrable=True, initially="DEFERRED"), nullable=False),

        sa.UniqueConstraint('catalogueresource_id', 'user_id', name='unique_catalogueresource_user')
    )

    # Create index on the catalogue_catalogueresource_users table for the user_id and catalogueresource_id column
    op.create_index('catalogue_catalogueresource_users_user_id_idx', 'catalogue_catalogueresource_users', ['user_id'])
    op.create_index('catalogue_catalogueresource_users_catalogueresource_id_idx', 'catalogue_catalogueresource_users',
                    ['catalogueresource_id'])

    # Create the catalogue_catalogueresource_groups table
    op.create_table(
        'catalogue_catalogueresource_groups',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('catalogueresource_id', sa.Integer, sa.ForeignKey('catalogue_catalogueresource.id',
                                                                    ondelete='CASCADE', onupdate='CASCADE',
                                                                    deferrable=True, initially="DEFERRED"),
                  nullable=False),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('auth_group.id', ondelete='CASCADE', onupdate='CASCADE',
                                                       deferrable=True, initially="DEFERRED"), nullable=False),

        sa.UniqueConstraint('catalogueresource_id', 'group_id', name='unique_catalogueresource_group')
    )

    # Create index on the catalogue_catalogueresource_groups table for the group_id and catalogueresource_id column
    op.create_index('catalogue_catalogueresource_groups_group_id_idx', 'catalogue_catalogueresource_groups',
                    ['group_id'])
    op.create_index('catalogue_catalogueresource_groups_catalogueresource_id_idx', 'catalogue_catalogueresource_groups',
                    ['catalogueresource_id'])


def downgrade() -> None:
    op.drop_table('catalogue_catalogueresource_groups')
    op.drop_table('catalogue_catalogueresource_users')
    op.drop_table('catalogue_catalogueresource')
