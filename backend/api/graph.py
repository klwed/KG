from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from ..modules import kg_qa
from ..modules.auth_service import auth_service
from ..schemas.auth import TokenData
from ..core.security import get_current_user, require_teacher

router = APIRouter(prefix="/graph", tags=["图谱"])


class StudentQuery(BaseModel):
    student_id: str


@router.get("/overview", summary="获取图谱概览")
async def get_overview(limit: int = Query(500, ge=1, le=2000)):
    try:
        data = kg_qa.querier.get_graph_data(limit=limit)
        return {
            "nodes_count": len(data.get("nodes", [])),
            "links_count": len(data.get("links", [])),
            "graph": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}", summary="获取学生掌握情况子图")
async def get_student_graph(student_id: str, depth: int = Query(2, ge=1, le=5)):
    try:
        student = auth_service.get_user_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        username = student.get("username") or student.get("real_name")

        subgraph = kg_qa.querier.get_student_subgraph(username, depth=depth)

        return {
            "student_id": student_id,
            "student_name": username,
            "subgraph": subgraph,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query", summary="按关键词检索相关子图节点")
async def query_graph(
    keyword: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)
):
    try:
        results = kg_qa.querier.search(keyword, limit=limit)
        subgraph = kg_qa.querier.get_subgraph(keyword, depth=2)

        return {"keyword": keyword, "results": results, "subgraph": subgraph}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_name}", summary="获取实体详情")
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


@router.get("/ct-graph", summary="获取计算思维相关子图")
async def get_ct_graph(
    ct_dimension: str = Query(
        ..., description="计算思维维度：分解、模式识别、抽象、算法思维、评估"
    ),
):
    try:
        data = kg_qa.querier.get_ct_related_graph(ct_dimension)
        return {"ct_dimension": ct_dimension, "graph": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export", summary="导出图谱三元组")
async def export_graph():
    try:
        data = kg_qa.querier.get_graph_data(limit=10000)
        triples = [
            {
                "head": l["source"],
                "relation": l["relation"],
                "tail": l["target"],
            }
            for l in data.get("links", [])
        ]
        return {"triples": triples, "total": len(triples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
