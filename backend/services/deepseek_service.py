import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from ..core.config import get_settings

settings = get_settings()

TRIPLE_EXTRACTION_PROMPT = """你是一个知识图谱抽取专家。请从以下文本中提取实体和关系，形成三元组。

【重要】计算思维包含以下五个维度：
1. 分解 Decomposition - 将复杂问题拆分为可管理的小问题
2. 模式识别 Pattern Recognition - 发现数据、问题或现象中的规律
3. 抽象 Abstraction - 关注关键信息，忽略无关细节
4. 算法思维 Algorithmic Thinking - 设计一步步解决问题的步骤/流程
5. 评估 Evaluation - 分析评估解决方案的效率和可行性

要求：
1. 实体类型可以是：概念、定义、定理、算法、协议、应用、安全威胁、解决方法、计算思维 等
2. 关系类型包括：体现、包含、属于、是、用于、实现、基于、对比、区别、关联 等
3. 【关键】每个知识点必须提取其体现的计算思维，用"体现"关系连接到计算思维维度
4. 返回JSON数组格式的三元组

输出格式：
[
  {{"head": "实体1", "head_type": "实体类型", "relation": "关系", "tail": "实体2", "tail_type": "实体类型", "source": "来源"}}
]

示例：
- 离散数学的"递归"概念 --[体现]--> 计算思维的"分解"
- RSA加密算法 --[体现]--> 计算思维的"算法思维"

文本内容：
{content}
"""


class DeepSeekClient:
    _instance: Optional["DeepSeekClient"] = None
    _client: Optional[OpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_triples(self, content: str, source: str = "") -> List[Dict]:
        client = self.connect()
        prompt = TRIPLE_EXTRACTION_PROMPT.format(content=content)

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的知识图谱构建助手，擅长从文本中提取结构化的知识三元组。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        result = response.choices[0].message.content.strip()
        result = self._parse_json(result)
        for item in result:
            item["source"] = source
        return result

    def answer_question(self, context: str, question: str, kg_context: str = "") -> str:
        client = self.connect()

        system_prompt = """你是一个专业的知识图谱问答助手。如果知识图谱中有相关信息，优先基于知识图谱内容回答。
        如果知识图谱中没有相关信息，请基于你的知识库回答，但请说明这是基于通用知识而非课程内容。"""

        user_prompt = f"知识图谱相关信息：\n{kg_context}\n\n用户问题：{question}"

        if context:
            user_prompt = f"文档上下文：\n{context}\n\n{user_prompt}"

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        return response.choices[0].message.content.strip()

    def _parse_json(self, text: str) -> List[Dict]:
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []


deepseek_client = DeepSeekClient()
