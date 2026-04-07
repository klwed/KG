from typing import List, Dict, Optional
from neo4j import GraphDatabase
from openai import OpenAI
from ..core.config import get_settings

settings = get_settings()


class KGQuerier:
    _instance = None
    _driver = None
    _llm_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _connect_neo4j(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
            )
        return self._driver

    def _connect_llm(self):
        if self._llm_client is None:
            self._llm_client = OpenAI(
                api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url
            )
        return self._llm_client

    def _run_query(self, query: str, params: Dict = None) -> List[Dict]:
        driver = self._connect_neo4j()
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def search(self, keyword: str, limit: int = 20) -> List[Dict]:
        query = """
        MATCH (n)-[r]-(m)
        WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
        RETURN n.name as head, labels(n)[0] as head_type,
               type(r) as relation, m.name as tail,
               labels(m)[0] as tail_type
        LIMIT $limit
        """
        return self._run_query(query, {"keyword": keyword, "limit": limit})

    def search_by_entity(self, entity_name: str) -> Dict:
        query = """
        MATCH (n {name: $name})
        OPTIONAL MATCH (n)-[r_out]->(out)
        OPTIONAL MATCH (in)-[r_in]->(n)
        RETURN n.name as entity, labels(n)[0] as type,
               collect(DISTINCT {target: out.name, relation: type(r_out), direction: 'out'}) as outgoing,
               collect(DISTINCT {source: in.name, relation: type(r_in), direction: 'in'}) as incoming
        """
        results = self._run_query(query, {"name": entity_name})
        return results[0] if results else None

    def search_by_ct_dimension(self, ct_dimension: str) -> List[Dict]:
        query = """
        MATCH (k)-[r {relation: '体现'}]->(ct {name: $dimension})
        RETURN k.name as knowledge, labels(k)[0] as knowledge_type,
               ct.name as ct_dimension
        """
        return self._run_query(query, {"dimension": ct_dimension})

    def get_entity_details(self, entity_name: str) -> Dict:
        query = """
        MATCH (n {name: $name})
        OPTIONAL MATCH (n)-[r_out]->(out)
        OPTIONAL MATCH (in)-[r_in]->(n)
        OPTIONAL MATCH path = (n)-[*1..2]-(related)
        WITH n, 
             collect(DISTINCT {target: out.name, relation: type(r_out), target_type: labels(out)[0]}) as outgoing,
             collect(DISTINCT {source: in.name, relation: type(r_in), source_type: labels(in)[0]}) as incoming,
             collect(DISTINCT {node: related.name, type: labels(related)[0]}) as related_nodes
        RETURN n.name as name, labels(n)[0] as type,
               [x IN outgoing WHERE x.target IS NOT NULL] as outgoing,
               [x IN incoming WHERE x.source IS NOT NULL] as incoming,
               [x IN related_nodes WHERE x.node IS NOT NULL AND x.node <> n.name] as related
        """
        results = self._run_query(query, {"name": entity_name})
        return results[0] if results else None

    def get_neighbors(self, entity_name: str, depth: int = 1) -> Dict:
        query = """
        MATCH path = (center {name: $name})-[*0..{depth}]-(connected)
        UNWIND nodes(path) as n
        UNWIND relationships(path) as r
        WITH collect(DISTINCT n) as nodes, collect(DISTINCT r) as rels
        RETURN nodes, rels
        """.format(depth=depth)

        results = self._run_query(query, {"name": entity_name})
        return results[0] if results else None

    def get_graph_data(self, limit: int = 500) -> Dict:
        query = """
        MATCH (n)-[r]->(m)
        RETURN n.name as source, labels(n)[0] as source_type,
               type(r) as relation, m.name as target,
               labels(m)[0] as target_type
        LIMIT $limit
        """
        links = self._run_query(query, {"limit": limit})

        nodes_dict = {}
        links_formatted = []

        for link in links:
            src, tgt = link["source"], link["target"]
            if src not in nodes_dict:
                nodes_dict[src] = {"id": src, "type": link["source_type"]}
            if tgt not in nodes_dict:
                nodes_dict[tgt] = {"id": tgt, "type": link["target_type"]}

            links_formatted.append(
                {"source": src, "target": tgt, "relation": link["relation"]}
            )

        return {"nodes": list(nodes_dict.values()), "links": links_formatted}

    def get_subgraph(self, keyword: str, depth: int = 2) -> Dict:
        """获取与关键词相关的子图谱，支持多级展示"""
        query = """
        MATCH (n)
        WHERE n.name CONTAINS $keyword
        WITH n
        OPTIONAL MATCH path = (n)-[r1*0..2]-(connected)
        WITH nodes(path) as ns, relationships(path) as rs
        UNWIND ns as node
        WITH collect(DISTINCT node) as all_nodes, rs
        UNWIND all_nodes as n
        WITH n, rs
        OPTIONAL MATCH (n)-[r]->(m)
        WITH collect(DISTINCT {source: n.name, source_type: labels(n)[0], 
                               relation: type(r), target: m.name, target_type: labels(m)[0]}) as links
        UNWIND links as link
        WITH link WHERE link.source IS NOT NULL
        RETURN link.source as source, link.source_type as source_type,
               link.relation as relation, link.target as target, link.target_type as target_type
        """

        links = self._run_query(query, {"keyword": keyword})

        nodes_dict = {}
        links_formatted = []

        for link in links:
            if not link.get("source") or not link.get("target"):
                continue
            src, tgt = link["source"], link["target"]
            if src not in nodes_dict:
                nodes_dict[src] = {
                    "id": src,
                    "type": link.get("source_type") or "Entity",
                }
            if tgt not in nodes_dict:
                nodes_dict[tgt] = {
                    "id": tgt,
                    "type": link.get("target_type") or "Entity",
                }

            links_formatted.append(
                {
                    "source": src,
                    "target": tgt,
                    "relation": link.get("relation") or "关联",
                }
            )

        return {"nodes": list(nodes_dict.values()), "links": links_formatted}

    def get_ct_related_graph(self, ct_dimension: str) -> Dict:
        """获取计算思维相关的完整子图：课程 --计算思维-- 课程"""
        query = """
        MATCH (course1)-[:包含]->(k1)-[:体现]->(ct:CT {name: $ct})
        MATCH (course2)-[:包含]->(k2)-[:体现]->(ct)
        WHERE course1 <> course2
        WITH course1, course2, k1, k2, ct
        OPTIONAL MATCH (k1)-[d:描述]->(tag1)
        OPTIONAL MATCH (k2)-[d2:描述]->(tag2)
        RETURN 
            course1.name as course1, course2.name as course2,
            k1.name as knowledge1, k2.name as knowledge2,
            ct.name as ct_dimension,
            collect(DISTINCT tag1.name) as tags1,
            collect(DISTINCT tag2.name) as tags2
        """

        results = self._run_query(query, {"ct": ct_dimension})

        nodes_dict = {}
        links_formatted = []

        for r in results:
            c1, c2 = r.get("course1"), r.get("course2")
            k1, k2 = r.get("knowledge1"), r.get("knowledge2")
            ct = r.get("ct_dimension")

            if c1 and c1 not in nodes_dict:
                nodes_dict[c1] = {"id": c1, "type": "课程"}
            if c2 and c2 not in nodes_dict:
                nodes_dict[c2] = {"id": c2, "type": "课程"}
            if k1 and k1 not in nodes_dict:
                nodes_dict[k1] = {"id": k1, "type": "知识点"}
            if k2 and k2 not in nodes_dict:
                nodes_dict[k2] = {"id": k2, "type": "知识点"}
            if ct and ct not in nodes_dict:
                nodes_dict[ct] = {"id": ct, "type": "计算思维"}

            if k1 and ct:
                links_formatted.append({"source": k1, "target": ct, "relation": "体现"})
            if k2 and ct:
                links_formatted.append({"source": k2, "target": ct, "relation": "体现"})
            if c1 and k1:
                links_formatted.append({"source": c1, "target": k1, "relation": "包含"})
            if c2 and k2:
                links_formatted.append({"source": c2, "target": k2, "relation": "包含"})

        return {"nodes": list(nodes_dict.values()), "links": links_formatted}


class KGQA:
    def __init__(self):
        self.querier = KGQuerier()
        self.conversations = {}

    def get_student_scores(self, username: str) -> Dict:
        """获取学生的知识点掌握情况"""
        from .student_processor import student_processor
        from pathlib import Path

        csv_path = Path(__file__).parent.parent.parent / "data" / "students.csv"
        if not csv_path.exists():
            return None

        students = student_processor.load_from_csv(str(csv_path))
        scores = student_processor.get_student_by_name(students, username)
        return scores

    def check_personal_question(self, question: str, username: str) -> bool:
        """检查是否是个人相关问题"""
        keywords = ["我", "我的", "自己", "个人", "掌握情况", "学习情况", "成绩"]
        return any(kw in question for kw in keywords) and username

    def format_personal_context(self, scores: Dict, question: str) -> str:
        """格式化学生个人数据为上下文"""
        if not scores:
            return ""

        context = f"\n【当前用户个人信息】\n"
        context += f"学生: {scores.get('name', '未知')}\n"
        context += f"平均掌握程度: {scores.get('level', '未知')}\n"
        context += f"平均得分: {scores.get('avgScore', 0) * 100:.0f}%\n"

        if scores.get("strong"):
            context += f"强项: {', '.join(scores['strong'])}\n"
        if scores.get("weak"):
            context += f"薄弱点: {', '.join(scores['weak'])}\n"

        context += "\n各知识点详情:\n"
        for detail in scores.get("details", [])[:8]:
            context += f"  - {detail['topic']}: {detail['level']} ({detail['score'] * 100:.0f}%)\n"

        return context

    def ask(
        self,
        question: str,
        use_kg_only: bool = False,
        session_id: str = "default",
        conversation_history: List[Dict] = None,
        username: str = None,
    ) -> Dict:

        context_triples = []
        context_entities = set()
        personal_scores = None

        if username and self.check_personal_question(question, username):
            personal_scores = self.get_student_scores(username)

        if conversation_history:
            for hist in conversation_history[-5:]:
                if "related_triples" in hist and hist["related_triples"]:
                    context_triples.extend(hist["related_triples"])
                    for t in hist["related_triples"]:
                        context_entities.add(t.get("head"))
                        context_entities.add(t.get("tail"))

        current_triples = self.querier.search(question, limit=15)

        if current_triples:
            context_triples.extend(current_triples)
            for t in current_triples:
                context_entities.add(t.get("head"))
                context_entities.add(t.get("tail"))

        context_triples = context_triples[-30:]

        subgraph = None
        if current_triples:
            keywords = [t["head"] for t in current_triples] + [
                t["tail"] for t in current_triples
            ]
            keyword = keywords[0] if keywords else question
            subgraph = self.querier.get_subgraph(keyword, depth=2)

            ct_keywords = ["分解", "模式识别", "抽象", "算法思维", "评估", "算法"]
            for kw in keywords:
                if kw in ct_keywords:
                    subgraph = self.querier.get_ct_related_graph(kw)
                    break

        if context_triples:
            kg_context = self._format_kg_context(context_triples)

            personal_context = ""
            if personal_scores:
                personal_context = self.format_personal_context(
                    personal_scores, question
                )

            if use_kg_only:
                return {
                    "answer": self._generate_kg_answer(context_triples, question),
                    "source": "knowledge_graph",
                    "related_triples": context_triples,
                    "subgraph": subgraph,
                    "personal_scores": personal_scores,
                }
            else:
                answer = self._llm_answer(
                    question, kg_context, conversation_history or [], personal_context
                )
                return {
                    "answer": answer,
                    "source": "knowledge_graph + LLM",
                    "related_triples": context_triples,
                    "subgraph": subgraph,
                    "personal_scores": personal_scores,
                }
        else:
            personal_context = ""
            if personal_scores:
                personal_context = self.format_personal_context(
                    personal_scores, question
                )

            if use_kg_only:
                return {
                    "answer": "抱歉，知识图谱中没有找到相关信息。",
                    "source": "none",
                    "related_triples": [],
                    "subgraph": None,
                    "personal_scores": personal_scores,
                }
            else:
                answer = self._llm_answer(
                    question, "", conversation_history or [], personal_context
                )
                return {
                    "answer": answer,
                    "source": "LLM",
                    "related_triples": [],
                    "subgraph": None,
                    "personal_scores": personal_scores,
                }

    def _format_kg_context(self, triples: List[Dict]) -> str:
        lines = []
        for t in triples:
            lines.append(f"- {t['head']} --[{t['relation']}]--> {t['tail']}")
        return "\n".join(lines)

    def _generate_kg_answer(self, triples: List[Dict], question: str) -> str:
        if not triples:
            return "没有找到相关信息。"

        entities = set()
        relations = {}
        for t in triples:
            entities.add(t["head"])
            entities.add(t["tail"])
            rel = t["relation"]
            if rel not in relations:
                relations[rel] = []
            relations[rel].append((t["head"], t["tail"]))

        answer = f"根据知识图谱，我找到了以下相关信息：\n\n"
        answer += f"涉及实体：{', '.join(list(entities)[:10])}...\n\n"

        for rel, pairs in relations.items():
            answer += f"【{rel}】\n"
            for h, t in pairs[:5]:
                answer += f"  • {h} → {t}\n"
            answer += "\n"

        return answer

    def _llm_answer(
        self,
        question: str,
        kg_context: str,
        conversation_history: List[Dict] = None,
        personal_context: str = "",
    ) -> str:
        client = self.querier._connect_llm()

        system_prompt = """你是一个专业的知识图谱问答助手。如果知识图谱中有相关信息，优先基于知识图谱内容回答。
        如果知识图谱中没有相关信息，请基于你的知识库回答。
        回答要简洁、专业、清晰。如果用户追问，请结合之前的对话上下文回答。
        如果用户提供个人信息（如个人掌握情况），请结合这些信息给出针对性的回答。"""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for hist in conversation_history[-5:]:
                messages.append({"role": "user", "content": hist.get("question", "")})
                messages.append(
                    {"role": "assistant", "content": hist.get("answer", "")}
                )

        user_prompt_parts = []

        if personal_context:
            user_prompt_parts.append(f"【个人学习信息】\n{personal_context}")

        if kg_context:
            user_prompt_parts.append(f"【知识图谱信息】\n{kg_context}")

        user_prompt_parts.append(f"【用户问题】\n{question}")

        if personal_context:
            user_prompt_parts.append(
                "\n请结合上面的个人学习信息，针对用户的问题给出回答。"
            )

        messages.append({"role": "user", "content": "\n\n".join(user_prompt_parts)})

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )

        return response.choices[0].message.content.strip()


kg_qa = KGQA()
