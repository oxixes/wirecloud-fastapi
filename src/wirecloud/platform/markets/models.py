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

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class Market(Base):
    __tablename__ = 'wirecloud_market'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    public = Column(Boolean, nullable=False)
    options = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                         onupdate='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_market_name_user'),
    )

    user = relationship('User', back_populates='markets')
    userdata = relationship('MarketUserData', back_populates='market')


class MarketUserData(Base):
    __tablename__ = 'wirecloud_marketuserdata'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    value = Column(String(250), nullable=False)
    market_id = Column(Integer, ForeignKey('wirecloud_market.id', deferrable=True, initially="DEFERRED",
                                           ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                         onupdate='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('market_id', 'user_id', 'name', name='unique_marketuserdata_name_user_market'),
    )

    market = relationship('Market', back_populates='userdata')
    user = relationship('User', back_populates='marketuserdata')
