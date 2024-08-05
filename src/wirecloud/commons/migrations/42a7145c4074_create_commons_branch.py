"""create commons branch

Revision ID: 42a7145c4074
Revises: 
Create Date: 2024-08-01 00:09:08.207156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42a7145c4074'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('commons',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The following tables are based on what Django creates (some changes have been made).
    # This is done to maintain compatibility with the old WireCloud database schema and
    # facilitate the migration of the old data to the new schema.

    # Create the auth_permission table
    op.create_table(
        'auth_permission',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('codename', sa.String(255), nullable=False, unique=True)
    )

    # Create the auth_user table
    op.create_table(
        'auth_user',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('username', sa.String(150), nullable=False, unique=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(30), nullable=False),
        sa.Column('last_name', sa.String(150), nullable=False),
        sa.Column('is_superuser', sa.Boolean, nullable=False),
        sa.Column('is_staff', sa.Boolean, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False),
        sa.Column('date_joined', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True)
    )

    # Create an index on the auth_user table for the username column (varchar_pattern_ops)
    op.create_index('auth_user_username_idx', 'auth_user', ['username'], unique=True,
                    postgresql_ops={'username': 'varchar_pattern_ops'})

    # Create the auth_group table
    op.create_table(
        'auth_group',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('name', sa.String(150), nullable=False, unique=True)
    )

    # Create an index on the auth_group table for the name column (varchar_pattern_ops)
    op.create_index('auth_group_name_idx', 'auth_group', ['name'], unique=True,
                    postgresql_ops={'name': 'varchar_pattern_ops'})

    # Create the auth_user_groups table
    op.create_table(
        'auth_user_groups',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED",
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('auth_group.id', deferrable=True, initially="DEFERRED",
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'group_id', name='unique_user_group')
    )

    # Create indexes on the auth_user_groups table for the user_id and group_id columns
    op.create_index('auth_user_groups_user_id_idx', 'auth_user_groups', ['user_id'])
    op.create_index('auth_user_groups_group_id_idx', 'auth_user_groups', ['group_id'])

    # Create the auth_user_user_permissions table
    op.create_table(
        'auth_user_user_permissions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED",
                                                       ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.Integer, sa.ForeignKey('auth_permission.id', deferrable=True,
                                                             initially="DEFERRED", ondelete='CASCADE',
                                                             onupdate='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'permission_id', name='unique_user_permission')
    )

    # Create indexes on the auth_user_user_permissions table for the user_id and permission_id columns
    op.create_index('auth_user_user_permissions_user_id_idx', 'auth_user_user_permissions', ['user_id'])
    op.create_index('auth_user_user_permissions_permission_id_idx', 'auth_user_user_permissions', ['permission_id'])

    # Create the auth_group_permissions table
    op.create_table(
        'auth_group_permissions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('auth_group.id', deferrable=True, initially="DEFERRED",
                                                        ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.Integer,
                  sa.ForeignKey('auth_permission.id', deferrable=True, initially="DEFERRED",
                                ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.UniqueConstraint('group_id', 'permission_id', name='unique_group_permission')
    )

    # Create indexes on the auth_group_permissions table for the group_id and permission_id columns
    op.create_index('auth_group_permissions_group_id_idx', 'auth_group_permissions', ['group_id'])
    op.create_index('auth_group_permissions_permission_id_idx', 'auth_group_permissions', ['permission_id'])


def downgrade() -> None:
    op.drop_table('auth_group_permissions')
    op.drop_table('auth_user_user_permissions')
    op.drop_table('auth_user_groups')
    op.drop_table('auth_group')
    op.drop_table('auth_user')
    op.drop_table('auth_permission')
