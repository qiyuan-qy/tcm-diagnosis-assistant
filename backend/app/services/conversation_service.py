from typing import List, Dict, Optional
import os
import json
from datetime import datetime
import uuid

class ConversationService:
    """对话历史管理服务"""
    
    def __init__(self):
        self.persist_file = './data/conversations.json'
        os.makedirs('./data', exist_ok=True)
        self._load_data()
    
    def _load_data(self):
        if os.path.exists(self.persist_file):
            with open(self.persist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.conversations = data.get('conversations', [])
        else:
            self.conversations = []
            self._save_data()
    
    def _save_data(self):
        with open(self.persist_file, 'w', encoding='utf-8') as f:
            json.dump({'conversations': self.conversations}, f, ensure_ascii=False, indent=2)
    
    def create_conversation(self, title: str = '新对话') -> Dict:
        """创建新对话"""
        conversation = {
            'id': str(uuid.uuid4()),
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': []
        }
        self.conversations.insert(0, conversation)
        self._save_data()
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """获取对话详情"""
        for conv in self.conversations:
            if conv['id'] == conversation_id:
                return conv
        return None
    
    def list_conversations(self) -> List[Dict]:
        """获取所有对话列表"""
        return self.conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        original_len = len(self.conversations)
        self.conversations = [c for c in self.conversations if c['id'] != conversation_id]
        self._save_data()
        return len(self.conversations) < original_len
    
    def add_message(self, conversation_id: str, role: str, content: str, sources: List = None) -> Dict:
        """添加消息到对话"""
        for conv in self.conversations:
            if conv['id'] == conversation_id:
                message = {
                    'role': role,
                    'content': content,
                    'timestamp': datetime.now().isoformat(),
                    'sources': sources or []
                }
                conv['messages'].append(message)
                conv['updated_at'] = datetime.now().isoformat()
                
                if len(conv['messages']) == 1 and role == 'user':
                    conv['title'] = content[:30] + ('...' if len(content) > 30 else '')
                
                self.conversations.remove(conv)
                self.conversations.insert(0, conv)
                self._save_data()
                return message
        return None
    
    def update_title(self, conversation_id: str, title: str) -> bool:
        """更新对话标题"""
        for conv in self.conversations:
            if conv['id'] == conversation_id:
                conv['title'] = title
                conv['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

conversation_service = ConversationService()
