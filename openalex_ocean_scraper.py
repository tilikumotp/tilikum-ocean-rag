import os
import re
import time
import requests

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- Ayarlar ---
SEARCH_QUERY = "ocean OR marine biology OR oceanography"
TARGET_DOC_COUNT = 100          # Toplam hedeflenen belge sayısı
PER_PAGE = 25                   # Sayfa başına sonuç (max 200)
MAILTO = "serdarbush@email.com"      # OpenAlex "polite pool" için - rate limit'i yükseltir, kendi mailini yaz

search_url = "https://api.openalex.org/works"


def slugify(text: str, max_len: int = 50) -> str:
    """Dosya adı için başlığı temizler."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_len] if text else "untitled"


def fetch_works(cursor="*"):
    """OpenAlex'ten sayfa sayfa sonuç çeker (cursor tabanlı sayfalama)."""
    params = {
        "filter": f"default.search:{SEARCH_QUERY},has_fulltext:true,is_oa:true",
        "per-page": PER_PAGE,
        "cursor": cursor,
        "mailto": MAILTO,
    }
    resp = requests.get(search_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", []), data.get("meta", {}).get("next_cursor")


def download_pdf(work, idx):
    """Tek bir work objesinden PDF indirmeyi dener. Başarılıysa True döner."""
    title = work.get("title") or f"document_{idx}"
    best_loc = work.get("best_oa_location") or {}
    pdf_url = best_loc.get("pdf_url")

    if not pdf_url:
        print(f"Atlandı (PDF linki yok): {title[:50]}")
        return False

    try:
        resp = requests.get(pdf_url, timeout=15)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if "pdf" not in content_type:
            print(f"Atlandı (Content-Type PDF değil - {content_type}): {title[:50]}")
            return False

        filename = f"ocean_{idx+1:03d}_{slugify(title)}.pdf"
        file_path = os.path.join(DATA_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(resp.content)

        print(f"İndirildi: {title[:50]} -> {file_path}")
        return True

    except Exception as e:
        print(f"Hata ({title[:30]}): {e}")
        return False


def main():
    downloaded = 0
    idx = 0
    cursor = "*"

    while downloaded < TARGET_DOC_COUNT and cursor:
        results, cursor = fetch_works(cursor)
        if not results:
            break

        for work in results:
            if downloaded >= TARGET_DOC_COUNT:
                break
            if download_pdf(work, idx):
                downloaded += 1
            idx += 1
            time.sleep(1)  # Rate limit koruması

    print(f"\nTamamlandı. Toplam indirilen dosya: {downloaded}")


if __name__ == "__main__":
    main()
