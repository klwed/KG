from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import shutil
from ..modules import process_student_data, import_student_to_kg, generate_report
from ..modules.auth_service import auth_service
from ..modules.student_processor import student_processor
from ..schemas.auth import TokenData
from ..core.security import get_current_user, require_teacher
from ..core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/students", tags=["学生管理"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class StudentUploadResponse(BaseModel):
    filename: str
    student_count: int
    triples_count: int


@router.get("/list", summary="获取所有学生列表")
async def list_students(current_user: TokenData = Depends(require_teacher)):
    try:
        students = auth_service.get_all_students()
        return {"students": students, "total": len(students)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{student_id}/graph", summary="获取指定学生图谱")
async def get_student_graph(
    student_id: str, current_user: TokenData = Depends(require_teacher)
):
    try:
        student = auth_service.get_user_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        username = student.get("username") or student.get("real_name")

        csv_path = DATA_DIR / "students.csv"
        if not csv_path.exists():
            return {"message": "暂无学生成绩数据", "graph": None}

        students = student_processor.load_from_csv(str(csv_path))
        student_data = student_processor.get_student_by_name(students, username)

        if not student_data:
            return {"message": "未找到该学生成绩", "graph": None}

        from ..modules import kg_qa

        subgraph = kg_qa.querier.get_student_subgraph(username, depth=2)

        return {
            "student_id": student_id,
            "student_name": username,
            "student_data": student_data,
            "graph": subgraph,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", summary="所有学生掌握情况汇总")
async def get_students_overview(current_user: TokenData = Depends(require_teacher)):
    try:
        result = process_student_data()
        return {
            "students": result["summaries"],
            "topic_stats": result["topic_stats"],
            "total_students": len(result["summaries"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", summary="上传学生数据")
async def upload_student_data(
    file: UploadFile = File(...), current_user: TokenData = Depends(require_teacher)
):
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


@router.post("/import", summary="将学生数据导入知识图谱")
async def import_students_to_kg(current_user: TokenData = Depends(require_teacher)):
    try:
        result = import_student_to_kg()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report", summary="生成学生掌握情况报告")
async def get_report(current_user: TokenData = Depends(require_teacher)):
    try:
        report = generate_report()
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
