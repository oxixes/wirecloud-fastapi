# -*- coding: utf-8 -*-

# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

from src.wirecloud.database import Base

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class UserGroup(Base):
    __tablename__ = 'auth_user_groups'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('auth_group.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='unique_user_group'),
    )


class UserPermission(Base):
    __tablename__ = 'auth_user_user_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('auth_permission.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'permission_id', name='unique_user_permission'),
    )


class GroupPermission(Base):
    __tablename__ = 'auth_group_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    group_id = Column(Integer, ForeignKey('auth_group.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('auth_permission.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('group_id', 'permission_id', name='unique_group_permission'),
    )


class Permission(Base):
    __tablename__ = 'auth_permission'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    codename = Column(String(255), nullable=False, unique=True)


class User(Base):
    __tablename__ = 'auth_user'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    username = Column(String(150), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    first_name = Column(String(30), nullable=False)
    last_name = Column(String(150), nullable=False)
    is_superuser = Column(Boolean, nullable=False)
    is_staff = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    date_joined = Column(DateTime(timezone=True), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=False)

    groups = relationship('Group', secondary='auth_user_groups', back_populates='users')
    permissions = relationship('Permission', secondary='auth_user_user_permissions')

    uploaded_resources = relationship('CatalogueResource', back_populates='creator')
    local_resources = relationship('CatalogueResource', secondary='catalogue_catalogueresource_users', back_populates='users')


class Group(Base):
    __tablename__ = 'auth_group'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    name = Column(String(150), nullable=False, unique=True)

    users = relationship('User', secondary='auth_user_groups', back_populates='groups')
    permissions = relationship('Permission', secondary='auth_group_permissions')

    local_resources = relationship('CatalogueResource', secondary='catalogue_catalogueresource_groups', back_populates='groups')
