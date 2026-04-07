from typing import List, Dict, Optional
from neo4j import GraphDatabase
from ..core.config import get_settings

settings = get_settings()


class KGImporter:
    _instance = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
            )
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def _run_query(self, query: str, params: Dict = None) -> List[Dict]:
        driver = self.connect()
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def import_triples(self, triples: List[Dict]) -> Dict:
        created_nodes = 0
        created_relations = 0

        for triple in triples:
            head = triple.get("head", "")
            tail = triple.get("tail", "")
            relation = triple.get("relation", "")
            head_type = triple.get("head_type", "Entity")
            tail_type = triple.get("tail_type", "Entity")
            source = triple.get("source", "")

            if not all([head, tail, relation]):
                continue

            head_query = """
            MERGE (h:`{head_type}` {name: $head})
            ON CREATE SET h:__created__
            SET h.source = COALESCE(h.source, []) + $source
            """.format(head_type=head_type)

            tail_query = """
            MERGE (t:`{tail_type}` {name: $tail})
            ON CREATE SET t:__created__
            SET t.source = COALESCE(t.source, []) + $source
            """.format(tail_type=tail_type)

            rel_query = """
            MATCH (h:`{head_type}` {name: $head})
            MATCH (t:`{tail_type}` {name: $tail})
            MERGE (h)-[r:`{relation}`]->(t)
            SET r.source = $source
            """.format(head_type=head_type, tail_type=tail_type, relation=relation)

            try:
                self._run_query(head_query, {"head": head, "source": source})
                self._run_query(tail_query, {"tail": tail, "source": source})
                self._run_query(
                    rel_query, {"head": head, "tail": tail, "source": source}
                )
                created_relations += 1
            except Exception as e:
                print(f"导入三元组失败: {head} --[{relation}]--> {tail}: {e}")

        return {"imported": created_relations, "total_triples": len(triples)}

    def import_from_file(self, file_path: str) -> Dict:
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            triples = json.load(f)
        return self.import_triples(triples)

    def clear_all(self):
        self._run_query("MATCH (n) DETACH DELETE n")

    def get_statistics(self) -> Dict:
        node_count = self._run_query("MATCH (n) RETURN count(n) as count")
        rel_count = self._run_query("MATCH ()-[r]->() RETURN count(r) as count")

        node_types = self._run_query("""
            MATCH (n)
            UNWIND labels(n) as label
            WHERE NOT label STARTS WITH '__'
            RETURN label, count(*) as count
        """)

        rel_types = self._run_query("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
        """)

        return {
            "node_count": node_count[0]["count"] if node_count else 0,
            "relation_count": rel_count[0]["count"] if rel_count else 0,
            "node_types": {r["label"]: r["count"] for r in node_types},
            "relation_types": {r["type"]: r["count"] for r in rel_types},
        }


kg_importer = KGImporter()
