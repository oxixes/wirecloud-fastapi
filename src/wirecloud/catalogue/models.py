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

from sqlalchemy import (Column, Integer, String, SmallInteger, Boolean, DateTime, Numeric, Text, ForeignKey,
                        UniqueConstraint)
from sqlalchemy.orm import relationship


class CatalogueResourceUsers(Base):
    __tablename__ = 'catalogue_catalogueresource_users'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    catalogueresource_id = Column(Integer, ForeignKey('catalogue_catalogueresource.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('catalogueresource_id', 'user_id', name='unique_catalogueresource_user'),
    )


class CatalogueResourceGroups(Base):
    __tablename__ = 'catalogue_catalogueresource_groups'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    catalogueresource_id = Column(Integer, ForeignKey('catalogue_catalogueresource.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('auth_group.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('catalogueresource_id', 'group_id', name='unique_catalogueresource_group'),
    )


class CatalogueResource(Base):
    __tablename__ = 'catalogue_catalogueresource'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    vendor = Column(String(250), nullable=False)
    short_name = Column(String(250), nullable=False)
    version = Column(String(150), nullable=False)
    type = Column(SmallInteger, nullable=False)

    public = Column(Boolean, nullable=False)
    creation_date = Column(DateTime(timezone=True), nullable=False)

    # TODO: transform this field into a "trashed" field
    # We need to make a migration renaming files before removing it
    # Currently a empty value means that the resource has been marked as a trashed version when deploying a WireCloud catalogue
    # The idea is to track removed versions to disallow reuploading them
    # In those cases, users should upload a new version. This is done mimic default behaviour: https://github.com/pypa/packaging-problems/issues/74
    # This field should not be used on WireCloud platform, were this behaviour is not required
    template_uri = Column(String(200), nullable=False)
    popularity = Column(Numeric(2, 1), nullable=False)
    json_description = Column(Text, nullable=False)

    creator_id = Column(Integer, ForeignKey('auth_user.id'))

    creator = relationship('User', back_populates='uploaded_resources')
    users = relationship('User', secondary='catalogue_catalogueresource_users', back_populates='local_resources')
    groups = relationship('Group', secondary='catalogue_catalogueresource_groups', back_populates='local_resources')

    __table_args__ = (
        UniqueConstraint('short_name', 'vendor', 'version', name='unique_catalogue_resource'),
    )

