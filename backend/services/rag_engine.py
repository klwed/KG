from typing import List, Dict, Optional, Tuple
from ..services.vector_store import vector_store
from ..services.neo4j_service import neo4j_client
from ..core.config import get_settings

settings = get_settings()


class RAGEngine:
    def __init__(self):
        self.vector_store = vector_store
        self.kg_client = neo4j_client

    def search_vector(self, query: str, top_k: int = 5) -> List[Dict]:
        return self.vector_store.search(query, top_k)

    def search_kg(self, query: str, top_k: int = 10) -> List[Dict]:
        return self.kg_client.search_by_keyword(query, limit=top_k)

    def dual_search(
        self, query: str, vector_top_k: int = 5, kg_top_k: int = 10
    ) -> Dict:
        vector_results = self.search_vector(query, vector_top_k)
        kg_results = self.search_kg(query, kg_top_k)

        return {
            "vector_results": vector_results,
            "kg_results": kg_results,
            "has_vector_results": len(vector_results) > 0,
            "has_kg_results": len(kg_results) > 0,
        }

    def fuse_results(
        self, vector_results: List[Dict], kg_results: List[Dict], top_k: int = 10
    ) -> List[Dict]:
        seen = set()
        fused = []

        for r in vector_results:
            item = {
                "source": "vector",
                "content": r.get("text", ""),
                "score": r.get("distance", 0),
                "metadata": r,
            }
            key = item["content"]
            if key not in seen:
                seen.add(key)
                fused.append(item)

        for r in kg_results:
            content = f"{r.get('head', '')} {r.get('relation', '')} {r.get('tail', '')}"
            item = {
                "source": "knowledge_graph",
                "content": content,
                "score": 1.0,
                "metadata": r,
                "head": r.get("head"),
                "relation": r.get("relation"),
                "tail": r.get("tail"),
            }
            if content not in seen:
                seen.add(content)
                fused.append(item)

        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:top_k]

    def build_context(self, fused_results: List[Dict]) -> str:
        if not fused_results:
            return ""

        context_parts = ["【参考信息】\n"]

        vector_results = [r for r in fused_results if r["source"] == "vector"]
        if vector_results:
            context_parts.append("【文档相关内容】")
            for r in vector_results[:3]:
                context_parts.append(f"- {r['content']}")
            context_parts.append("")

        kg_results = [r for r in fused_results if r["source"] == "knowledge_graph"]
        if kg_results:
            context_parts.append("【知识图谱相关信息】")
            for r in kg_results[:5]:
                head = r.get("head", "")
                relation = r.get("relation", "")
                tail = r.get("tail", "")
                if head and relation and tail:
                    context_parts.append(f"- {head} --[{relation}]--> {tail}")
            context_parts.append("")

        return "\n".join(context_parts)

    def retrieve(self, query: str) -> Dict:
        search_result = self.dual_search(query)

        fused = self.fuse_results(
            search_result["vector_results"], search_result["kg_results"]
        )

        context = self.build_context(fused)

        return {
            "has_results": len(fused) > 0,
            "fused_results": fused,
            "context": context,
            "vector_count": len(search_result["vector_results"]),
            "kg_count": len(search_result["kg_results"]),
        }


rag_engine = RAGEngine()
