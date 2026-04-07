"""
知识图谱问答系统 - 模块化运行脚本

使用方法：
1. 确保已安装依赖: pip install -r requirements.txt
2. 配置 .env 文件
3. 运行此脚本

python run_pipeline.py --step 1  # 只运行分词清洗
python run_pipeline.py --step 2  # 只运行关系抽取
python run_pipeline.py --step 3  # 只运行导入图谱
python run_pipeline.py --step 4  # 运行完整流程
"""

import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import document_processor, relation_extractor, kg_importer, kg_qa

DOCUMENTS_DIR = Path(__file__).parent.parent / "documents"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def step1_split_and_clean(file_name: str = None):
    """第一步：分词与清洗"""
    print("\n" + "=" * 60)
    print("步骤1: 分词与清洗")
    print("=" * 60)

    if file_name:
        files = [DOCUMENTS_DIR / file_name]
    else:
        files = (
            list(DOCUMENTS_DIR.glob("*.docx"))
            + list(DOCUMENTS_DIR.glob("*.pdf"))
            + list(DOCUMENTS_DIR.glob("*.txt"))
        )

    results = []
    for file_path in files:
        if not file_path.exists():
            print(f"  文件不存在: {file_path}")
            continue

        print(f"\n处理文件: {file_path.name}")
        result = document_processor.process_document(str(file_path))

        output_file = OUTPUT_DIR / f"{file_path.stem}_chunks.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"  原始长度: {result['raw_length']} 字符")
        print(f"  清洗后长度: {result['cleaned_length']} 字符")
        print(f"  分块数量: {result['chunk_count']}")
        print(f"  输出: {output_file}")

        results.append(result)

    return results


def step2_extract_triples(file_name: str = None):
    """第二步：关系抽取"""
    print("\n" + "=" * 60)
    print("步骤2: 关系抽取")
    print("=" * 60)

    if file_name:
        chunk_files = [OUTPUT_DIR / f"{Path(file_name).stem}_chunks.json"]
    else:
        chunk_files = list(OUTPUT_DIR.glob("*_chunks.json"))

    all_triples = []
    for chunk_file in chunk_files:
        if not chunk_file.exists():
            print(f"  请先运行步骤1处理: {chunk_file.name}")
            continue

        with open(chunk_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n处理: {chunk_file.name}")
        triples = relation_extractor.extract_batch(
            data["chunks"], source=data["filename"]
        )
        all_triples.extend(triples)

        print(f"  提取三元组数量: {len(triples)}")

    if all_triples:
        output_file = OUTPUT_DIR / "triples.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_triples, f, ensure_ascii=False, indent=2)

        stats = relation_extractor.get_statistics(all_triples)
        print(f"\n统计信息:")
        print(f"  总三元组数: {stats['total_triples']}")
        print(f"  实体类型分布: {stats['entity_types']}")
        print(f"  关系类型分布: {stats['relation_types']}")
        print(f"  计算思维维度: {stats['ct_dimensions']}")
        print(f"  输出: {output_file}")

        table = relation_extractor.triples_to_table(all_triples[:50])
        table_file = OUTPUT_DIR / "triples_table.md"
        with open(table_file, "w", encoding="utf-8") as f:
            f.write("# 知识三元组表格\n\n")
            f.write(table)
        print(f"  表格输出: {table_file}")

    return all_triples


def step3_import_kg(clear: bool = True):
    """第三步：导入知识图谱"""
    print("\n" + "=" * 60)
    print("步骤3: 导入知识图谱")
    print("=" * 60)

    triples_file = OUTPUT_DIR / "triples.json"
    if not triples_file.exists():
        print("  请先运行步骤2生成三元组")
        return

    with open(triples_file, "r", encoding="utf-8") as f:
        triples = json.load(f)

    if clear:
        print("  清空现有图谱...")
        kg_importer.clear_all()

    print(f"  导入 {len(triples)} 个三元组...")
    result = kg_importer.import_triples(triples)

    print(f"  导入完成: {result['imported']}/{result['total_triples']}")

    stats = kg_importer.get_statistics()
    print(f"\n图谱统计:")
    print(f"  节点数: {stats['node_count']}")
    print(f"  关系数: {stats['relation_count']}")
    print(f"  节点类型: {stats['node_types']}")
    print(f"  关系类型: {stats['relation_types']}")

    return result


def step4_qa_demo():
    """第四步：问答演示"""
    print("\n" + "=" * 60)
    print("步骤4: 知识检索与问答")
    print("=" * 60)

    demo_questions = [
        "什么是RSA算法？",
        "离散数学和计算机安全有什么联系？",
        "递归算法体现了哪些计算思维？",
        "密码学中的对称加密和非对称加密有什么区别？",
    ]

    for question in demo_questions:
        print(f"\n问题: {question}")
        print("-" * 40)

        result = kg_qa.ask(question)

        print(f"答案来源: {result['source']}")
        print(f"答案:\n{result['answer']}")

        if result["related_triples"]:
            print(f"相关三元组 ({len(result['related_triples'])}):")
            for t in result["related_triples"][:3]:
                print(f"  - {t['head']} --[{t['relation']}]--> {t['tail']}")


def run_pipeline():
    """运行完整流程"""
    print("\n" + "=" * 60)
    print("开始知识图谱构建完整流程")
    print("=" * 60)

    step1_split_and_clean()
    triples = step2_extract_triples()
    if triples:
        step3_import_kg(clear=True)
        step4_qa_demo()

    print("\n" + "=" * 60)
    print("流程完成!")
    print("=" * 60)
    print(f"\n输出文件位置: {OUTPUT_DIR}")
    print("  - *_chunks.json: 分块后的文档")
    print("  - triples.json: 提取的三元组")
    print("  - triples_table.md: 三元组表格")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="知识图谱系统运行脚本")
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4],
        help="运行指定步骤 (1:分词 2:抽取 3:导入 4:完整)",
    )
    parser.add_argument("--file", type=str, help="指定处理的文件名")
    parser.add_argument(
        "--clear", action="store_true", default=True, help="导入前清空图谱"
    )

    args = parser.parse_args()

    if args.step == 1:
        step1_split_and_clean(args.file)
    elif args.step == 2:
        step2_extract_triples(args.file)
    elif args.step == 3:
        step3_import_kg(args.clear)
    elif args.step == 4:
        run_pipeline()
    else:
        run_pipeline()
