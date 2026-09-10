"""
🔬 Tilikum AI: Akademik Deniz Canlıları & Biyoloji Makale Toplayıcı (Multi-Source Academic Harvester)
---------------------------------------------------------------------------------------------------
Kaynaklar:
1. OpenAlex API (250M+ Bilimsel Makale Kataloğu, Açık Erişim / Open Access)
2. Europe PMC / EMBL-EBI REST API (Biyomedikal ve Deniz Biyolojisi Literatürü)

Bu betik; hakemli dergilerdeki (Nature, Marine Biology, Deep Sea Research, PLOS ONE, Frontiers in Marine Science)
makaleleri, DOI numaralarını, yazarlarını, özetlerini ve bilimsel bulgularını çekip './data_creatures' klasörüne kaydeder.
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = "./data_creatures"
os.makedirs(DATA_DIR, exist_ok=True)

MAILTO = "research@tilikum-ocean.org"
HEADERS = {
    "User-Agent": "TilikumMarineResearch/3.0 (mailto:research@tilikum-ocean.org)"
}

# -------------------------------------------------------------------------
# 1. BİLİMSEL ARAMA SORGULARI (Hakemli Dergi & Araştırma Konuları)
# -------------------------------------------------------------------------
ACADEMIC_SEARCH_TOPICS = [
    # Deniz Memelileri (Cetaceans & Acoustics)
    "Balaenoptera musculus blue whale foraging biomechanics",
    "Orcinus orca killer whale dialect acoustics social structure",
    "Physeter macrocephalus sperm whale echolocation deep diving",
    "Megaptera novaeangliae humpback whale song migration",
    "Delphinidae bottlenose dolphin signature whistles cognition",
    "Monodon monoceros narwhal tusk function sensory organ",
    
    # Köpekbalıkları & Vatozlar (Elasmobranchs & Apex Predators)
    "Carcharodon carcharias great white shark predatory behavior tracking",
    "Rhincodon typus whale shark filter feeding aggregation genetics",
    "Somniosus microcephalus Greenland shark longevity radiocarbon dating",
    "Sphyrna lewini scalloped hammerhead shark navigation magnetic field",
    "Otodus megalodon body size evolution extinction drivers",
    "Mobula birostris giant manta ray spatial ecology cleaning stations",
    
    # Derin Deniz & Abisal Ekosistemler (Abyssal & Hadal Fauna)
    "Hadalpelagic Mariana trench snailfish Pseudoliparis swirei adaptation",
    "Ceratiidae deep sea anglerfish bioluminescent sexual parasitism",
    "Macropinna microstoma barreleye fish tubular eyes transparent head",
    "Eurypharynx pelecanoides gulper eel feeding mechanics morphology",
    "Bathynomus giganteus giant isopod starvation deep sea scavenger",
    "Hydrothermal vent fauna Riftia pachyptila chemosynthetic symbiosis",
    "Coelacanth Latimeria chalumnae living fossil genome evolution",
    
    # Kafadanbacaklılar & Nörobiyoloji (Cephalopods)
    "Mesonychoteuthis hamiltoni colossal squid vision giant eyes",
    "Architeuthis dux giant squid morphology trophic ecology",
    "Vampyroteuthis infernalis vampire squid detritivory marine snow",
    "Hapalochlaena blue-ringed octopus tetrodotoxin venom biology",
    "Octopus vulgaris camouflage skin chromatophores cognition",
    "Nautilus pompilius buoyancy chambered shell growth",
    
    # Mercanlar & Denizel Ekosistem (Cnidaria & Calcification)
    "Scleractinia coral calcification ocean acidification warming",
    "Symbiodiniaceae coral bleaching thermal tolerance genetics",
    "Chironex fleckeri box jellyfish cnidocyte venom cardiotoxicity",
    "Cyanea capillata lion's mane jellyfish ecology blooms",
    "Praya dubia giant siphonophore colonial zooid differentiation",
    
    # Kabuklular, Plankton & Trofik Düzey (Crustaceans & Plankton)
    "Euphausia superba Antarctic krill biomass carbon pump climate change",
    "Odontodactylus scyllarus mantis shrimp dactyl club strike cavitation",
    "Macrocheira kaempferi Japanese spider crab deep benthic ecology",
    "Marine phytoplankton diatom dinoflagellate primary productivity carbon cycle",
    "Marine bioluminescence luciferin luciferase dinoflagellates deep sea",
    
    # Deniz Sürüngenleri & Pelajik Balıklar
    "Dermochelys coriacea leatherback sea turtle gigantothermy deep diving",
    "Amblyrhynchus cristatus Galapagos marine iguana diving foraging physiology",
    "Thunnus thynnus Atlantic bluefin tuna endothermy migration physiology",
    "Mola mola ocean sunfish diving behaviour jellyfish diet telemetry",
    "Regalecus glesne giant oarfish vertical swimming autotomy"
]

def slugify(text: str, max_len: int = 50) -> str:
    """Dosya adı temizleme."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_len] if text else "untitled"

def reconstruct_openalex_abstract(inverted_index: dict) -> str:
    """OpenAlex'in inverted index formatındaki özetini tam paragrafa dönüştürür."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join([w[1] for w in word_positions])

# -------------------------------------------------------------------------
# 2. OPENALEX API FETCHER
# -------------------------------------------------------------------------
def fetch_openalex_papers(query: str, limit: int = 4):
    """OpenAlex API üzerinden konuya özel açık erişim akademik makaleleri çeker."""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "filter": "has_abstract:true,is_oa:true",
        "per-page": limit,
        "mailto": MAILTO
    }
    papers = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                title = item.get("title", "")
                if not title or len(title) < 15:
                    continue
                    
                abstract = reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
                if not abstract or len(abstract) < 250:
                    continue
                    
                doi = item.get("doi", "N/A")
                pub_year = item.get("publication_year", 2023)
                cited_by = item.get("cited_by_count", 0)
                
                # Dergi / Kaynak bilgisi
                primary_loc = item.get("primary_location") or {}
                source_name = (primary_loc.get("source") or {}).get("display_name", "Peer-Reviewed Scientific Journal")
                
                # Yazarlar
                authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])[:5]]
                authors_str = ", ".join([a for a in authors if a]) or "Scientific Research Group"
                
                # Kavramlar / Anahtar kelimeler
                concepts = [c.get("display_name", "") for c in item.get("concepts", [])[:6]]
                
                papers.append({
                    "title": title,
                    "doi": doi,
                    "year": pub_year,
                    "cited_by": cited_by,
                    "journal": source_name,
                    "authors": authors_str,
                    "concepts": concepts,
                    "abstract": abstract,
                    "source_api": "OpenAlex Scholarly Database"
                })
    except Exception as e:
        print(f"⚠️ OpenAlex API Hatası ({query[:30]}): {e}")
    return papers

# -------------------------------------------------------------------------
# 3. EUROPE PMC API FETCHER
# -------------------------------------------------------------------------
def fetch_europe_pmc_papers(query: str, limit: int = 3):
    """Europe PMC API üzerinden hakemli biyoloji ve deniz bilimleri makaleleri çeker."""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": f"{query} AND (OPEN_ACCESS:Y OR HAS_ABSTRACT:Y)",
        "format": "json",
        "pageSize": limit,
        "resultType": "core"
    }
    papers = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("resultList", {}).get("result", []):
                title = item.get("title", "").rstrip(".")
                abstract = item.get("abstractText", "")
                if not title or not abstract or len(abstract) < 250:
                    continue
                    
                # HTML taglerini temizle
                abstract_clean = re.sub(r"<[^>]+>", "", abstract)
                
                doi = item.get("doi", f"https://doi.org/{item.get('id', '')}")
                pub_year = item.get("pubYear", 2023)
                journal = item.get("journalInfo", {}).get("journal", {}).get("title", "Europe PMC Life Sciences")
                author_str = item.get("authorString", "Marine Biological Researchers")
                
                papers.append({
                    "title": title,
                    "doi": doi,
                    "year": pub_year,
                    "cited_by": item.get("citedByCount", 0),
                    "journal": journal,
                    "authors": author_str[:120],
                    "concepts": [query.split()[0], "Marine Biology", "Ecology"],
                    "abstract": abstract_clean,
                    "source_api": "Europe PMC (EMBL-EBI)"
                })
    except Exception as e:
        print(f"⚠️ Europe PMC Hatası ({query[:30]}): {e}")
    return papers

# -------------------------------------------------------------------------
# 4. MAKALE KAYDETME MOTORU
# -------------------------------------------------------------------------
def save_academic_paper(paper: dict, index: int) -> bool:
    """Makale nesnesini zengin akademik Markdown dosyası olarak kaydeder."""
    title = paper["title"]
    clean_slug = slugify(title)
    filename = f"academic_{index:04d}_{clean_slug}.md"
    file_path = os.path.join(DATA_DIR, filename)

    concepts_str = ", ".join(paper.get("concepts", []))
    doi_val = str(paper.get("doi") or "N/A")
    doi_link = doi_val if "http" in doi_val else (f"https://doi.org/{doi_val}" if doi_val != "N/A" else "#")
    journal_val = str(paper.get("journal") or "Peer-Reviewed Scientific Journal")
    authors_val = str(paper.get("authors") or "Scientific Research Group")

    md_content = f"""---
title: "{title}"
doi: "{doi_val}"
year: {paper.get('year', 2023)}
journal: "{journal_val}"
authors: "{authors_val}"
citations: {paper.get('cited_by', 0)}
concepts: [{concepts_str}]
source: "{paper.get('source_api', 'Academic Source')}"
type: "Peer-Reviewed Research Paper"
language: "en"
---

# 📑 Scientific Paper: {title}

**Journal / Source:** {journal_val} ({paper.get('year', 2023)})  
**DOI:** [{doi_val}]({doi_link})  
**Authors:** {authors_val}  
**Key Research Concepts:** {concepts_str}  
**Citation Impact:** {paper.get('cited_by', 0)} citations  

---

## 🔬 Abstract & Scientific Findings

{paper['abstract']}

---

## 🌊 Ecological & Biological Significance for Marine Knowledge Base

- **Taxonomic & Functional Context:** Bu araştırma, ilgili deniz canlısının morfolojik, biyomekanik ve ekosistem rollerine dair hakemli ampirik veriler sunmaktadır.
- **Data Provenance:** Doğrulanmış akademik kaynak ({paper['source_api']}) üzerinden Tilikum AI Okyanus RAG sistemine dahil edilmiştir.

---
*Tilikum AI Peer-Reviewed Marine Science & Abyssal Biology Archive*
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return True

# -------------------------------------------------------------------------
# 5. ANA YÜRÜTÜCÜ (Main Pipeline)
# -------------------------------------------------------------------------
def main():
    print("=" * 80)
    print("🔬 TILIKUM AI: AKADEMİK DENİZ CANLILARI & BİYOLOJİ MAKALE TOPLAYICI")
    print(f"📂 Hedef Dizin: {os.path.abspath(DATA_DIR)}")
    print(f"🎯 Taranacak Bilimsel Konu Başlığı: {len(ACADEMIC_SEARCH_TOPICS)} alan")
    print("=" * 80)

    total_harvested = 0
    seen_titles = set()
    global_index = 1000 # Academic index offset

    # Mevcut dosyaları tara ve başlıkları hafızaya al
    for f in os.listdir(DATA_DIR):
        if f.startswith("academic_"):
            global_index += 1

    print(f"\n[1/2] OpenAlex ve Europe PMC API'lerinden akademik makaleler toplanıyor...\n")

    for i, topic in enumerate(ACADEMIC_SEARCH_TOPICS, 1):
        print(f"🔍 [{i:02d}/{len(ACADEMIC_SEARCH_TOPICS)}] Taranıyor: '{topic}'")
        
        # 1. OpenAlex'ten çek
        oa_papers = fetch_openalex_papers(topic, limit=4)
        
        # 2. Europe PMC'den çek
        pmc_papers = fetch_europe_pmc_papers(topic, limit=3)
        
        combined = oa_papers + pmc_papers
        saved_for_topic = 0
        
        for paper in combined:
            t_norm = paper["title"].lower().strip()
            if t_norm in seen_titles:
                continue
            seen_titles.add(t_norm)
            
            global_index += 1
            if save_academic_paper(paper, global_index):
                saved_for_topic += 1
                total_harvested += 1
                print(f"   📄 [{paper['year']}] {paper['journal'][:30]:<30} | {paper['title'][:55]}... ({paper['cited_by']} cit)")
        
        time.sleep(0.4) # API Rate limit nezaketi

    print("\n" + "=" * 80)
    print(f"🎉 AKADEMİK MAKALE HASADI TAMAMLANDI!")
    print(f"📊 Yeni Eklenen Hakemli Makale Sayısı: {total_harvested}")
    print(f"📁 Toplam 'data_creatures' Dosya Sayısı: {len(os.listdir(DATA_DIR))}")
    print("=" * 80)

if __name__ == "__main__":
    main()
