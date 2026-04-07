from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pathlib import Path
import shutil
import json
import io

from ..core.config import get_settings
from ..modules import (
    document_processor,
    relation_extractor,
    kg_importer,
    kg_qa,
    process_student_data,
    import_student_to_kg,
    generate_report,
)
from ..schemas.schemas import Triple
from ..schemas.auth import TokenData
from ..core.security import get_current_user, require_teacher
from ..modules.student_processor import student_processor
from .auth import router as auth_router

settings = get_settings()

app = FastAPI(title="知识图谱问答系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    return {
        "message": "知识图谱问答系统 API v2.0",
        "modules": ["document", "extract", "kg", "qa"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/document/process")
async def process_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    file_path = DOCUMENTS_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = document_processor.process_document(str(file_path))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/api/document/list")
async def list_documents():
    files = []
    for f in DOCUMENTS_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".doc", ".txt"]:
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                }
            )
    return {"documents": files}


@app.post("/api/extract")
async def extract_triples(file_path: str = Body(...)):
    full_path = (
        DOCUMENTS_DIR / file_path
        if not Path(file_path).is_absolute()
        else Path(file_path)
    )

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        result = document_processor.process_document(str(full_path))
        chunks = result["chunks"]

        triples = relation_extractor.extract_batch(chunks, source=file_path)
        stats = relation_extractor.get_statistics(triples)

        return {
            "filename": full_path.name,
            "chunks_processed": len(chunks),
            "total_triples": len(triples),
            "statistics": stats,
            "triples": [Triple(**t) for t in triples],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"抽取失败: {str(e)}")


@app.post("/api/extract/all")
async def extract_all_documents():
    results = []
    for f in DOCUMENTS_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".doc", ".txt"]:
            try:
                result = document_processor.process_document(str(f))
                chunks = result["chunks"]

                triples = relation_extractor.extract_batch(chunks, source=f.name)

                results.append(
                    {"filename": f.name, "chunks": len(chunks), "triples": len(triples)}
                )
            except Exception as e:
                results.append({"filename": f.name, "error": str(e)})

    return {"results": results}


@app.get("/api/extract/table")
async def get_triples_table(limit: int = 100):
    from ..services.neo4j_service import neo4j_client

    try:
        data = neo4j_client.get_graph_data(limit=1000)
        triples = [
            {
                "head": l["source"],
                "head_type": next(
                    (n["type"] for n in data["nodes"] if n["id"] == l["source"]),
                    "Entity",
                ),
                "relation": l["relation"],
                "tail": l["target"],
                "tail_type": next(
                    (n["type"] for n in data["nodes"] if n["id"] == l["target"]),
                    "Entity",
                ),
                "source": "",
            }
            for l in data["links"]
        ]

        table = relation_extractor.triples_to_table(triples[:limit])
        return {"table": table, "total": len(triples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/kg/import")
async def import_triples(request: dict = Body(...)):
    triples = request.get("triples", [])
    if not triples:
        raise HTTPException(status_code=400, detail="没有三元组数据")

    try:
        result = kg_importer.import_triples(triples)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@app.post("/api/kg/import/file")
async def import_from_file(file_path: str = Body(...)):
    try:
        result = kg_importer.import_from_file(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@app.delete("/api/kg/clear")
async def clear_kg():
    try:
        kg_importer.clear_all()
        return {"message": "知识图谱已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/stats")
async def get_kg_stats():
    try:
        stats = kg_importer.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/graph")
async def get_graph_data(limit: int = 500):
    try:
        data = kg_qa.querier.get_graph_data(limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/search")
async def search_kg(keyword: str, limit: int = 20):
    try:
        results = kg_qa.querier.search(keyword, limit=limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/qa")
async def ask_question(request: dict = Body(...)):
    question = request.get("question", "")
    use_kg_only = request.get("use_kg_only", False)
    username = request.get("username", None)

    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        result = kg_qa.ask(question, use_kg_only=use_kg_only, username=username)
        return {
            "answer": result["answer"],
            "source": result["source"],
            "related_triples": result["related_triples"],
            "subgraph": result.get("subgraph"),
            "personal_scores": result.get("personal_scores"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@app.get("/api/kg/subgraph")
async def get_subgraph(keyword: str, depth: int = 2):
    try:
        data = kg_qa.querier.get_subgraph(keyword, depth=depth)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/ct-graph")
async def get_ct_graph(ct_dimension: str):
    try:
        data = kg_qa.querier.get_ct_related_graph(ct_dimension)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/export")
async def export_triples():
    try:
        data = kg_qa.querier.get_graph_data(limit=10000)
        triples = [
            {
                "head": l["source"],
                "relation": l["relation"],
                "tail": l["target"],
                "source": "",
            }
            for l in data["links"]
        ]

        return Response(
            content=json.dumps(triples, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=triples.json"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kg/entity/{entity_name}")
async def get_entity_details(entity_name: str):
    try:
        details = kg_qa.querier.get_entity_details(entity_name)
        if not details:
            raise HTTPException(status_code=404, detail="实体不存在")
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/student/summary")
async def get_student_summary():
    try:
        result = process_student_data()
        return {"students": result["summaries"], "topic_stats": result["topic_stats"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/student/import")
async def import_student_data():
    try:
        result = import_student_to_kg()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/student/report")
async def get_student_report():
    try:
        report = generate_report()
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/student/upload")
async def upload_student_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400, detail="不支持的文件格式，仅支持 CSV、Excel"
        )

    file_path = DATA_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = process_student_data(str(file_path))
        return {
            "filename": file.filename,
            "student_count": len(result["students"]),
            "triples_count": len(result["triples"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/api/student/my-scores")
async def get_my_scores(
    username: str, current_user: TokenData = Depends(get_current_user)
):
    csv_path = DATA_DIR / "students.csv"
    if not csv_path.exists():
        return {"scores": None, "message": "暂无成绩数据"}

    students = student_processor.load_from_csv(str(csv_path))
    scores = student_processor.get_student_by_name(students, username)

    if not scores:
        return {"scores": None, "message": "未找到您的成绩记录"}

    return {"scores": scores}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
