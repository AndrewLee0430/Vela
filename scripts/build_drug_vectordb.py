"""
Build Drug Vector Database (NumPy JSON index)
將收集的藥物資料向量化並存為 JSON，供 VectorStore 載入

使用方法:
    python scripts/build_drug_vectordb.py
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# 載入環境變數
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

if not os.getenv('OPENAI_API_KEY'):
    print(f"❌ Error: OPENAI_API_KEY not found")
    print(f"   Checked: {env_path}")
    sys.exit(1)
else:
    print(f"✅ API Key loaded from {env_path}")

from openai import OpenAI

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"


def load_drug_data(data_dir: Path) -> List[Dict]:
    """載入所有藥物 JSON 檔案"""
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return []

    json_files = list(data_dir.glob("*.json"))
    print(f"📂 Found {len(json_files)} drug data files")

    drug_data = []
    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                drug_data.append(json.load(f))
        except Exception as e:
            print(f"❌ Error loading {filepath}: {e}")

    print(f"✅ Loaded {len(drug_data)} drug data files")
    return drug_data


def create_documents(drug_data: List[Dict]) -> List[Dict]:
    """將藥物資料轉為 document metadata dicts"""
    documents = []

    for data in drug_data:
        drug_name = data.get('drug_name', 'Unknown')

        # 1. 基本資訊
        basic_info = f"""Drug: {drug_name}
Generic Name: {data.get('generic_name', '')}
Brand Names: {', '.join(data.get('brand_names', []))}

Indications and Usage:
{data.get('indications', '')}

Dosage and Administration:
{data.get('dosage', '')}""".strip()

        documents.append({
            "content": basic_info,
            "source_type": "fda_label",
            "source_id": f"fda-{drug_name.lower().replace(' ', '-')}-basic",
            "title": f"{drug_name} - Basic Info",
            "url": "",
            "credibility": "official",
            "drug_name": drug_name,
            "doc_type": "basic_info",
        })

        # 2. 禁忌症和警告
        if data.get('contraindications') or data.get('warnings'):
            safety_info = f"""Drug: {drug_name}

Contraindications:
{data.get('contraindications', '')}

Warnings and Precautions:
{data.get('warnings', '')}""".strip()

            documents.append({
                "content": safety_info,
                "source_type": "fda_label",
                "source_id": f"fda-{drug_name.lower().replace(' ', '-')}-safety",
                "title": f"{drug_name} - Safety",
                "url": "",
                "credibility": "official",
                "drug_name": drug_name,
                "doc_type": "safety",
            })

        # 3. 不良反應
        if data.get('adverse_reactions'):
            adverse_info = f"""Drug: {drug_name}

Adverse Reactions:
{data.get('adverse_reactions', '')}""".strip()

            documents.append({
                "content": adverse_info,
                "source_type": "fda_label",
                "source_id": f"fda-{drug_name.lower().replace(' ', '-')}-adverse",
                "title": f"{drug_name} - Adverse Reactions",
                "url": "",
                "credibility": "official",
                "drug_name": drug_name,
                "doc_type": "adverse_reactions",
            })

        # 4. 藥物交互作用
        if data.get('drug_interactions'):
            interaction_info = f"""Drug: {drug_name}

Drug Interactions:
{data.get('drug_interactions', '')}""".strip()

            documents.append({
                "content": interaction_info,
                "source_type": "fda_label",
                "source_id": f"fda-{drug_name.lower().replace(' ', '-')}-interactions",
                "title": f"{drug_name} - Interactions",
                "url": "",
                "credibility": "official",
                "drug_name": drug_name,
                "doc_type": "interactions",
            })

        # 5. 藥理學
        if data.get('pharmacology'):
            pharm_info = f"""Drug: {drug_name}

Clinical Pharmacology:
{data.get('pharmacology', '')}""".strip()

            documents.append({
                "content": pharm_info,
                "source_type": "fda_label",
                "source_id": f"fda-{drug_name.lower().replace(' ', '-')}-pharm",
                "title": f"{drug_name} - Pharmacology",
                "url": "",
                "credibility": "official",
                "drug_name": drug_name,
                "doc_type": "pharmacology",
            })

    print(f"✅ Created {len(documents)} documents from {len(drug_data)} drugs")
    return documents


def embed_documents(documents: List[Dict], batch_size: int = 100) -> List[List[float]]:
    """批次產生 embeddings"""
    all_embeddings = []
    texts = [doc["content"] for doc in documents]

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"   Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1} ({len(batch)} docs)...")
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Build drug vector database (NumPy JSON)')
    parser.add_argument('--data-dir', type=str, default='data/drug_database',
                        help='Drug data directory')
    parser.add_argument('--output-dir', type=str, default='data/drug_vectordb',
                        help='Output directory for index.json')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 Building Drug Vector Database (NumPy JSON)")
    print("=" * 60)

    # 1. 載入資料
    drug_data = load_drug_data(data_dir)
    if not drug_data:
        print("❌ No drug data found. Run collect_drug_data.py first!")
        return

    # 2. 建立 documents
    documents = create_documents(drug_data)

    # 3. 產生 embeddings
    print(f"🔨 Embedding {len(documents)} documents with {EMBEDDING_MODEL}...")
    embeddings = embed_documents(documents)

    # 4. 寫入 index.json
    index_path = output_dir / "index.json"
    index_data = {
        "model": EMBEDDING_MODEL,
        "documents": documents,
        "embeddings": embeddings,
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False)

    size_mb = index_path.stat().st_size / (1024 * 1024)
    print(f"💾 Saved: {index_path} ({size_mb:.1f} MB)")

    # 5. 驗證
    import numpy as np
    emb_array = np.array(embeddings, dtype=np.float32)
    print(f"\n✅ Build completed!")
    print(f"   Documents: {len(documents)}")
    print(f"   Embedding dim: {emb_array.shape[1]}")
    print(f"   Index: {index_path}")


if __name__ == "__main__":
    main()
