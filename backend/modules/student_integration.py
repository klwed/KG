import csv
from pathlib import Path
from typing import List, Dict
from .student_processor import student_processor, DISCRETE_MATH_TOPICS
from .relation_extractor import relation_extractor
from .kg_importer import kg_importer

DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "documents"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def process_student_data(csv_path: str = None) -> Dict:
    if csv_path is None:
        csv_path = DATA_DIR / "students.csv"

    students = student_processor.load_from_csv(str(csv_path))
    triples = student_processor.generate_triples(students)
    summaries = student_processor.get_student_summary(students)
    topic_stats = student_processor.get_topic_statistics(students)

    return {
        "students": students,
        "triples": triples,
        "summaries": summaries,
        "topic_stats": topic_stats,
    }


def import_student_to_kg(csv_path: str = None) -> Dict:
    result = process_student_data(csv_path)

    kg_importer.import_triples(result["triples"])

    return {
        "imported_triples": len(result["triples"]),
        "student_count": len(result["students"]),
        "summaries": result["summaries"],
    }


def generate_report() -> str:
    csv_path = DATA_DIR / "students.csv"
    if not csv_path.exists():
        return "学生数据文件不存在"

    result = process_student_data(str(csv_path))

    report = ["# 学生离散数学掌握情况报告\n"]

    report.append("## 各知识点统计\n")
    report.append("| 知识点 | 平均分 | 最高分 | 最低分 | 关联计算思维 |")
    report.append("|--------|--------|--------|--------|-------------|")

    for topic, stats in result["topic_stats"].items():
        ct = ", ".join(stats["计算思维"])
        report.append(
            f"| {topic} | {stats['平均分']} | {stats['最高分']} | {stats['最低分']} | {ct} |"
        )

    report.append("\n## 学生掌握情况\n")
    report.append("| 姓名 | 平均分 | 总评 | 薄弱点 | 强项 |")
    report.append("|------|--------|------|--------|------|")

    for s in result["summaries"]:
        weak = ", ".join(s["薄弱点"]) if s["薄弱点"] else "无"
        strong = ", ".join(s["强项"]) if s["强项"] else "无"
        report.append(
            f"| {s['姓名']} | {s['平均分']} | {s['总评']} | {weak} | {strong} |"
        )

    report.append("\n## 图谱结构说明\n")
    report.append("""```
                    计算思维
                   /   |   \\
                  /    |    \\
             分解   算法思维   抽象
                   \\    |    /
                    \\   |   /
                 ┌──────────────────┐
                 │    离散数学       │
                 │ 集合、函数、图论  │
                 │ 递归、逻辑...    │
                 └──────────────────┘
                       │ 属于
                       ↓
                 ┌──────────────────┐
                 │   知识点A        │
                 │   知识点B        │
                 └──────────────────┘
                       │ 掌握
                       ↓
                 ┌──────────────────┐
                 │    学生张三       │
                 │  掌握程度:优秀   │
                 └──────────────────┘
```""")

    return "\n".join(report)


def export_student_triples():
    csv_path = DATA_DIR / "students.csv"
    if not csv_path.exists():
        return None

    result = process_student_data(str(csv_path))

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / "student_triples.json"

    import json

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result["triples"], f, ensure_ascii=False, indent=2)

    return str(output_file)


if __name__ == "__main__":
    result = process_student_data()
    print(f"处理了 {len(result['students'])} 名学生")
    print(f"生成了 {len(result['triples'])} 个三元组")
    print("\n学生汇总:")
    for s in result["summaries"]:
        print(f"  {s['姓名']}: {s['总评']} (平均分 {s['平均分']})")
