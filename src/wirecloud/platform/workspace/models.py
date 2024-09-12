from src.wirecloud.database import Base

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, SmallInteger
from sqlalchemy.orm import relationship


class UserWorkspace(Base):
    __tablename__ = 'wirecloud_userworkspace'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                         onupdate='CASCADE'), nullable=False)
    workspace_id = Column(Integer, ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED",
                                              ondelete='CASCADE',
                                              onupdate='CASCADE'), nullable=False)
    accesslevel = Column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='unique_userworkspace_user_workspace'),
    )


class WorkspaceGroup(Base):
    __tablename__ = 'wirecloud_workspace_groups'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    workspace_id = Column(Integer, ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED",
                                              ondelete='CASCADE',
                                              onupdate='CASCADE'), nullable=False)
    group_id = Column(Integer,
                      ForeignKey('auth_group.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                 onupdate='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('workspace_id', 'group_id', name='unique_workspace_groups_group_workspace'),
    )


class Workspace(Base):
    __tablename__ = 'wirecloud_workspace'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    name = Column(String(30), nullable=False)
    title = Column(String(255), nullable=False)
    creation_date = Column(DateTime(timezone=True), nullable=False)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    searchable = Column(Boolean, nullable=False)
    public = Column(Boolean, nullable=False)
    description = Column(Text, nullable=False)
    longdescription = Column(Text, nullable=False)
    forcedValues = Column(Text, nullable=False)
    wiringStatus = Column(Text, nullable=False)
    creator_id = Column(Integer, ForeignKey('auth_user.id', deferrable=True, initially="DEFERRED", ondelete='CASCADE',
                                            onupdate='CASCADE'), nullable=False)
    requireauth = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint('creator_id', 'name', name='unique_workspace_name_creator'),
    )

    creator = relationship('User', back_populates='workspaces_created')
    users = relationship('User', secondary='wirecloud_userworkspace', back_populates='workspaces')
    tabs = relationship('Tab', back_populates='workspace')
    groups = relationship('Group', secondary='wirecloud_workspace_groups', back_populates='workspaces')


class Tab(Base):
    __tablename__ = 'wirecloud_tab'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    name = Column(String(30), nullable=False)
    tittle = Column(String(30), nullable=False)
    visible = Column(Boolean, nullable=False)
    position = Column(Integer, nullable=True)
    workspace_id = Column(Integer, ForeignKey('wirecloud_workspace.id', deferrable=True, initially="DEFERRED",
                                              ondelete='CASCADE',
                                              onupdate='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', 'workspace_id', name='unique_tab_workspace_name'),
    )

    workspace = relationship('Workspace', back_populates='tabs')