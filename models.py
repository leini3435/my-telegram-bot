# models.py - 数据库模型定义
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# 数据库引擎（从环境变量读取 DATABASE_URL）
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("请在 Railway Variables 中设置 DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class CertifiedUser(Base):
    __tablename__ = "certified_users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, index=True)       # Telegram 用户 ID（字符串）
    username = Column(String, nullable=True)              # @username（可选）
    full_name = Column(String, nullable=True)             # 姓名或备注
    certified_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)             # 是否有效

class Checkin(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True, index=True)
    teacher_tg_id = Column(String, index=True)            # 关联认证用户 tg_id
    checkin_time = Column(DateTime, default=datetime.utcnow)
    date = Column(DateTime)                               # 当天日期，用于去重

# 创建所有表（只运行一次，或在 bot 启动时调用）
def create_tables():
    Base.metadata.create_all(bind=engine)

# 在 bot.py 的 main() 里调用一次
# create_tables()
