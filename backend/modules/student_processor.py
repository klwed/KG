import csv
from typing import List, Dict, Tuple

DISCRETE_MATH_TOPICS = [
    "集合",
    "函数",
    "关系",
    "图论",
    "命题逻辑",
    "谓词逻辑",
    "递归",
    "排列组合",
]

SCORE_TO_LEVEL = {
    (0.9, 1.0): "优秀",
    (0.7, 0.9): "良好",
    (0.5, 0.7): "一般",
    (0.3, 0.5): "较差",
    (0.0, 0.3): "很差",
}

TOPIC_CT_MAPPING = {
    "集合": ["抽象", "分解"],
    "函数": ["抽象", "模式识别"],
    "关系": ["抽象", "模式识别"],
    "图论": ["分解", "模式识别", "算法思维"],
    "命题逻辑": ["抽象", "算法思维"],
    "谓词逻辑": ["抽象", "算法思维"],
    "递归": ["分解", "算法思维"],
    "排列组合": ["模式识别", "算法思维"],
}


def score_to_level(score: float) -> str:
    for (min_score, max_score), level in SCORE_TO_LEVEL.items():
        if min_score <= score <= max_score:
            return level
    return "未知"


class StudentProcessor:
    @staticmethod
    def load_from_csv(file_path: str) -> List[Dict]:
        students = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                students.append(row)
        return students

    @staticmethod
    def generate_triples(students: List[Dict]) -> List[Dict]:
        triples = []

        for student in students:
            name = student["姓名"]

            for topic in DISCRETE_MATH_TOPICS:
                if topic in student:
                    score = float(student[topic])
                    level = score_to_level(score)

                    triples.append(
                        {
                            "head": name,
                            "head_type": "学生",
                            "relation": "掌握",
                            "tail": topic,
                            "tail_type": "知识点",
                            "source": "学生数据",
                        }
                    )

                    triples.append(
                        {
                            "head": name,
                            "head_type": "学生",
                            "relation": "掌握程度",
                            "tail": f"{topic}：{level}",
                            "tail_type": "掌握情况",
                            "source": "学生数据",
                        }
                    )

                    triples.append(
                        {
                            "head": topic,
                            "head_type": "知识点",
                            "relation": "属于",
                            "tail": "离散数学",
                            "tail_type": "课程",
                            "source": "学生数据",
                        }
                    )

                    if topic in TOPIC_CT_MAPPING:
                        for ct in TOPIC_CT_MAPPING[topic]:
                            triples.append(
                                {
                                    "head": topic,
                                    "head_type": "知识点",
                                    "relation": "体现",
                                    "tail": ct,
                                    "tail_type": "计算思维",
                                    "source": "知识关联",
                                }
                            )

        return triples

    @staticmethod
    def get_student_summary(students: List[Dict]) -> List[Dict]:
        summaries = []
        for student in students:
            name = student["姓名"]
            scores = {
                topic: float(student[topic])
                for topic in DISCRETE_MATH_TOPICS
                if topic in student
            }
            avg_score = sum(scores.values()) / len(scores) if scores else 0

            weak_topics = [t for t, s in scores.items() if s < 0.6]
            strong_topics = [t for t, s in scores.items() if s >= 0.8]

            summaries.append(
                {
                    "姓名": name,
                    "平均分": round(avg_score, 2),
                    "总评": score_to_level(avg_score),
                    "薄弱点": weak_topics,
                    "强项": strong_topics,
                }
            )

        return summaries

    @staticmethod
    def get_topic_statistics(students: List[Dict]) -> Dict:
        stats = {}
        for topic in DISCRETE_MATH_TOPICS:
            scores = [float(s[topic]) for s in students if topic in s]
            if scores:
                stats[topic] = {
                    "平均分": round(sum(scores) / len(scores), 2),
                    "最高分": max(scores),
                    "最低分": min(scores),
                    "计算思维": TOPIC_CT_MAPPING.get(topic, []),
                }
        return stats

    @staticmethod
    def get_student_by_name(students: List[Dict], name: str) -> Dict:
        for student in students:
            if student.get("姓名") == name or student.get("username") == name:
                scores = {
                    topic: float(student[topic])
                    for topic in DISCRETE_MATH_TOPICS
                    if topic in student
                }
                avg_score = sum(scores.values()) / len(scores) if scores else 0

                details = []
                for topic, score in scores.items():
                    details.append(
                        {
                            "topic": topic,
                            "score": score,
                            "level": score_to_level(score),
                            "ct": ", ".join(TOPIC_CT_MAPPING.get(topic, [])),
                        }
                    )

                return {
                    "name": name,
                    "avgScore": round(avg_score, 2),
                    "level": score_to_level(avg_score),
                    "strong": [t for t, s in scores.items() if s >= 0.8],
                    "weak": [t for t, s in scores.items() if s < 0.6],
                    "details": details,
                }
        return None


student_processor = StudentProcessor()
