"""
build_index.py - Tilikum AI ChromaDB Vektör İndeksleyici
--------------------------------------------------------
chunks.json dosyasından BAAI/bge-m3 modeliyle embedding üretip
'ocean_chroma_db' klasörünü otomatik oluşturur.
Kullanım:
    python build_index.py           # Tüm chunkları indeksler
    python build_index.py 500       # Hızlı test için ilk 500 chunkı indeksler
"""

import json
import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = "chunks.json"
DB_DIR = "./ocean_chroma_db"
COLLECTION_NAME = "ocean_collection"
BATCH_SIZE = 64


def build(limit: int = None):
    if not os.path.exists(CHUNKS_FILE):
        print(f"❌ Hata: '{CHUNKS_FILE}' bulunamadı.")
        sys.exit(1)

    print(f"📂 '{CHUNKS_FILE}' yükleniyor...")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if limit:
        chunks = chunks[:limit]
        print(f"⚡ Hızlı test modu: İlk {limit} chunk seçildi.")

    total = len(chunks)
    print(f"📊 Toplam {total} chunk işlenecek.")

    print("🧠 Embedding modeli (BAAI/bge-m3) yükleniyor...")
    model = SentenceTransformer("BAAI/bge-m3")

    print(f"💾 ChromaDB '{DB_DIR}' üzerinde hazırlanıyor...")
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    print(f"🚀 İndeksleme başlıyor (Batch boyutu: {BATCH_SIZE})...")
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        ids = [f"chunk_{idx}" for idx in range(i, i + len(batch))]
        metadatas = [
            {
                "source": c.get("source", "unknown"),
                "char_count": c.get("char_count", len(c["text"])),
            }
            for c in batch
        ]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=BATCH_SIZE
        ).tolist()

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        progress = min(i + BATCH_SIZE, total)
        print(f"   İlerleme: {progress}/{total} (%{progress*100/total:.1f})", end="\r")

    print(f"\n✅ Başarılı! {total} chunk '{COLLECTION_NAME}' koleksiyonuna kaydedildi.")
    print(f"📁 Veritabanı Yolu: {os.path.abspath(DB_DIR)}")


if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    build(limit=limit_arg)
