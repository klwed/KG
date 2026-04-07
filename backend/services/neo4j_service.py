from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
from ..core.config import get_settings

settings = get_settings()


class Neo4jClient:
    _instance: Optional["Neo4jClient"] = None
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

    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        driver = self.connect()
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def create_entities_and_relations(self, triples: List[Dict]):
        for triple in triples:
            head = triple.get("head")
            relation = triple.get("relation")
            tail = triple.get("tail")
            head_type = triple.get("head_type", "Entity")
            tail_type = triple.get("tail_type", "Entity")
            source = triple.get("source", "")

            cypher = """
            MERGE (h:`{head_type}` {{name: $head}})
            MERGE (t:`{tail_type}` {{name: $tail}})
            MERGE (h)-[r:`{relation}`]->(t)
            SET r.source = $source
            """.format(head_type=head_type, tail_type=tail_type, relation=relation)

            self.execute_query(cypher, {"head": head, "tail": tail, "source": source})

    def search_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict]:
        query = """
        MATCH (n)-[r]-(m)
        WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
        RETURN n.name as head, labels(n)[0] as head_type, 
               type(r) as relation, m.name as tail,
               labels(m)[0] as tail_type
        LIMIT $limit
        """
        return self.execute_query(query, {"keyword": keyword, "limit": limit})

    def get_graph_data(self, limit: int = 500) -> Dict:
        query = """
        MATCH (n)-[r]->(m)
        RETURN n.name as source, labels(n)[0] as source_type,
               type(r) as relation, m.name as target,
               labels(m)[0] as target_type
        LIMIT $limit
        """
        links = self.execute_query(query, {"limit": limit})

        nodes_set = set()
        nodes = []
        links_formatted = []

        for link in links:
            if link["source"] not in nodes_set:
                nodes_set.add(link["source"])
                nodes.append({"id": link["source"], "type": link["source_type"]})
            if link["target"] not in nodes_set:
                nodes_set.add(link["target"])
                nodes.append({"id": link["target"], "type": link["target_type"]})

            links_formatted.append(
                {
                    "source": link["source"],
                    "target": link["target"],
                    "relation": link["relation"],
                }
            )

        return {"nodes": nodes, "links": links_formatted}

    def delete_all(self):
        self.execute_query("MATCH (n) DETACH DELETE n")


neo4j_client = Neo4jClient()
