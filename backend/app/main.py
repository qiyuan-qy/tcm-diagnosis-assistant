from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, knowledge
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
    description='基于RAG的中医诊疗助手系统'
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 路由
app.include_router(
    chat.router,
    prefix=f'{settings.API_V1_STR}/chat',
    tags=['chat']
)

app.include_router(
    knowledge.router,
    prefix=f'{settings.API_V1_STR}/knowledge',
    tags=['knowledge']
)

@app.get('/')
async def root():
    return {
        'message': settings.PROJECT_NAME,
        'version': settings.VERSION,
        'docs': '/docs',
        'features': [
            'RAG知识库检索',
            '多格式文档支持(.docx, .md, .pdf)',
            '智谱AI对话',
            '问卷式问诊'
        ]
    }

@app.get('/health')
async def health():
    return {'status': 'healthy', 'version': settings.VERSION}
