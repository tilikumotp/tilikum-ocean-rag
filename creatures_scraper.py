"""
🌊 Tilikum AI: Okyanus & Deniz Canlıları Kapsamlı Makale Toplayıcı (Marine Creatures Scraper)
-----------------------------------------------------------------------------------------
Bu betik; okyanus memelileri, derin deniz canlıları, köpekbalıkları, kafadanbacaklılar,
mercanlar, planktonlar, deniz sürüngenleri ve pelajik balıklar hakkında bilimsel makaleleri
Wikipedia ve REST kaynaklarından otonom olarak çekip './data_creatures' klasörüne kaydeder.
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = "./data_creatures"
os.makedirs(DATA_DIR, exist_ok=True)

LANG = "en"
API_URL = f"https://{LANG}.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "TilikumMarineResearchBot/2.0 (okyanus_rag_project; contact: research@ocean.local)"}

# 1. HEDEF KATEGORİLER (Wikipedia Kategori Ağacı)
TARGET_CATEGORIES = [
    ("Cetaceans", 40),                     # Balinalar, Yunuslar, Orka
    ("Sharks", 40),                        # Köpekbalıkları, Megalodon
    ("Deep_sea_fish", 40),                 # Fener balığı, Işıklı balıklar, Abisal türler
    ("Cephalopods", 35),                   # Dev mürekkep balığı, Ahtapotlar, Nautilus
    ("Jellyfish", 30),                     # Deniz anaları, Kutu deniz anası, Sifonoforlar
    ("Corals", 30),                        # Resif mercanları, Derin deniz mercanları
    ("Marine_crustaceans", 30),            # Krill, Mantis karidesi, Örümcek yengeç
    ("Marine_reptiles", 25),               # Deniz kaplumbağaları, Deniz iguanası
    ("Plankton", 25),                      # Fitoplankton, Zooplankton, Diatomlar
    ("Ray-finned_fish_of_the_ocean", 35)   # Orkinos, Ay balığı (Mola mola), Kürek balığı
]

# 2. ÖZEL OLARAK EKSİK OLMAMASI GEREKEN ANAHTAR TÜRLER & EKOSİSTEMLER
CORE_SPECIES = [
    "Blue whale", "Killer whale", "Humpback whale", "Sperm whale", "Narwhal", "Beluga whale",
    "Bowhead whale", "Fin whale", "Right whale", "Gray whale", "Dolphin", "Bottlenose dolphin",
    "Great white shark", "Whale shark", "Basking shark", "Hammerhead shark", "Tiger shark",
    "Greenland shark", "Megalodon", "Bull shark", "Manta ray", "Stingray",
    "Anglerfish", "Gigantactis", "Barreleye", "Pelican eel", "Viperfish", "Blobfish",
    "Snailfish", "Coelacanth", "Fangtooth", "Black swallower", "Hatchetfish", "Lanternfish",
    "Giant squid", "Colossal squid", "Vampire squid", "Blue-ringed octopus", "Common octopus",
    "Mimic octopus", "Nautilus", "Cuttlefish", "Giant Pacific octopus",
    "Box jellyfish", "Lion's mane jellyfish", "Portuguese man o' war", "Siphonophore",
    "Praya dubia", "Immortal jellyfish", "Comb jelly",
    "Coral reef", "Great Barrier Reef", "Deep-water coral", "Sea anemone",
    "Antarctic krill", "Copepod", "Peacock mantis shrimp", "Japanese spider crab",
    "Horseshoe crab", "Giant isopod", "Barnacle",
    "Leatherback sea turtle", "Green sea turtle", "Loggerhead sea turtle", "Marine iguana",
    "Sea snake", "Hydrophiinae",
    "Ocean sunfish", "Giant oarfish", "Atlantic bluefin tuna", "Sailfish", "Swordfish",
    "Moray eel", "Clownfish", "Parrotfish", "Barracuda", "Lionfish", "Mahi-mahi",
    "Phytoplankton", "Diatom", "Dinoflagellate", "Bioluminescence in marine organisms",
    "Hydrothermal vent microbial community", "Whale fall", "Abyssal zone fauna",
    "Hadal zone fauna", "Pelagic zone", "Benthic zone", "Mesopelagic zone"
]

def slugify(text: str, max_len: int = 50) -> str:
    """Dosya adı için metni güvenli hale getirir."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_len] if text else "untitled"

def get_category_members(category: str, limit: int = 35):
    """Kategorideki makale başlıklarını çeker."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": limit,
        "cmtype": "page",
        "format": "json",
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            members = data.get("query", {}).get("categorymembers", [])
            return [m["title"] for m in members if not m["title"].startswith("List of")]
    except Exception as e:
        print(f"⚠️ Kategori çekme hatası ({category}): {e}")
    return []

def get_article_plaintext(title: str):
    """Makalenin tam metnini ve bölümlerini çeker."""
    params = {
        "action": "query",
        "prop": "extracts|categories",
        "explaintext": 1,
        "titles": title,
        "cllimit": 10,
        "format": "json",
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for p_id, p_data in pages.items():
                if p_id != "-1":
                    extract = p_data.get("extract", "")
                    cats = [c.get("title", "").replace("Category:", "") for c in p_data.get("categories", [])]
                    return extract, cats
    except Exception as e:
        print(f"⚠️ Makale çekme hatası ({title}): {e}")
    return "", []

def process_and_save_article(title: str, index: int, category_hint: str = "Marine Biology"):
    """Makaleyi çeker, temizler ve data_creatures içine kaydeder."""
    filename = f"creature_{index:03d}_{slugify(title)}.md"
    file_path = os.path.join(DATA_DIR, filename)
    
    # Zaten varsa kontrol et
    if os.path.exists(file_path):
        return True, title, "Zaten Mevcut"

    text, cats = get_article_plaintext(title)
    if not text or len(text) < 300:
        return False, title, "İçerik çok kısa / boş"

    # Yapılandırılmış Markdown Belgesi Oluştur
    cat_str = ", ".join(cats[:5]) if cats else category_hint
    md_content = f"""---
title: "{title}"
category: "{category_hint}"
tags: [{cat_str}]
source: "Wikipedia Scientific Archive"
language: "en"
---

# 🐋 Marine Creature Dossier: {title}

**Target Category:** {category_hint}  
**Scientific / Ecological Tags:** {cat_str}  

---

## 📖 Overview & Biological Description

{text}

---
*Tilikum AI Marine Biology & Deep-Sea Database — Auto-Ingested Document*
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return True, title, f"{len(text)} karakter"

def main():
    print("=" * 70)
    print("🌊 TILIKUM AI: OKYANUS VE DENİZ CANLILARI MAKALE TOPLAYICI BAŞLATILIYOR")
    print(f"📂 Hedef Dizin: {DATA_DIR}")
    print("=" * 70)

    # 1. Başlık Havuzunu Oluştur
    all_titles = set(CORE_SPECIES)
    print(f"\n[1/3] Çekirdek tür listesi yüklendi ({len(CORE_SPECIES)} anahtar tür).")
    
    print("\n[2/3] Wikipedia Kategori Ağacı taranıyor...")
    for cat_name, limit in TARGET_CATEGORIES:
        members = get_category_members(cat_name, limit)
        print(f" -> {cat_name}: {len(members)} makale başlığı bulundu.")
        all_titles.update(members)
        time.sleep(0.3)

    sorted_titles = sorted(list(all_titles))
    print(f"\n[+] Toplam taranacak benzersiz deniz canlısı makalesi: {len(sorted_titles)}")

    # 2. Çok İş Parçacıklı (Multi-threaded) İndirme
    print(f"\n[3/3] Makaleler indiriliyor ve '{DATA_DIR}' dizinine kaydediliyor...\n")
    downloaded_count = 0
    skipped_count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(process_and_save_article, title, idx + 1): title 
            for idx, title in enumerate(sorted_titles)
        }
        
        for future in as_completed(futures):
            title = futures[future]
            try:
                success, t_name, status_msg = future.result()
                if success:
                    downloaded_count += 1
                    print(f" ✅ [{downloaded_count:03d}] {t_name:<35} | {status_msg}")
                else:
                    skipped_count += 1
                    print(f" ⚠️ Atlandı: {t_name:<35} | {status_msg}")
            except Exception as exc:
                print(f" ❌ Hata ({title}): {exc}")

    print("\n" + "=" * 70)
    print(f"🎉 İŞLEM TAMAMLANDI!")
    print(f"📊 Toplam Başarıyla Kaydedilen Makale: {downloaded_count}")
    print(f"📁 Dizin: {os.path.abspath(DATA_DIR)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
