import os
import docx
import PyPDF2
from typing import List, Dict
from pathlib import Path
import re

class DocumentParser:
    """文档解析器 - 支持.docx, .md, .pdf"""
    
    def __init__(self):
        self.supported_formats = ['.docx', '.md', '.pdf', '.txt']
    
    def parse(self, file_path: str) -> Dict[str, any]:
        """解析文档"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        if suffix == '.docx':
            content = self._parse_docx(file_path)
        elif suffix == '.pdf':
            content = self._parse_pdf(file_path)
        else:  # .md or .txt
            content = self._parse_text(file_path)
        
        # 清理文本
        content = self._clean_text(content)
        
        return {
            'filename': path.name,
            'content': content,
            'type': suffix[1:],  # 去掉点号
            'size': path.stat().st_size,
            'line_count': len(content.split('\n'))
        }
    
    def _parse_docx(self, file_path: str) -> str:
        """解析Word文档"""
        doc = docx.Document(file_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text.strip())
        
        return '\n'.join(paragraphs)
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文档"""
        text = []
        
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text.strip():
                    text.append(page_text.strip())
        
        return '\n'.join(text)
    
    def _parse_text(self, file_path: str) -> str:
        """解析文本文件(.md, .txt)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """将文本分块"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap if end < text_length else text_length
        
        return chunks

document_parser = DocumentParser()
