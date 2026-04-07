from typing import List, Dict
from ..services.llm_service import llm_service


class RelationExtractor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def extract_triples(self, text: str, source: str = "") -> List[Dict]:
        return llm_service.extract_triples(text, source)

    def extract_batch(
        self, chunks: List[Dict], source: str = "", progress_callback=None
    ) -> List[Dict]:
        all_triples = []
        for i, chunk in enumerate(chunks):
            try:
                text = chunk.get("text", chunk) if isinstance(chunk, dict) else chunk
                triples = self.extract_triples(text, source)
                all_triples.extend(triples)
                print(f"  块 {i + 1}/{len(chunks)}: 提取到 {len(triples)} 个三元组")
                if progress_callback:
                    progress_callback(
                        {
                            "current": i + 1,
                            "total": len(chunks),
                            "progress": int((i + 1) / len(chunks) * 100),
                            "triples_count": len(all_triples),
                        }
                    )
            except Exception as e:
                print(f"  块 {i + 1} 处理失败: {e}")
                if progress_callback:
                    progress_callback(
                        {
                            "current": i + 1,
                            "total": len(chunks),
                            "progress": int((i + 1) / len(chunks) * 100),
                            "error": str(e),
                        }
                    )
                continue
        return all_triples

    def triples_to_table(self, triples: List[Dict]) -> str:
        if not triples:
            return "暂无三元组数据"
        return llm_service.triples_to_table(triples)

    def get_statistics(self, triples: List[Dict]) -> Dict:
        entity_types = {}
        relation_types = {}
        ct_dimensions = {"分解": 0, "模式识别": 0, "抽象": 0, "算法思维": 0, "评估": 0}

        for t in triples:
            entity_types[t.get("head_type", "Unknown")] = (
                entity_types.get(t.get("head_type"), 0) + 1
            )
            entity_types[t.get("tail_type", "Unknown")] = (
                entity_types.get(t.get("tail_type"), 0) + 1
            )
            relation_types[t.get("relation", "Unknown")] = (
                relation_types.get(t.get("relation"), 0) + 1
            )

            if t.get("tail") in ct_dimensions or t.get("head") in ct_dimensions:
                if t.get("tail") in ct_dimensions:
                    ct_dimensions[t.get("tail")] += 1
                if t.get("head") in ct_dimensions:
                    ct_dimensions[t.get("head")] += 1

        return {
            "total_triples": len(triples),
            "entity_types": entity_types,
            "relation_types": relation_types,
            "ct_dimensions": ct_dimensions,
        }


relation_extractor = RelationExtractor()
