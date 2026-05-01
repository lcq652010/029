from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "服务器性能监控系统"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./monitor.db"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-keep-it-safe-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 监控阈值配置
    CPU_THRESHOLD: float = 80.0  # CPU 使用率阈值
    MEMORY_THRESHOLD: float = 80.0  # 内存使用率阈值
    
    # WebSocket 配置
    WS_UPDATE_INTERVAL: int = 1  # 推送间隔（秒）
    
    # 历史数据保存天数
    HISTORY_RETENTION_DAYS: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
