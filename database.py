from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from ..config.settings import settings


Base = declarative_base()


class OriginalDocs(Base):
    __tablename__ = "original_docs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    create_time = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    parent_chunks = relationship("ParentChunk", back_populates="original_docs", cascade="all, delete-orphan")
    child_chunks = relationship("ChildChunk", back_populates="original_docs", cascade="all, delete-orphan")


class ParentChunk(Base):
    __tablename__ = "parent_chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("original_docs.id"), nullable=False)
    parent_id = Column(String(100), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    json_metadata = Column(JSON)
    vector_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now())
    hypothetic_questions = Column(JSON, nullable=True)

    original_docs = relationship("OriginalDocs", back_populates="parent_chunks")
    child_chunks = relationship("ChildChunk", back_populates="parent_chunk", cascade="all, delete-orphan")


class ChildChunk(Base):
    __tablename__ = "child_chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("original_docs.id"), nullable=False)
    parent_chunk_id = Column(Integer, ForeignKey("parent_chunks.id"), nullable=False)
    child_id = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    json_metadata = Column(JSON)
    vector_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now())
    summary = Column(Text, nullable=True)

    original_docs = relationship("OriginalDocs", back_populates="child_chunks")
    parent_chunk = relationship("ParentChunk", back_populates="child_chunks")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=False)
    document_ids = Column(String(500))
    used_chunks = Column(Text)
    created_at = Column(DateTime, default=datetime.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DatabaseManager:
    """
    MCP 侧 DatabaseManager（RAG 迁移后统一使用它）。
    说明：当前 `427MCPProject` 原本没有 DB 层，因此作为迁移依赖一并补齐。
    """

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.init_database()

    def init_database(self):
        connection = (
            f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
            f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        )
        self.engine = create_engine(url=connection, pool_size=3, pool_pre_ping=True, max_overflow=5)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

    # 用户相关数据库操作
    def create_user(self, username: str, password_hash: str, email: str = None):
        """创建新用户"""
        session = self.get_session()
        try:
            user = User(username=username, password_hash=password_hash, email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_by_username(self, username: str):
        """根据用户名获取用户"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            return user
        finally:
            session.close()

    def get_user_by_id(self, user_id: int):
        """根据ID获取用户"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            return user
        finally:
            session.close()
