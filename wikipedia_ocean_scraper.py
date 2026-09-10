import os
import re
import time
import requests

DATA_DIR = "./data_wikipedia"
os.makedirs(DATA_DIR, exist_ok=True)

# --- Ayarlar ---
CATEGORIES = [
    "Oceanography",
    "Marine biology",
    "Ocean currents",
    "Marine ecosystems",
    "Physical oceanography",
]
MAX_DEPTH = 1          # Alt kategorilere ne kadar derine inilecek (0 = sadece ana kategori)
MAX_ARTICLES_PER_CAT = 60   # Kategori başına maksimum makale sayısı
LANG = "en"             # "en" (İngilizce kaynak daha geniş), istersen "tr" dene ama içerik çok daha az olur

API_URL = f"https://{LANG}.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "OkyanusRAGProjesi/1.0 (personal research project)"}


def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_len] if text else "untitled"


def get_category_members(category: str, limit: int = 60):
    """Bir kategorideki sayfa (makale) başlıklarını çeker."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": limit,
        "cmtype": "page",
        "format": "json",
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def get_subcategories(category: str, limit: int = 20):
    """Bir kategorinin alt kategorilerini çeker (derinlemesine tarama için)."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": limit,
        "cmtype": "subcat",
        "format": "json",
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # "Category:XYZ" -> "XYZ"
    return [m["title"].replace("Category:", "") for m in data.get("query", {}).get("categorymembers", [])]


def get_article_plaintext(title: str):
    """Bir makalenin tam düz metnini çeker."""
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json",
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        return page.get("extract", "")
    return ""


def collect_titles(categories, max_depth, max_per_cat):
    """Verilen kategoriler (ve isteğe bağlı alt kategoriler) altındaki tüm makale başlıklarını toplar."""
    seen_titles = set()
    to_process = [(cat, 0) for cat in categories]

    while to_process:
        cat, depth = to_process.pop(0)
        print(f"Kategori taranıyor: {cat} (derinlik {depth})")

        try:
            titles = get_category_members(cat, max_per_cat)
            seen_titles.update(titles)

            if depth < max_depth:
                subcats = get_subcategories(cat)
                for sub in subcats:
                    to_process.append((sub, depth + 1))
        except Exception as e:
            print(f"Hata (kategori: {cat}): {e}")

        time.sleep(0.5)

    return sorted(seen_titles)


def main():
    titles = collect_titles(CATEGORIES, MAX_DEPTH, MAX_ARTICLES_PER_CAT)
    print(f"\nToplam benzersiz makale bulundu: {len(titles)}\n")

    downloaded = 0
    for idx, title in enumerate(titles):
        try:
            text = get_article_plaintext(title)
            if not text or len(text) < 200:  # Çok kısa/boş sayfaları atla (disambiguation vb.)
                print(f"Atlandı (içerik yetersiz): {title}")
                continue

            filename = f"wiki_{idx+1:03d}_{slugify(title)}.txt"
            file_path = os.path.join(DATA_DIR, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{text}")

            print(f"Kaydedildi: {title} -> {file_path}")
            downloaded += 1
            time.sleep(0.5)  # Wikipedia API'ye nazik davran

        except Exception as e:
            print(f"Hata ({title}): {e}")

    print(f"\nTamamlandı. Toplam kaydedilen makale: {downloaded}")


if __name__ == "__main__":
    main()