from typing import List, Dict, Optional
import os
import json
from datetime import datetime
import uuid

class RAGService:
    def __init__(self):
        self.persist_file = './data/knowledge_base.json'
        os.makedirs('./data', exist_ok=True)
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.persist_file):
            with open(self.persist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.categories = data.get('categories', [])
                self.documents = data.get('documents', [])
        else:
            self.categories = []
            self.documents = []
            self._save_data()

    def _save_data(self):
        with open(self.persist_file, 'w', encoding='utf-8') as f:
            json.dump({'categories': self.categories, 'documents': self.documents}, f, ensure_ascii=False, indent=2)

    def create_category(self, name: str, creator: str = 'admin') -> Dict:
        category = {'id': str(uuid.uuid4()), 'name': name, 'creator': creator, 'created_at': datetime.now().isoformat(), 'document_count': 0}
        self.categories.append(category)
        self._save_data()
        return category

    def list_categories(self) -> List[Dict]:
        for cat in self.categories:
            cat['document_count'] = len([d for d in self.documents if d.get('category_id') == cat['id']])
        return self.categories

    def delete_category(self, category_id: str) -> bool:
        self.categories = [c for c in self.categories if c['id'] != category_id]
        self.documents = [d for d in self.documents if d.get('category_id') != category_id]
        self._save_data()
        return True

    def add_document(self, content: str, filename: str, file_type: str, file_size: int, category_id: str, creator: str = 'admin') -> Dict:
        chunk_size = 500
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append({'id': str(uuid.uuid4()), 'content': content[i:i+chunk_size], 'index': i // chunk_size})
        doc = {'id': str(uuid.uuid4()), 'filename': filename, 'original_filename': filename, 'type': file_type, 'size': file_size, 'category_id': category_id, 'chunks': chunks, 'chunk_count': len(chunks), 'status': 'enabled', 'creator': creator, 'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()}
        self.documents.append(doc)
        self._save_data()
        return doc

    def list_documents(self, category_id: Optional[str] = None, page: int = 1, page_size: int = 10, status: Optional[str] = None) -> Dict:
        filtered_docs = self.documents
        if category_id:
            filtered_docs = [d for d in filtered_docs if d.get('category_id') == category_id]
        if status:
            filtered_docs = [d for d in filtered_docs if d.get('status') == status]
        total = len(filtered_docs)
        start = (page - 1) * page_size
        paged_docs = filtered_docs[start:start + page_size]
        return {'documents': paged_docs, 'total': total, 'page': page, 'page_size': page_size, 'total_pages': (total + page_size - 1) // page_size}

    def delete_document(self, doc_id: str) -> bool:
        self.documents = [d for d in self.documents if d['id'] != doc_id]
        self._save_data()
        return True

    def disable_document(self, doc_id: str) -> bool:
        for doc in self.documents:
            if doc['id'] == doc_id:
                doc['status'] = 'disabled'
                doc['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def enable_document(self, doc_id: str) -> bool:
        for doc in self.documents:
            if doc['id'] == doc_id:
                doc['status'] = 'enabled'
                doc['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def rename_document(self, doc_id: str, new_name: str) -> bool:
        for doc in self.documents:
            if doc['id'] == doc_id:
                doc['original_filename'] = new_name
                doc['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def migrate_document(self, doc_id: str, new_category_id: str) -> bool:
        for doc in self.documents:
            if doc['id'] == doc_id:
                doc['category_id'] = new_category_id
                doc['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def update_document_content(self, doc_id: str, new_content: str) -> bool:
        for doc in self.documents:
            if doc['id'] == doc_id:
                chunk_size = 500
                chunks = []
                for i in range(0, len(new_content), chunk_size):
                    chunks.append({'id': str(uuid.uuid4()), 'content': new_content[i:i+chunk_size], 'index': i // chunk_size})
                doc['chunks'] = chunks
                doc['chunk_count'] = len(chunks)
                doc['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def similarity_search(self, query: str, k: int = 3, category_id: Optional[str] = None) -> List[Dict]:
        results = []
        query_lower = query.lower()
        enabled_docs = [d for d in self.documents if d.get('status') == 'enabled']
        if category_id:
            enabled_docs = [d for d in enabled_docs if d.get('category_id') == category_id]
        for doc in enabled_docs:
            for chunk in doc.get('chunks', []):
                content = chunk['content'].lower()
                if any(word in content for word in query_lower.split()[:5]):
                    results.append({'content': chunk['content'], 'metadata': {'filename': doc['original_filename'], 'doc_id': doc['id'], 'category_id': doc['category_id']}, 'score': query_lower.count(chunk['content'][:50].lower())})
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]

    def get_stats(self) -> Dict:
        enabled_docs = [d for d in self.documents if d.get('status') == 'enabled']
        return {'total_categories': len(self.categories), 'total_documents': len(self.documents), 'enabled_documents': len(enabled_docs), 'total_chunks': sum(d['chunk_count'] for d in enabled_docs), 'collection_name': 'tcm_knowledge'}

rag_service = RAGService()
