from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.services.llm_service import llm_service
from app.services.conversation_service import conversation_service

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []

@router.post('/consultation', response_model=ChatResponse)
async def consultation(request: ChatRequest):
    """中医诊疗对话接口"""
    
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail='消息不能为空')
    
    try:
        # 获取或创建对话
        if request.conversation_id:
            conversation = conversation_service.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail='对话不存在')
        else:
            conversation = conversation_service.create_conversation()
        
        # 添加用户消息
        conversation_service.add_message(conversation['id'], 'user', request.message)
        
        # 获取对话历史
        conv = conversation_service.get_conversation(conversation['id'])
        conversation_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conv['messages'][:-1]
        ]
        
        # 调用RAG服务
        result = llm_service.chat_with_rag(
            message=request.message,
            conversation_history=conversation_history,
            session_id=conversation['id']
        )
        
        # 添加助手回复
        conversation_service.add_message(
            conversation['id'],
            'assistant',
            result['response'],
            result.get('sources', [])
        )
        
        return ChatResponse(
            response=result['response'],
            conversation_id=conversation['id'],
            sources=result.get('sources', [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'处理失败: {str(e)}')

@router.get('/conversations')
async def list_conversations():
    """获取所有对话列表"""
    try:
        conversations = conversation_service.list_conversations()
        return {
            'status': 'success',
            'data': conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/conversations/{conversation_id}')
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    try:
        conversation = conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail='对话不存在')
        return {
            'status': 'success',
            'data': conversation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/conversations')
async def create_conversation(title: str = '新对话'):
    """创建新对话"""
    try:
        conversation = conversation_service.create_conversation(title)
        return {
            'status': 'success',
            'data': conversation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/conversations/{conversation_id}')
async def delete_conversation(conversation_id: str):
    """删除对话"""
    try:
        success = conversation_service.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail='对话不存在')
        return {
            'status': 'success',
            'message': '✅ 对话已删除'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/conversations/{conversation_id}/title')
async def update_title(conversation_id: str, title: str):
    """更新对话标题"""
    try:
        success = conversation_service.update_title(conversation_id, title)
        if not success:
            raise HTTPException(status_code=404, detail='对话不存在')
        return {
            'status': 'success',
            'message': '✅ 标题已更新'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/health')
async def health_check():
    """健康检查"""
    return {
        'status': 'healthy',
        'service': 'tcm-diagnosis-rag',
        'version': '2.1.0'
    }

@router.post('/test-rag')
async def test_rag(query: str = '头痛发热怎么办？'):
    """测试RAG功能"""
    try:
        result = llm_service.chat_with_rag(
            message=query,
            conversation_history=[],
            session_id='test'
        )
        return {
            'status': 'success',
            'query': query,
            'response': result['response'],
            'sources': result['sources']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
