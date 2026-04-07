from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import PydanticOutputParser
from langchain.pydantic_v1 import BaseModel
from ..core.config import get_settings

settings = get_settings()


class TripleOutput(BaseModel):
    head: str
    head_type: str
    relation: str
    tail: str
    tail_type: str
    source: str


class LLMService:
    _instance = None
    _llm = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.1,
                max_tokens=4096,
            )
        return self._llm

    def extract_triples(self, text: str, source: str = "") -> List[Dict]:
        """从文本中提取知识三元组"""
        prompt = """你是一个知识图谱抽取专家。请从以下文本中提取实体和关系，形成三元组。

【重要】计算思维包含以下五个维度：
1. 分解 Decomposition - 将复杂问题拆分为可管理的小问题
2. 模式识别 Pattern Recognition - 发现数据、问题或现象中的规律
3. 抽象 Abstraction - 关注关键信息，忽略无关细节
4. 算法思维 Algorithmic Thinking - 设计一步步解决问题的步骤/流程
5. 评估 Evaluation - 分析评估解决方案的效率和可行性

【图谱层级结构】
第一层：课程（如：离散数学、信息安全）
第二层：章节（如：集合与关系、密码学基础）
第三层：知识点（如：等价关系、RSA算法）
第四层：知识标签/描述（如：定义、对称性、自反性等）

实体类型：课程、章节、知识点、知识标签、计算思维
关系类型：包含、体现、描述、关联

【关键要求】
1. 抽取完整的层级结构：课程 → 章节 → 知识点
2. 每个知识点必须提取其体现的计算思维
3. 每个知识点需要提取描述性标签（1-3个关键词）
4. 返回JSON数组格式

输出格式：
[
  {"head": "实体1", "head_type": "实体类型", "relation": "关系", "tail": "实体2", "tail_type": "实体类型", "source": "来源"}
]

三元组类型说明：
1. 课程层级：课程 --[包含]--> 章节，章节 --[包含]--> 知识点
2. 计算思维：知识点 --[体现]--> 计算思维维度
3. 知识标签：知识点 --[描述]--> 标签词

文本内容：
{content}
"""

        llm = self._get_llm()
        response = llm.invoke(prompt.format(content=text))
        content = response.content

        import json
        import re

        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                for item in data:
                    item["source"] = source
                return data
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(content)
            for item in data:
                item["source"] = source
            return data
        except json.JSONDecodeError:
            return []

    def extract_batch(self, chunks: List[Dict], source: str = "") -> List[Dict]:
        """批量提取三元组"""
        all_triples = []
        for i, chunk in enumerate(chunks):
            try:
                text = chunk.get("text", chunk) if isinstance(chunk, dict) else chunk
                triples = self.extract_triples(text, source)
                all_triples.extend(triples)
                print(f"  块 {i + 1}/{len(chunks)}: 提取到 {len(triples)} 个三元组")
            except Exception as e:
                print(f"  块 {i + 1} 处理失败: {e}")
                continue
        return all_triples

    def ask_question(
        self,
        question: str,
        kg_context: str = "",
        conversation_history: List[Dict] = None,
        personal_context: str = "",
    ) -> str:
        """回答用户问题"""
        prompt = """你是一个专业的知识图谱问答助手。如果知识图谱中有相关信息，优先基于知识图谱内容回答。
如果知识图谱中没有相关信息，请基于你的知识库回答。
回答要简洁、专业、清晰。如果用户追问，请结合之前的对话上下文回答。
如果用户提供个人信息（如个人掌握情况），请结合这些信息给出针对性的回答。

{context}

【用户问题】
{question}
"""

        context_parts = []
        if personal_context:
            context_parts.append(f"【个人学习信息】\n{personal_context}")
        if kg_context:
            context_parts.append(f"【知识图谱信息】\n{kg_context}")

        full_context = "\n\n".join(context_parts)

        if conversation_history:
            history_prompt = "\n\n【对话历史】\n"
            for hist in conversation_history[-5:]:
                history_prompt += f"用户: {hist.get('question', '')}\n助手: {hist.get('answer', '')}\n"
            full_context += history_prompt

        llm = self._get_llm()
        response = llm.invoke(prompt.format(context=full_context, question=question))
        return response.content.strip()

    def triples_to_table(self, triples: List[Dict]) -> str:
        """将三元组转换为表格格式"""
        prompt = """请将以下三元组数据整理成表格格式：

三元组数据：
{triples}

输出格式（Markdown表格）：
| 序号 | 头实体 | 关系 | 尾实体 | 头实体类型 | 尾实体类型 | 来源 |
|------|--------|------|--------|-----------|-----------|------|
| 1 | ... | ... | ... | ... | ... | ... |
"""

        llm = self._get_llm()
        triples_str = json.dumps(triples, ensure_ascii=False, indent=2)
        response = llm.invoke(prompt.format(triples=triples_str))
        return response.content.strip()


import json

llm_service = LLMService()
