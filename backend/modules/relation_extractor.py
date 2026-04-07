import json
import re
from typing import List, Dict
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from ..core.config import get_settings

settings = get_settings()

EXTRACTION_PROMPT = """你是一个知识图谱抽取专家。请从以下文本中提取实体和关系，形成三元组。

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

示例：
- 离散数学 --[包含]--> 集合论
- 集合论 --[包含]--> 等价关系
- 等价关系 --[描述]--> 定义
- 等价关系 --[描述]--> 自反性
- 等价关系 --[体现]--> 抽象
- 等价关系 --[体现]--> 算法思维
- 信息安全 --[包含]--> 密码学
- 密码学 --[包含]--> RSA算法
- RSA算法 --[描述]--> 非对称加密
- RSA算法 --[体现]--> 算法思维

文本内容：
{content}
"""

TABLE_PROMPT = """请将以下三元组数据整理成表格格式：

三元组数据：
{triples}

输出格式（Markdown表格）：
| 序号 | 头实体 | 关系 | 尾实体 | 头实体类型 | 尾实体类型 | 来源 |
|------|--------|------|--------|-----------|-----------|------|
| 1 | ... | ... | ... | ... | ... | ... |
"""


class RelationExtractor:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _connect(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_triples(self, text: str, source: str = "") -> List[Dict]:
        client = self._connect()
        prompt = EXTRACTION_PROMPT.format(content=text)

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
        return self._parse_json(result, source)

    def _parse_json(self, text: str, source: str) -> List[Dict]:
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                for item in data:
                    item["source"] = source
                return data
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(text)
            for item in data:
                item["source"] = source
            return data
        except json.JSONDecodeError:
            return []

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

        client = self._connect()
        triples_str = json.dumps(triples, ensure_ascii=False, indent=2)
        prompt = TABLE_PROMPT.format(triples=triples_str)

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个数据整理助手，擅长将数据格式化为表格。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )

        return response.choices[0].message.content.strip()

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
