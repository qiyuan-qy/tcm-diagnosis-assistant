from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API配置
    API_V1_STR: str = '/api/v1'
    PROJECT_NAME: str = 'TCM诊疗助手-RAG版'
    VERSION: str = '2.0.0'
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ['*']
    
    # 智谱AI配置
    ZHIPUAI_API_KEY: Optional[str] = None
    ZHIPUAI_MODEL: str = 'glm-4-flash'
    
    # 向量数据库配置
    CHROMA_PERSIST_DIR: str = './data/chroma'
    CHROMA_COLLECTION_NAME: str = 'tcm_knowledge'
    
    # 文档配置
    UPLOAD_DIR: str = './data/uploads'
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    
    # RAG配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 3
    
    class Config:
        env_file = '.env'
        case_sensitive = True

settings = Settings()

# 确保目录存在
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
