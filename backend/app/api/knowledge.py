from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import os
import shutil
import uuid
from datetime import datetime
from app.services.rag_service import rag_service
from app.services.document_parser import DocumentParser

router = APIRouter(tags=["knowledge"])
parser = DocumentParser()

@router.post("/categories")
async def create_category(name: str = Form(...), creator: str = Form(default="admin")):
    """创建知识库类别"""
    try:
        category = rag_service.create_category(name, creator)
        return {
            "status": "success",
            "message": f"✅ 类别「{name}」创建成功！",
            "data": category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def list_categories():
    """获取所有知识库类别"""
    try:
        categories = rag_service.list_categories()
        return {
            "status": "success",
            "data": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    try:
        rag_service.delete_category(category_id)
        return {
            "status": "success",
            "message": "✅ 类别已删除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/categories/{category_id}")
async def rename_category(category_id: str, name: str = Form(...)):
    try:
        for cat in rag_service.categories:
            if cat['id'] == category_id:
                cat['name'] = name
                rag_service._save_data()
                return {
                    "status": "success",
                    "message": "✅ 类别重命名成功"
                }
        raise HTTPException(status_code=404, detail="类别不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category_id: str = Form(...),
    creator: str = Form(default="admin")
):
    try:
        # 读取文件内容
        content = await file.read()

        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        upload_dir = "./data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        # 解析文档
        parse_result = parser.parse(file_path)
        text_content = parse_result['content']

        # 添加到知识库
        doc = rag_service.add_document(
            content=text_content,
            filename=safe_filename,
            file_type=file.filename.split('.')[-1] if '.' in file.filename else 'unknown',
            file_size=len(content),
            category_id=category_id,
            creator=creator
        )

        return {
            "status": "success",
            "message": f"✅ 上传成功！\n\n文件：{file.filename}\n类型：{doc['type']}\n大小：{len(content)} 字节\n知识块：{doc['chunk_count']} 个",
            "data": doc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")

@router.get("/documents")
async def list_documents(
    category_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None
):
    """分页获取文档列表"""
    try:
        result = rag_service.list_documents(
            category_id=category_id,
            page=page,
            page_size=page_size,
            status=status
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    try:
        rag_service.delete_document(doc_id)
        return {
            "status": "success",
            "message": "✅ 文档已删除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{doc_id}/disable")
async def disable_document(doc_id: str):
    """禁用文档"""
    try:
        if rag_service.disable_document(doc_id):
            return {
                "status": "success",
                "message": "✅ 文档已禁用"
            }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{doc_id}/enable")
async def enable_document(doc_id: str):
    """启用文档"""
    try:
        if rag_service.enable_document(doc_id):
            return {
                "status": "success",
                "message": "✅ 文档已启用"
            }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{doc_id}/rename")
async def rename_document(doc_id: str, new_name: str = Form(...)):
    """重命名文档"""
    try:
        if rag_service.rename_document(doc_id, new_name):
            return {
                "status": "success",
                "message": "✅ 文档已重命名"
            }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{doc_id}/migrate")
async def migrate_document(doc_id: str, new_category_id: str = Form(...)):
    try:
        if rag_service.migrate_document(doc_id, new_category_id):
            return {
                "status": "success",
                "message": "✅ 文档已迁移"
            }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{doc_id}/copy")
async def copy_document(doc_id: str, target_category_id: str = Form(...)):
    try:
        import copy
        for doc in rag_service.documents:
            if doc['id'] == doc_id:
                new_doc = copy.deepcopy(doc)
                new_doc['id'] = str(uuid.uuid4())
                new_doc['category_id'] = target_category_id
                new_doc['created_at'] = datetime.now().isoformat()
                new_doc['updated_at'] = datetime.now().isoformat()
                rag_service.documents.append(new_doc)
                rag_service._save_data()
                return {
                    "status": "success",
                    "message": "✅ 文档已复制"
                }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{doc_id}/reupload")
async def reupload_document(doc_id: str, file: UploadFile = File(...)):
    """重新上传文档内容"""
    try:
        content = await file.read()
        text_content = parser.parse(content, file.filename)

        if rag_service.update_document_content(doc_id, text_content):
            return {
                "status": "success",
                "message": "✅ 文档内容已更新"
            }
        raise HTTPException(status_code=404, detail="文档不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats():
    """获取知识库统计信息"""
    try:
        stats = rag_service.get_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
