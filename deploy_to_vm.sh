#!/bin/bash
# ==============================================
# TCM诊疗助手 - 虚拟机全自动部署脚本
# 在Ubuntu 22.04.5虚拟机中运行
# ==============================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TCM诊疗助手 - 开始部署${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 更新系统并安装基础依赖
echo -e "\n${YELLOW}[1/10] 更新系统并安装基础依赖...${NC}"
sudo apt update
sudo apt install -y curl wget git python3-pip python3-venv \
    build-essential software-properties-common nginx

# 2. 安装Docker
echo -e "\n${YELLOW}[2/10] 安装Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker安装完成${NC}"
else
    echo -e "${GREEN}Docker已安装${NC}"
fi

# 3. 安装Docker Compose
echo -e "\n${YELLOW}[3/10] 安装Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose安装完成${NC}"
else
    echo -e "${GREEN}Docker Compose已安装${NC}"
fi

# 4. 创建项目目录结构
echo -e "\n${YELLOW}[4/10] 创建项目目录结构...${NC}"
cd ~/tcm-diagnosis-assistant
mkdir -p backend/app/{api,core,services,models}
mkdir -p frontend/dist
mkdir -p data/chroma
mkdir -p nginx

# 5. 创建Python requirements.txt
echo -e "\n${YELLOW}[5/10] 创建依赖配置...${NC}"
cat > backend/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
langchain==0.1.0
langchain-community==0.0.10
chromadb==0.4.22
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
sentence-transformers==2.3.1
EOF

# 6. 创建后端配置文件
echo -e "\n${YELLOW}[6/10] 创建后端代码...${NC}"

cat > backend/app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "TCM诊疗助手"
    VERSION: str = "1.0.0"
    BACKEND_CORS_ORIGINS: list = ["*"]
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"

    class Config:
        env_file = ".env"

settings = Settings()
EOF

cat > backend/app/services/embedding.py << 'EOF'
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import numpy as np

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed_text(self, text: str) -> list:
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_texts(self, texts: list) -> list:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

embedding_service = EmbeddingService()
EOF

cat > backend/app/core/rag.py << 'EOF'
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.services.embedding import embedding_service
import os
import json

class RAGService:
    def __init__(self):
        self.persist_directory = "./data/chroma"
        os.makedirs(self.persist_directory, exist_ok=True)
        self.documents = []
        self.load_documents()

    def load_documents(self):
        """从文件加载文档"""
        doc_file = os.path.join(self.persist_directory, "documents.json")
        if os.path.exists(doc_file):
            with open(doc_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])

    def save_documents(self):
        """保存文档到文件"""
        doc_file = os.path.join(self.persist_directory, "documents.json")
        with open(doc_file, 'w', encoding='utf-8') as f:
            json.dump({'documents': self.documents}, f, ensure_ascii=False, indent=2)

    def add_document(self, text: str, metadata: dict = None):
        """添加文档"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )

        chunks = text_splitter.split_text(text)
        for chunk in chunks:
            doc = {
                'content': chunk,
                'metadata': metadata or {}
            }
            self.documents.append(doc)

        self.save_documents()
        return len(chunks)

    def similarity_search(self, query: str, k: int = 3) -> list:
        """相似度搜索"""
        if not self.documents:
            return []

        query_embedding = embedding_service.embed_text(query)

        # 计算所有文档的相似度
        similarities = []
        for doc in self.documents:
            doc_embedding = embedding_service.embed_text(doc['content'])
            # 计算余弦相似度
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append((similarity, doc))

        # 排序并返回top-k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in similarities[:k]]

    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        import numpy as np
        a = np.array(vec1)
        b = np.array(vec2)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

rag_service = RAGService()
EOF

cat > backend/app/models/schemas.py << 'EOF'
from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    response: str
    session_id: str
    need_more_info: bool = False

class DocumentUpload(BaseModel):
    filename: str
    content: str
    doc_type: str
EOF

cat > backend/app/api/chat.py << 'EOF'
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
import uuid
import random

router = APIRouter()

# 简化的中医知识库
TCM_KNOWLEDGE = {
    "感冒": [
        "风寒感冒：发热轻、恶寒重、无汗、头痛、肢体酸痛、鼻塞声重",
        "风热感冒：发热重、恶寒轻、有汗、咽喉肿痛、咳痰黄稠",
        "暑湿感冒：发热、汗出不畅、肢体困重、头昏重胀、心烦口渴"
    ],
    "咳嗽": [
        "风寒咳嗽：咳声重浊、痰白稀薄、伴有鼻塞流清涕",
        "风热咳嗽：咳声粗亢、痰黄黏稠、咽痛口干",
        "燥咳：干咳无痰、咽干鼻燥、舌红少津"
    ],
    "失眠": [
        "心脾两虚：多梦易醒、心悸健忘、头晕目眩、神疲食少",
        "阴虚火旺：心烦失眠、入睡困难、手足心热、盗汗口干",
        "心胆气虚：失眠多梦、易于惊醒、心悸胆怯、气短倦怠"
    ]
}

def get_tcm_diagnosis(symptoms: str) -> str:
    """基于症状的中医诊断"""
    symptoms_lower = symptoms.lower()

    # 检查症状关键词
    if any(word in symptoms_lower for word in ["发热", "感冒", "寒", "鼻塞"]):
        if "寒" in symptoms_lower and "热" not in symptoms_lower:
            return "根据您描述的症状（恶寒重、发热轻），初步判断为**风寒感冒**。\n\n**辨证要点**：\n- 风寒束表，肺卫不固\n- 治法：辛温解表，宣肺散寒\n\n**建议**：\n1. 生姜红糖水驱寒\n2. 意白、豆豉煮水饮用\n3. 注意保暖，避免吹风\n4. 如症状加重，请及时就医"
        elif "热" in symptoms_lower or "咽喉" in symptoms_lower:
            return "根据您描述的症状（发热重、咽喉痛），初步判断为**风热感冒**。\n\n**辨证要点**：\n- 风热犯表，热郁肌腠\n- 治法：辛凉解表，清热解毒\n\n**建议**：\n1. 菊花、薄荷泡茶饮用\n2. 金银花、连翘煮水\n3. 多饮温水，忌辛辣\n4. 如高热不退，请及时就医"

    if any(word in symptoms_lower for word in ["失眠", "睡不着", "多梦"]):
        return "根据您描述的失眠症状，需要了解更多信息：\n\n**请补充以下信息**：\n1. 入睡是否困难？\n2. 是否多梦易醒？\n3. 是否有心悸、健忘？\n4. 是否有手足心热、盗汗？\n5. 饮食、大便情况如何？\n\n请详细描述，以便我为您进行更准确的辨证。"

    if any(word in symptoms_lower for word in ["咳嗽", "咳"]):
        return "关于咳嗽症状，我需要了解更多：\n\n**请补充**：\n1. 痰的颜色和质地（白稀/黄稠/无痰）？\n2. 是否伴有咽喉痛？\n3. 咳嗽的声音（重浊/粗亢/干咳）？\n4. 起病时间及诱因？\n\n请提供更多信息以便辨证。"

    # 默认响应 - 需要更多信息
    return "感谢您提供的信息。为了更准确地为您进行中医辨证，我需要了解更多症状：\n\n**请补充以下信息**：\n1. 主要不适部位及具体感觉\n2. 症状的起病时间\n3. 是否有其他伴随症状\n4. 饮食、睡眠、二便情况\n5. 舌象（如：舌红、苔黄腻等）\n\n请逐一描述，我将为您进行详细的辨证分析。"

@router.post("/consultation", response_model=ChatResponse)
async def consultation(request: ChatRequest):
    """中医诊疗对话接口"""
    try:
        # 生成诊断回复
        response = get_tcm_diagnosis(request.message)

        # 判断是否需要更多信息
        need_more_info = "请补充" in response or "请详细描述" in response or "请提供" in response

        return ChatResponse(
            response=response,
            session_id=request.session_id or str(uuid.uuid4()),
            need_more_info=need_more_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "tcm-diagnosis"}
EOF

cat > backend/app/api/knowledge.py << 'EOF'
from fastapi import APIRouter
from app.core.rag import rag_service
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_document(data: dict):
    """上传知识库文档"""
    try:
        content = data.get('content', '')
        filename = data.get('filename', 'unknown')

        chunk_count = rag_service.add_document(
            text=content,
            metadata={"filename": filename, "doc_id": str(uuid.uuid4())}
        )

        return {
            "status": "success",
            "filename": filename,
            "chunks_added": chunk_count,
            "message": f"文档上传成功，添加了{chunk_count}个文本块"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/documents")
async def list_documents():
    """列出所有文档"""
    return {"documents": rag_service.documents, "count": len(rag_service.documents)}
EOF

cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, knowledge
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["knowledge"])

@app.get("/")
async def root():
    return {
        "message": "TCM诊疗助手API",
        "version": settings.VERSION,
        "docs": "/docs"
    }
EOF

# 创建空的__init__.py文件
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/core/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py

echo -e "${GREEN}后端代码创建完成${NC}"

# 7. 创建前端页面
echo -e "\n${YELLOW}[7/10] 创建前端页面...${NC}"
cat > frontend/dist/index.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TCM诊疗助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        .title {
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .subtitle { color: #666; font-size: 1.1em; }
        .chat-container {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .chat-messages {
            height: 450px;
            overflow-y: auto;
            padding: 25px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 18px;
            padding: 14px 20px;
            border-radius: 18px;
            max-width: 80%;
            animation: slideIn 0.3s ease-out;
            line-height: 1.6;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        .message.assistant {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .input-area {
            padding: 20px 25px;
            background: white;
            border-top: 1px solid #eee;
            display: flex;
            gap: 12px;
        }
        #userInput {
            flex: 1;
            padding: 14px 22px;
            border: 2px solid #e0e0e0;
            border-radius: 28px;
            font-size: 16px;
            outline: none;
            transition: all 0.3s;
            background: #f8f9fa;
        }
        #userInput:focus {
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        #sendBtn {
            padding: 14px 35px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 28px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        #sendBtn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        #sendBtn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            padding: 12px 25px;
            border-radius: 12px;
            margin-bottom: 18px;
            text-align: center;
            font-weight: 500;
        }
        .status.ready {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.thinking {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .welcome-msg {
            background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        .loading {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        strong { color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🌿 TCM诊疗助手</h1>
            <p class="subtitle">传统中医智能诊疗系统 - 专业辨证分析</p>
        </div>

        <div id="status" class="status ready">
            ✅ 系统已就绪，请描述您的症状
        </div>

        <div class="chat-container">
            <div class="chat-messages" id="messages">
                <div class="welcome-msg message assistant">
                    <strong>您好！</strong>我是您的中医诊疗助手。<br><br>
                    请告诉我您哪里不舒服，我会通过问诊了解您的症状，并提供专业的中医辨证分析和调理建议。<br><br>
                    <em>您可以描述：头痛、发热、咳嗽、失眠、消化不良等症状</em>
                </div>
            </div>
            <div class="input-area">
                <input type="text" id="userInput" placeholder="描述您的症状，如：最近头痛发热..." onkeypress="if(event.key==='Enter')sendMessage()">
                <button id="sendBtn" onclick="sendMessage()">咨询</button>
            </div>
        </div>
    </div>

    <script>
        const API_URL = '/api/v1';
        let sessionId = null;
        let isLoading = false;

        async function sendMessage() {
            if (isLoading) return;

            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            // 添加用户消息
            addMessage(message, 'user');
            input.value = '';
            isLoading = true;

            // 更新状态
            const statusDiv = document.getElementById('status');
            statusDiv.className = 'status thinking';
            statusDiv.innerHTML = '正在分析症状... <span class="loading"></span>';

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;

            try {
                const response = await fetch(`${API_URL}/chat/consultation`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    })
                });

                if (!response.ok) throw new Error('API请求失败');

                const data = await response.json();
                sessionId = data.session_id;
                addMessage(data.response, 'assistant');

                if (data.need_more_info) {
                    statusDiv.textContent = '🩺 需要更多信息以完成诊断，请补充症状描述';
                    statusDiv.className = 'status thinking';
                } else {
                    statusDiv.textContent = '✅ 诊断分析已完成';
                    statusDiv.className = 'status ready';
                }
            } catch (error) {
                statusDiv.textContent = '❌ 连接失败，请检查后端服务';
                statusDiv.className = 'status error';
                addMessage('抱歉，系统出现错误。请确保后端服务正常运行。', 'assistant');
            } finally {
                isLoading = false;
                sendBtn.disabled = false;
            }
        }

        function addMessage(text, type) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
EOF

echo -e "${GREEN}前端页面创建完成${NC}"

# 8. 创建Nginx配置
echo -e "\n${YELLOW}[8/10] 创建Nginx配置...${NC}"
cat > nginx/nginx.conf << 'EOF'
events { worker_connections 1024; }

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    server {
        listen 80;
        server_name localhost;

        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 9. 安装Python依赖并启动后端
echo -e "\n${YELLOW}[9/10] 安装Python依赖...${NC}"
cd ~/tcm-diagnosis-assistant/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${GREEN}Python依赖安装完成${NC}"

# 10. 启动服务
echo -e "\n${YELLOW}[10/10] 启动服务...${NC}"

# 复制前端文件到Nginx
sudo rm -rf /usr/share/nginx/html/*
sudo cp -r ~/tcm-diagnosis-assistant/frontend/dist/* /usr/share/nginx/html/

# 启动Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# 创建systemd服务
cat > /tmp/tcm-backend.service << 'EOF'
[Unit]
Description=TCM Diagnosis Backend
After=network.target

[Service]
Type=simple
User=xiyun
WorkingDirectory=/home/xiyun/tcm-diagnosis-assistant/backend
Environment="PATH=/home/xiyun/tcm-diagnosis-assistant/backend/venv/bin"
ExecStart=/home/xiyun/tcm-diagnosis-assistant/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/tcm-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start tcm-backend
sudo systemctl enable tcm-backend

# 等待服务启动
sleep 3

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}🌐 访问地址：${NC}"
echo -e "   http://192.168.171.129"
echo ""
echo -e "${BLUE}📊 服务状态：${NC}"
echo -e "   后端API: http://192.168.171.129:8000/docs"
echo -e "   前端界面: http://192.168.171.129"
echo ""
echo -e "${BLUE}🔧 管理命令：${NC}"
echo -e "   查看后端日志: sudo journalctl -u tcm-backend -f"
echo -e "   重启后端: sudo systemctl restart tcm-backend"
echo -e "   重启Nginx: sudo systemctl restart nginx"
echo ""
echo -e "${YELLOW}提示：首次访问会下载中文向量模型，可能需要几分钟${NC}"
