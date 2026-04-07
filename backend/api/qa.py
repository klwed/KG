from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
from ..modules import kg_qa
from ..services.rag_engine import rag_engine
from ..modules.auth_service import auth_service
from ..schemas.auth import TokenData
from ..core.security import get_current_user

router = APIRouter(prefix="/qa", tags=["问答"])


class AskRequest(BaseModel):
    question: str
    use_kg_only: bool = False
    username: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    source: str
    related_triples: List[Dict]
    subgraph: Optional[Dict] = None
    personal_scores: Optional[Dict] = None
    use_rag: bool = False


@router.post("/ask", response_model=AskResponse, summary="问答接口")
async def ask_question(request: AskRequest):
    if not request.question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        rag_result = rag_engine.retrieve(request.question)
        use_rag = rag_result["has_results"] and not request.use_kg_only

        if use_rag:
            kg_context = rag_result["context"]
            source = "RAG"
        else:
            kg_context = ""
            source = "LLM" if not request.use_kg_only else "knowledge_graph"

        personal_scores = None
        if request.username and kg_qa.check_personal_question(
            request.question, request.username
        ):
            personal_scores = kg_qa.get_student_scores(request.username)

        if request.use_kg_only:
            related_triples = (
                rag_result["fused_results"] if rag_result["has_results"] else []
            )
            subgraph = None
            if related_triples:
                keywords = [
                    r.get("head") or r.get("content", "") for r in related_triples
                ]
                if keywords:
                    subgraph = kg_qa.querier.get_subgraph(keywords[0], depth=2)

            return AskResponse(
                answer=kg_qa._generate_kg_answer(related_triples, request.question),
                source="knowledge_graph",
                related_triples=related_triples,
                subgraph=subgraph,
                personal_scores=personal_scores,
                use_rag=False,
            )

        answer = kg_qa._llm_answer(
            request.question,
            kg_context,
            [],
            kg_qa.format_personal_context(personal_scores, request.question)
            if personal_scores
            else "",
        )

        related_triples = (
            rag_result["fused_results"] if rag_result["has_results"] else []
        )
        subgraph = None
        if rag_result["has_results"]:
            keywords = [r.get("head") or r.get("content", "") for r in related_triples]
            if keywords:
                subgraph = kg_qa.querier.get_subgraph(keywords[0], depth=2)

        return AskResponse(
            answer=answer,
            source=source,
            related_triples=related_triples,
            subgraph=subgraph,
            personal_scores=personal_scores,
            use_rag=use_rag,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@router.get("/history", summary="获取问答历史")
async def get_history(limit: int = 20, current_user: TokenData = None):
    return {"history": [], "message": "历史记录功能待实现"}
