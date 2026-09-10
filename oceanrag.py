import streamlit as st
import streamlit.components.v1 as components
import chromadb
from sentence_transformers import SentenceTransformer
import requests
import re
import os
import json
import math
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

# Sayfa Yapılandırması ve Tema Ayarları
st.set_page_config(
    page_title="Tilikum AI: Okyanus & Bilim RAG Motoru",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS ile Arayüz Güzelleştirme
st.markdown("""
<style>
    .stApp {
        background-color: #071017;
    }
    .main-header {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e2e8f0 0%, #a2c0cd 45%, #7696a7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 1.0rem;
        color: #7f95a4;
        margin-bottom: 24px;
    }
    .gating-failed {
        background-color: #1a1012;
        color: #d19a9d;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #b8686d;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .gating-passed {
        background-color: #0e1c17;
        color: #9ac2af;
        padding: 10px 16px;
        border-radius: 8px;
        border-left: 4px solid #6b9d88;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .web-mode {
        background-color: #0f1a24;
        color: #9cb5c7;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #5e8093;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .tool-mode {
        background-color: #0a1822;
        color: #8dafc0;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #6c94a6;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .sidebar-card {
        background: rgba(13, 27, 36, 0.55);
        border: 1px solid rgba(148, 180, 196, 0.12);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Başlık Bölümü
st.markdown("<div class='main-header'>🌊 Tilikum AI: Okyanus & Bilim RAG Motoru</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Yerel Vektör Arşivi + 7 Özel Okyanus & Bilim Aracı + Otonom Canlı Web Motoru (v6)</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# SESSION STATE (Önbellek & Durum Yönetimi)
# -------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ocean_active_widgets" not in st.session_state:
    st.session_state.ocean_active_widgets = {}


# -------------------------------------------------------------------------
# OTONOM AKILLI WEB ARAMA MOTORU (DDGS + Wikipedia REST + Multi-Try)
# -------------------------------------------------------------------------
def clean_search_text(text: str) -> str:
    """Arama sorgusundaki dolgu kelimelerini ve noktalama işaretlerini temizler."""
    stop_words = [
        "hayır", "evet", "peki", "acaba", "lütfen", "bana", "anlat", "söyle",
        "nerede", "nerededir", "kaç", "kaçtır", "metre", "nedir", "nelerdir",
        "nasıl", "nasıldır", "ne kadar", "hakkında", "bilgi", "ver", "mıdır",
        "midir", "mu", "mü", "olan", "ve", "ile", "de", "da"
    ]
    cleaned = re.sub(r'[\?\!\.\,\:\;\"\'\(\)]', ' ', text)
    tokens = [w for w in cleaned.split() if w.lower() not in stop_words and len(w) > 1]
    return " ".join(tokens)

def search_web_duckduckgo(query: str, max_results: int = 4):
    """İnternette doğrudan, zengin ve asla boş dönmeyen canlı arama yapar."""
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    clean_q = clean_search_text(query)
    search_queries = [q for q in [clean_q, query] if q and len(q) > 2]
    
    # 1. DDGS ile Canlı Arama (Önce temizlenmiş, sonra orijinal sorguyla)
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for s_term in search_queries:
                raw_results = list(ddgs.text(s_term, max_results=max_results))
                if raw_results:
                    for r in raw_results:
                        title = r.get("title", "Web Kaynağı")
                        href = r.get("href", "")
                        body = r.get("body", "")
                        
                        # Wikipedia REST zenginleştirmesi
                        if "wikipedia.org/wiki/" in href:
                            try:
                                wiki_slug = href.split("wikipedia.org/wiki/")[-1].split("#")[0].strip()
                                wiki_api = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{wiki_slug}"
                                w_resp = requests.get(wiki_api, headers=headers, timeout=3)
                                if w_resp.status_code == 200:
                                    w_extract = w_resp.json().get("extract", "")
                                    if w_extract and len(w_extract) > len(body):
                                        body = w_extract
                            except Exception:
                                pass
                        
                        if body and len(body) > 30:
                            results.append({
                                "title": title,
                                "href": href,
                                "body": body
                            })
                    break
    except Exception:
        pass

    # 2. Wikipedia REST API Fallback
    if not results:
        for s_term in search_queries:
            try:
                wiki_search_url = "https://tr.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": s_term,
                    "format": "json",
                    "srlimit": max_results
                }
                resp = requests.get(wiki_search_url, params=params, headers=headers, timeout=4)
                if resp.status_code == 200:
                    search_data = resp.json()
                    for item in search_data.get("query", {}).get("search", []):
                        title = item.get("title", "")
                        if title and "fuhuş" not in title.lower():
                            sum_api = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
                            s_resp = requests.get(sum_api, headers=headers, timeout=3)
                            if s_resp.status_code == 200:
                                s_data = s_resp.json()
                                ext = s_data.get("extract", "")
                                if ext:
                                    results.append({
                                        "title": f"{title} - Vikipedi",
                                        "href": f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                        "body": ext
                                    })
                if results:
                    break
            except Exception:
                pass
            
    return results

# =========================================================================
# 1. ÖZEL OKYANUS & BİLİM ARAÇLARI (ELITE OCEAN TOOL SUITE)
# =========================================================================

# -------------------------------------------------------------------------
# [TOOL 1] OKYANUS AKINTILARI, DALGA & SICAKLIK MONİTÖRÜ (Marine Weather & Waves)
# -------------------------------------------------------------------------
KNOWN_SEAS = {
    "akdeniz": (35.5, 18.0, "Akdeniz", "Güneydoğu Avrupa & Kuzey Afrika"),
    "karadeniz": (43.0, 35.0, "Karadeniz", "Doğu Avrupa & Anadolu"),
    "ege": (38.5, 25.5, "Ege Denizi", "Türkiye & Yunanistan"),
    "marmara": (40.7, 28.2, "Marmara Denizi", "Türkiye İç Denizi"),
    "pasifik": (0.0, 160.0, "Büyük Okyanus (Pasifik)", "Küresel Okyanus"),
    "atlantik": (25.0, -40.0, "Atlas Okyanusu (Atlantik)", "Küresel Okyanus"),
    "hint": (-10.0, 75.0, "Hint Okyanusu", "Küresel Okyanus"),
    "arktik": (80.0, 0.0, "Arktik Okyanusu (Kuzey Buz)", "Kuzey Kutbu"),
    "antarktika": (-65.0, 0.0, "Güney Okyanusu (Antarktik)", "Güney Kutbu"),
    "kızıldeniz": (22.0, 38.0, "Kızıldeniz", "Ortadoğu & Afrika"),
    "baltık": (58.0, 20.0, "Baltık Denizi", "Kuzey Avrupa")
}

def get_marine_weather_and_currents(location_name: str = "Akdeniz"):
    """Seçilen deniz veya kıyı bölgesi için Open-Meteo Marine API ile dalga ve sıcaklık verisi çeker."""
    try:
        clean = str(location_name).lower().strip()
        lat, lon, sea_title, region_name = None, None, location_name.title(), "Deniz Bölgesi"
        
        for k, v in KNOWN_SEAS.items():
            if k in clean:
                lat, lon, sea_title, region_name = v
                break
                
        if lat is None:
            # Geocoding fallback
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_name}&count=1&language=tr&format=json"
            geo_res = requests.get(geo_url, timeout=4).json()
            if geo_res.get("results"):
                loc = geo_res["results"][0]
                lat, lon = loc["latitude"], loc["longitude"]
                sea_title = loc.get("name", location_name.title())
                region_name = loc.get("country", "Kıyı Bölgesi")
            else:
                lat, lon, sea_title, region_name = 35.5, 18.0, "Akdeniz", "Bölgesel Deniz"

        # 1. Marine API Çağrısı (Dalga & Akıntı Verileri)
        marine_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,wave_period,wind_wave_height&timezone=auto"
        m_resp = requests.get(marine_url, timeout=4).json()
        m_curr = m_resp.get("current", {})
        
        wave_height = m_curr.get("wave_height", 0.8)
        wave_period = m_curr.get("wave_period", 3.5)
        wave_dir = m_curr.get("wave_direction", 180)
        
        # 2. Forecast API Çağrısı (Sıcaklık & Rüzgar)
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m&timezone=auto"
        w_resp = requests.get(weather_url, timeout=4).json()
        w_curr = w_resp.get("current", {})
        
        temp_val = w_curr.get("temperature_2m", 21.0)
        wind_speed = w_curr.get("wind_speed_10m", 15.0)

        # Dalga Durum Değerlendirmesi (Mat Okyanus Tonları)
        if wave_height < 0.5:
            wave_status = "Sakin / Durgun Deniz"
            wave_color = "#76a38f"
            wave_icon = "🌊"
        elif wave_height < 1.25:
            wave_status = "Hafif Çalkantılı"
            wave_color = "#8faebd"
            wave_icon = "🌊"
        elif wave_height < 2.5:
            wave_status = "Orta Dalgalı"
            wave_color = "#c7b897"
            wave_icon = "⛵"
        elif wave_height < 4.0:
            wave_status = "Kaba & Sert Dalgalı"
            wave_color = "#b8686d"
            wave_icon = "⚠️"
        else:
            wave_status = "Ağır Fırtına / Dev Dalgalar"
            wave_color = "#a8545a"
            wave_icon = "🚨"

        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0; padding: 4px; background: transparent; overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 24px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:0.72rem;font-weight:600;color:#8aaab8;text-transform:uppercase;letter-spacing:0.12em;">🌊 Marine & Wave Monitor</div>
                <span style="font-size:0.65rem;background:rgba(138,170,184,0.12);color:#8aaab8;border:1px solid rgba(138,170,184,0.2);padding:2px 8px;border-radius:10px;font-weight:500;">CANLI VERİ</span>
            </div>
            
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                <div>
                    <div style="font-size:1.15rem;font-weight:700;color:#e2e8f0;">{sea_title}</div>
                    <div style="font-size:0.75rem;color:#7e93a2;">{region_name} • ({lat:.1f}°N, {lon:.1f}°E)</div>
                </div>
                <div style="font-size:1.5rem;opacity:0.9;">{wave_icon}</div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
                <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                    <div style="font-size:0.68rem;color:#7b8f9e;">Dalga Boyu</div>
                    <div style="font-size:1.25rem;font-weight:700;color:{wave_color};font-family:'JetBrains Mono',monospace;">{wave_height:.2f} m</div>
                    <div style="font-size:0.65rem;color:{wave_color};font-weight:500;">{wave_status}</div>
                </div>
                <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                    <div style="font-size:0.68rem;color:#7b8f9e;">Deniz / Yüzey Sıcaklığı</div>
                    <div style="font-size:1.25rem;font-weight:700;color:#9ec0ce;font-family:'JetBrains Mono',monospace;">{temp_val:.1f}°C</div>
                    <div style="font-size:0.65rem;color:#7b8f9e;">Rüzgar: {wind_speed:.0f} km/s</div>
                </div>
            </div>

            <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#5e7383;border-top:1px solid rgba(255,255,255,0.04);padding-top:6px;">
                <span>Dalga Periyodu: <b style="color:#94a8b7;">{wave_period:.1f} sn</b></span>
                <span>Dalga Yönü: <b style="color:#94a8b7;">{wave_dir}°</b></span>
            </div>
        </div>
        """

        summary_text = (
            f"🌊 **{sea_title} ({region_name}) Canlı Deniz ve Dalga Durumu:**\n"
            f"- **Dalga Yüksekliği:** {wave_height:.2f} metre ({wave_status})\n"
            f"- **Deniz/Hava Yüzey Sıcaklığı:** {temp_val:.1f}°C\n"
            f"- **Dalga Periyodu & Yönü:** {wave_period:.1f} saniye ({wave_dir}°)\n"
            f"- **Rüzgar Hızı:** {wind_speed:.0f} km/s (Deniz üzerinde ölçülen)"
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html,
            "height": 260
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Deniz hava durumu çekilirken hata oluştu: {str(e)}",
            "widget_html": None,
            "height": 0
        }

# -------------------------------------------------------------------------
# [TOOL 2] DENİZ CANLILARI & TAKSONOMİ KEŞİF KARTI (Marine Species Explorer)
# -------------------------------------------------------------------------
KNOWN_SPECIES = {
    "mavi balina": {
        "name": "Mavi Balina (Gök Balina)",
        "scientific": "Balaenoptera musculus",
        "taxonomy": "Animalia > Chordata > Mammalia > Cetacea > Balaenopteridae",
        "zone": "Epipelajik & Mezopelajik (0 - 500m)",
        "depth_val": 200,
        "zone_tag": "Epipelajik Zonu (0-200m)",
        "size": "25 - 30 metre / 150 - 200 ton (Dünyanın en büyük canlısı)",
        "diet": "Krill (Günde ~4 ton planktonik kabuklu)",
        "iucn": "Tehlikede (EN)",
        "iucn_color": "#b8686d",
        "icon": "🐋"
    },
    "katil balina": {
        "name": "Katil Balina (Orka / Tilikum)",
        "scientific": "Orcinus orca",
        "taxonomy": "Animalia > Chordata > Mammalia > Cetacea > Delphinidae",
        "zone": "Epipelajik (0 - 300m)",
        "depth_val": 150,
        "zone_tag": "Epipelajik Zonu (0-200m)",
        "size": "6 - 9 metre / 6 - 10 ton (Süper avcı tepe memeli)",
        "diet": "Balıklar, foklar, deniz aslanları ve küçük balinalar",
        "iucn": "Koruma Altında (DD)",
        "iucn_color": "#c7b897",
        "icon": "🐬"
    },
    "orka": {
        "name": "Katil Balina (Orka / Tilikum)",
        "scientific": "Orcinus orca",
        "taxonomy": "Animalia > Chordata > Mammalia > Cetacea > Delphinidae",
        "zone": "Epipelajik (0 - 300m)",
        "depth_val": 150,
        "zone_tag": "Epipelajik Zonu (0-200m)",
        "size": "6 - 9 metre / 6 - 10 ton",
        "diet": "Karnivor tepe avcı",
        "iucn": "Koruma Altında",
        "iucn_color": "#c7b897",
        "icon": "🐬"
    },
    "fener balığı": {
        "name": "Derin Deniz Fener Balığı",
        "scientific": "Ceratiidae / Lophiiformes",
        "taxonomy": "Animalia > Chordata > Actinopterygii > Lophiiformes",
        "zone": "Batipelajik & Abisopelajik (1.000 - 4.000m)",
        "depth_val": 2000,
        "zone_tag": "Batipelajik Zonu (1000-4000m)",
        "size": "20 - 100 cm (Biyolüminesans esca anteniyle avlanır)",
        "diet": "Kabuklular, küçük derin deniz balıkları",
        "iucn": "Asgari Endişe (LC)",
        "iucn_color": "#76a38f",
        "icon": "🐡"
    },
    "dev mürekkep balığı": {
        "name": "Dev Mürekkep Balığı",
        "scientific": "Architeuthis dux",
        "taxonomy": "Animalia > Mollusca > Cephalopoda > Architeuthidae",
        "zone": "Mezopelajik & Batipelajik (300 - 1.200m)",
        "depth_val": 900,
        "zone_tag": "Mezopelajik / Batipelajik (200-1000m)",
        "size": "10 - 13 metre / ~275 kg (Göz çapı 30 cm)",
        "diet": "Derin deniz balıkları ve diğer kafadanbacaklılar",
        "iucn": "Asgari Endişe (LC)",
        "iucn_color": "#76a38f",
        "icon": "🦑"
    },
    "megalodon": {
        "name": "Megalodon (Tarih Öncesi Dev Köpekbalığı)",
        "scientific": "Otodus megalodon",
        "taxonomy": "Animalia > Chordata > Chondrichthyes > Otodontidae",
        "zone": "Epipelajik Kıyı ve Açık Deniz (0 - 200m)",
        "depth_val": 100,
        "zone_tag": "Epipelajik Zonu (Tarih Öncesi)",
        "size": "15 - 18 metre / 50 - 70 ton (Isırma kuvveti 180.000 N)",
        "diet": "Büyük balinalar, deniz memelileri",
        "iucn": "Soyu Tükenmiş (EX)",
        "iucn_color": "#718290",
        "icon": "🦈"
    },
    "büyük beyaz": {
        "name": "Büyük Beyaz Köpekbalığı",
        "scientific": "Carcharodon carcharias",
        "taxonomy": "Animalia > Chordata > Chondrichthyes > Lamnidae",
        "zone": "Epipelajik (0 - 250m)",
        "depth_val": 120,
        "zone_tag": "Epipelajik Zonu (0-200m)",
        "size": "4 - 6 metre / 1 - 2.5 ton",
        "diet": "Foklar, deniz aslanları, ton balıkları",
        "iucn": "Hassas (VU)",
        "iucn_color": "#c7b897",
        "icon": "🦈"
    }
}

def get_marine_species_explorer(species_name: str = "Mavi Balina"):
    """Girilen deniz canlısının taksonomisini, yaşam derinliğini ve derinlik cetvelini üretir."""
    clean = str(species_name).lower().strip()
    data = None
    for k, v in KNOWN_SPECIES.items():
        if k in clean:
            data = v
            break
            
    if not data:
        data = {
            "name": species_name.title(),
            "scientific": f"{species_name.title()} spp.",
            "taxonomy": "Animalia > Chordata > Marine Life",
            "zone": "Pelajik Denizel Ekosistem (0 - 1.000m)",
            "depth_val": 300,
            "zone_tag": "Pelajik Zonu",
            "size": "Türe göre değişken",
            "diet": "Deniz ekosistemi besin zinciri üyesi",
            "iucn": "İnceleniyor",
            "iucn_color": "#8aaab8",
            "icon": "🌊"
        }

    widget_html = f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0; padding: 4px; background: transparent; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center;
        }}
    </style>
    <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 22px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:0.72rem;font-weight:600;color:#8aaab8;text-transform:uppercase;letter-spacing:0.12em;">🧬 Marine Biodiversity Explorer</div>
            <span style="font-size:0.65rem;background:{data['iucn_color']}18;color:{data['iucn_color']};border:1px solid {data['iucn_color']}40;padding:2px 8px;border-radius:10px;font-weight:600;">{data['iucn']}</span>
        </div>
        
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="font-size:1.8rem;opacity:0.9;">{data['icon']}</div>
            <div>
                <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">{data['name']}</div>
                <div style="font-size:0.75rem;font-style:italic;color:#7e93a2;">{data['scientific']}</div>
            </div>
        </div>

        <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;margin-bottom:10px;">
            <div style="font-size:0.66rem;color:#5e7383;margin-bottom:2px;letter-spacing:0.05em;">TAKSONOMİK HİYERARŞİ</div>
            <div style="font-size:0.72rem;color:#b0c4de;font-family:'JetBrains Mono',monospace;">{data['taxonomy']}</div>
        </div>

        <!-- Dikey Derinlik Cetveli Göstergesi (Mat Okyanus Gradyanı) -->
        <div style="background:#061017;border:1px solid rgba(148,180,196,0.1);border-radius:9px;padding:10px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-bottom:4px;">
                <span style="color:#7b8f9e;">Yaşam Katmanı:</span>
                <span style="color:#9ec0ce;font-weight:600;">{data['zone_tag']}</span>
            </div>
            <div style="width:100%;height:8px;background:linear-gradient(90deg, #6c93a3 0%, #4a6f80 30%, #29424f 65%, #101c24 100%);border-radius:4px;position:relative;">
                <div style="position:absolute;left:{min(max(data['depth_val']/40, 5), 90)}%;top:-4px;width:16px;height:16px;background:#d4c5a9;border:2px solid #ffffff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.5);transform:translateX(-50%);"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.62rem;color:#5e7383;margin-top:4px;">
                <span>0m (Güneş Işığı)</span>
                <span>1000m (Gece)</span>
                <span>4000m (Abis)</span>
                <span>11000m (Hadal)</span>
            </div>
        </div>

        <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#94a8b7;">
            <span>📏 Boyut: <b style="color:#d9e2ec;">{data['size'].split('/')[0]}</b></span>
            <span>🍽️ Diyet: <b style="color:#d9e2ec;">{data['diet'][:25]}...</b></span>
        </div>
    </div>
    """

    summary_text = (
        f"🐋 **{data['name']} ({data['scientific']}) Keşif Profili:**\n"
        f"- **Taksonomi:** {data['taxonomy']}\n"
        f"- **Yaşam Zonu & Derinlik:** {data['zone']}\n"
        f"- **Korunma Durumu (IUCN):** {data['iucn']}\n"
        f"- **Fiziksel Özellikler:** {data['size']}\n"
        f"- **Beslenme & Ekolojik Rol:** {data['diet']}"
    )
    return {
        "status": "success",
        "message": summary_text,
        "widget_html": widget_html,
        "height": 320
    }

# -------------------------------------------------------------------------
# [TOOL 3] GELGİT & AY EVRESİ HESAPLAYICI (Tide & Moon Phase Tracker)
# -------------------------------------------------------------------------
def get_tide_and_moon_phase(date_str: str = None):
    """Astronomik ay evresini, aydınlanma yüzdesini ve denizlerdeki gelgit (medcezir) etkisini hesaplar."""
    try:
        now = datetime.now()
        year, month, day = now.year, now.month, now.day
        if month < 3:
            year -= 1
            month += 12
        c = 365.25 * year
        e = 30.6 * month
        jd = c + e + day - 694039.09
        jd /= 29.5305882
        b = int(jd)
        jd -= b
        phase_val = round(jd * 8)
        if phase_val >= 8:
            phase_val = 0
            
        phase_catalog = [
            ("Yeni Ay (New Moon)", "🌑", "Büyük Gelgit (Spring Tide) — Ay ve Güneş çekimi hizalı, gelgit farkı maksimum.", 95),
            ("Hilal / Büyüyen (Waxing Crescent)", "🌒", "Orta Düzey Gelgit — Yükselen akıntılar.", 55),
            ("İlk Dördün (First Quarter)", "🌓", "Küçük Gelgit (Neap Tide) — Çekim kuvvetleri birbirini dengeler, su hareketi düşük.", 30),
            ("Şişkin Ay / Büyüyen (Waxing Gibbous)", "🌔", "Güçlenen Gelgit Hareketi.", 70),
            ("Dolunay (Full Moon)", "🌕", "Maksimum Büyük Gelgit (King Spring Tide) — Güçlü akıntılar ve yüksek sular.", 100),
            ("Şişkin Ay / Küçülen (Waning Gibbous)", "🌖", "Yavaşlayan Gelgit Hareketi.", 70),
            ("Son Dördün (Last Quarter)", "🌗", "Küçük Gelgit (Neap Tide) — Düşük su seviyesi dalgalanması.", 30),
            ("Hilal / Küçülen (Waning Crescent)", "🌘", "Orta Düzey Gelgit Hareketi.", 55)
        ]
        p_name, p_icon, tide_desc, tide_pct = phase_catalog[phase_val]
        illumination = round((1 - math.cos(jd * 2 * math.pi)) / 2 * 100)

        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0; padding: 4px; background: transparent; overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(199,184,151,0.2);border-radius:14px;padding:18px 24px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:0.72rem;font-weight:600;color:#c7b897;text-transform:uppercase;letter-spacing:0.12em;">🌔 Celestial Tide & Moon Phase</div>
                <span style="font-size:0.65rem;background:rgba(199,184,151,0.12);color:#c7b897;border:1px solid rgba(199,184,151,0.2);padding:2px 8px;border-radius:10px;font-weight:500;">ASTRONOMİK CANLI</span>
            </div>
            
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                <div>
                    <div style="font-size:1.15rem;font-weight:700;color:#e2e8f0;">{p_name}</div>
                    <div style="font-size:0.75rem;color:#7e93a2;">Ay Aydınlanma Oranı: <b style="color:#d4c5a9;">%{illumination}</b></div>
                </div>
                <div style="font-size:2.2rem;opacity:0.9;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.4));">{p_icon}</div>
            </div>

            <!-- Gelgit Gücü Gösterge Çubuğu (Mat Kum & Deniz Gradyanı) -->
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:10px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:0.72rem;margin-bottom:4px;">
                    <span style="color:#7b8f9e;">Okyanus Gelgit Şiddeti:</span>
                    <span style="color:#c7b897;font-weight:600;">%{tide_pct}</span>
                </div>
                <div style="width:100%;height:6px;background:#111e28;border-radius:3px;overflow:hidden;">
                    <div style="width:{tide_pct}%;height:100%;background:linear-gradient(90deg, #6c93a3, #c7b897);border-radius:3px;"></div>
                </div>
                <div style="font-size:0.68rem;color:#a3b8c6;margin-top:6px;line-height:1.3;">{tide_desc}</div>
            </div>
            
            <div style="font-size:0.68rem;color:#5e7383;text-align:right;">Okyanus sularının yerçekimsel hareket skalası.</div>
        </div>
        """

        summary_text = (
            f"🌔 **Astronomik Ay Evresi ve Gelgit (Medcezir) Analizi:**\n"
            f"- **Mevcut Ay Evresi:** {p_name} ({p_icon})\n"
            f"- **Ay Aydınlanma Oranı:** %{illumination}\n"
            f"- **Gelgit Dinamiği:** {tide_desc}\n"
            f"- **Deniz Canlılarına Etkisi:** Mercanların yumurtlama periyotları ve kıyı balıkçılığı bu evrede en yüksek biyolojik aktiviteyi gösterir."
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html,
            "height": 270
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ay evresi hesaplanırken hata: {str(e)}",
            "widget_html": None,
            "height": 0
        }

# -------------------------------------------------------------------------
# [TOOL 4] DERİNLİK, KATMAN & HİDROSTATİK BASINÇ SİMÜLATÖRÜ (Depth & Pressure)
# -------------------------------------------------------------------------
def calculate_ocean_depth_pressure(depth_m: float = 10994.0):
    """Herhangi bir derinlik için hidrostatik basıncı (Bar, Atm, PSI), foton ışık geçirgenliğini ve sonar ses hızını hesaplar."""
    try:
        depth = max(0.0, float(depth_m))
        density = 1025.0 # Deniz suyu yoğunluğu kg/m3
        g = 9.80665
        p_pa = (density * g * depth) + 101325.0
        p_bar = p_pa / 100000.0
        p_atm = p_bar / 1.01325
        p_kg_cm2 = p_pa / 98066.5
        p_psi = p_pa / 6894.76
        
        # Mackenzie Sualtı Ses Hızı Formülü (T=4°C, S=35 PSU)
        sound_speed = 1448.96 + (4.591 * 4) - (5.304e-2 * 16) + (1.63e-2 * depth)
        
        if depth <= 200:
            zone_title = "Epipelajik Zonu (Güneş Işığı)"
            light_pct = max(1.0, 100.0 - (depth * 0.495))
            light_desc = f"%{light_pct:.1f} Güneş Işığı (Fotosentez Mümkün)"
            temp_desc = "18°C - 26°C"
            zone_color = "#76a38f"
        elif depth <= 1000:
            zone_title = "Mezopelajik Zonu (Alacakaranlık)"
            light_desc = "%0.1 - %0.01 Zayıf Işık / Biyolüminesans"
            temp_desc = "4°C - 10°C"
            zone_color = "#8faebd"
        elif depth <= 4000:
            zone_title = "Batipelajik Zonu (Gece Zonu)"
            light_desc = "%0 Sıfır Güneş Işığı (Zifiri Karanlık)"
            temp_desc = "2°C - 4°C"
            zone_color = "#9b93b8"
        elif depth <= 6000:
            zone_title = "Abisopelajik Zonu (Uçurum)"
            light_desc = "%0 Işık Yok (Aşırı Hidrostatik Basınç)"
            temp_desc = "1°C - 2°C"
            zone_color = "#7e859b"
        else:
            zone_title = "Hadalpelajik Zonu (Okyanus Çukurları)"
            light_desc = "%0 Işık Yok (Hadal Ekosistem)"
            temp_desc = "1°C - 4°C"
            zone_color = "#b8686d"

        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0; padding: 4px; background: transparent; overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 24px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:0.72rem;font-weight:600;color:#8aaab8;text-transform:uppercase;letter-spacing:0.12em;">🤿 Hydrostatic Pressure Simulator</div>
                <span style="font-size:0.65rem;background:{zone_color}18;color:{zone_color};border:1px solid {zone_color}35;padding:2px 8px;border-radius:10px;font-weight:600;">{zone_title.split(' ')[0]}</span>
            </div>
            
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
                <div style="font-size:1.55rem;font-weight:700;color:#e2e8f0;font-family:'JetBrains Mono',monospace;">{depth:,.0f} m</div>
                <div style="font-size:0.8rem;color:{zone_color};font-weight:600;">{zone_title}</div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
                <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                    <div style="font-size:0.68rem;color:#7b8f9e;">Hidrostatik Basınç (Bar)</div>
                    <div style="font-size:1.25rem;font-weight:700;color:#c7b897;font-family:'JetBrains Mono',monospace;">{p_bar:,.1f} Bar</div>
                    <div style="font-size:0.65rem;color:#5e7383;">({p_atm:,.0f} Atmosfer)</div>
                </div>
                <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                    <div style="font-size:0.68rem;color:#7b8f9e;">Birim Alan Basıncı</div>
                    <div style="font-size:1.25rem;font-weight:700;color:#b8686d;font-family:'JetBrains Mono',monospace;">{p_kg_cm2:,.1f}</div>
                    <div style="font-size:0.65rem;color:#5e7383;">kg / cm²</div>
                </div>
            </div>

            <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#7b8f9e;border-top:1px solid rgba(255,255,255,0.04);padding-top:6px;">
                <span>Işık: <b style="color:#b0c4de;">{light_desc[:22]}...</b></span>
                <span>Ses Hızı: <b style="color:#9ec0ce;">{sound_speed:.0f} m/s</b></span>
            </div>
        </div>
        """

        summary_text = (
            f"🤿 **Okyanus Derinlik ve Basınç Simülasyonu ({depth:,.0f} Metre):**\n"
            f"- **Okyanus Zonu:** {zone_title}\n"
            f"- **Hidrostatik Basınç:** {p_bar:,.2f} Bar ({p_atm:,.2f} Atmosfer / {p_psi:,.1f} PSI)\n"
            f"- **Santimetrekareye Düşen Ağırlık:** {p_kg_cm2:,.2f} kg/cm²\n"
            f"- **Güneş Işığı Geçirgenliği:** {light_desc}\n"
            f"- **Sualtı Ses Yayılma Hızı:** {sound_speed:.1f} m/s (Mackenzie Formülü)"
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html,
            "height": 260
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Derinlik hesaplanırken hata: {str(e)}",
            "widget_html": None,
            "height": 0
        }

# -------------------------------------------------------------------------
# [TOOL 5] AKILLI OKYANUS TERİMLERİ & KAVRAM KARTI (Glossary & Concepts)
# -------------------------------------------------------------------------
OCEAN_GLOSSARY = {
    "termohalin": {
        "title": "Termohalin Dolaşımı (Büyük Okyanus Taşıyıcı Bandı)",
        "def": "Sıcaklık (termo) ve tuzluluk (halin) farklarından kaynaklanan yoğunluk gradyanlarının tetiklediği küresel derin okyanus akıntı döngüsüdür.",
        "cause": "Kutuplarda soğuyan ve tuzlanan ağır suların dibe batması.",
        "effect": "Dünya iklimini dengeler, tropiklerin aşırı ısınmasını ve kutupların donmasını engeller.",
        "importance": "Döngünün yavaşlaması Avrupa'da ani buzul çağını tetikleyebilir."
    },
    "asitlenme": {
        "title": "Okyanus Asitlenmesi (Ocean Acidification)",
        "def": "Atmosferdeki fazla CO2 gazının deniz suyu tarafından emilerek karbonik asit oluşturması ve suyun pH değerini düşürmesidir.",
        "cause": "Fosil yakıt emisyonları sonucu atmosferik CO2 artışı.",
        "effect": "Kalsiyum karbonat ($CaCO_3$) iyonlarının azalması, mercanların ve kabuklu canlıların kabuk bağlayamaması.",
        "importance": "Deniz besin piramidinin tabanındaki fitoplankton ve mercan resiflerini yok oluş tehlikesine sokar."
    },
    "upwelling": {
        "title": "Upwelling (Yukarı Yükselim Akıntısı)",
        "def": "Rüzgarların yüzey sularını kıyıdan uzaklaştırmasıyla derinlerdeki besin zengini soğuk suların yüzeye çıkması olayıdır.",
        "cause": "Coriolis kuvveti ve kıyıya paralel esen rüzgarlar.",
        "effect": "Yüzeyde fitoplankton patlaması ve olağanüstü zengin balık popülasyonları oluşur.",
        "importance": "Dünya balıkçılık üretiminin %50'den fazlası bu alanlarda gerçekleşir."
    },
    "hidrotermal": {
        "title": "Hidrotermal Bacalar (Sualtı Gayzerleri)",
        "def": "Okyanus tabanındaki magmatik yarıklardan çıkan, 400°C sıcaklıkta ve mineralce zengin suların oluşturduğu bacalardır.",
        "cause": "Tektonik levha sınırlarında deniz suyunun magma ile teması.",
        "effect": "Güneş ışığından bağımsız, kemosentez yapan bakterilere dayalı eşsiz ekosistemler oluşturur.",
        "importance": "Dünyadaki ilk yaşamın bu bacalarda başladığı düşünülmektedir."
    },
    "çöp": {
        "title": "Büyük Pasifik Çöp Girdabı (Gyre Plastic Patch)",
        "def": "Okyanus akıntı girdaplarının (gyre) merkezinde toplanan milyonlarca tonluk devasa plastik ve mikroplastik atık alanıdır.",
        "cause": "Karalardan atılan plastik atıkların okyanus akıntılarıyla merkezde hapsolması.",
        "effect": "Deniz kaplumbağaları, kuşlar ve balıklar tarafından yutulup besin zincirine karışması.",
        "importance": "İnsan sağlığına mikroplastik olarak geri dönen küresel çevre felaketi."
    }
}

def get_ocean_concept_glossary(term_name: str = "Termohalin Dolaşımı"):
    """Okyanus bilimi terimlerinin infografik özetini ve neden-sonuç akış kartını üretir."""
    clean = str(term_name).lower().strip()
    data = None
    for k, v in OCEAN_GLOSSARY.items():
        if k in clean:
            data = v
            break
            
    if not data:
        data = {
            "title": term_name.title(),
            "def": f"{term_name.title()}, okyanus bilimlerinde denizel sistemlerin hidrolojik ve biyolojik dengesini ifade eden temel kavramdır.",
            "cause": "Oşinografik fiziksel ve kimyasal süreçler.",
            "effect": "Denizel biyoçeşitlilik ve küresel iklim dengesi.",
            "importance": "Deniz ekosistemlerinin korunmasında kritik role sahiptir."
        }

    widget_html = f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0; padding: 4px; background: transparent; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center;
        }}
    </style>
    <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 22px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:0.72rem;font-weight:600;color:#8aaab8;text-transform:uppercase;letter-spacing:0.12em;">📚 Oceanic Concept Card</div>
            <span style="font-size:0.65rem;background:rgba(138,170,184,0.12);color:#8aaab8;border:1px solid rgba(138,170,184,0.2);padding:2px 8px;border-radius:10px;font-weight:600;">TERİM & ANALİZ</span>
        </div>
        
        <div style="font-size:1.05rem;font-weight:700;color:#e2e8f0;margin-bottom:6px;">{data['title']}</div>
        <div style="font-size:0.75rem;color:#7e93a2;line-height:1.4;margin-bottom:10px;">{data['def']}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:8px;padding:8px;">
                <div style="font-size:0.65rem;font-weight:600;color:#8faebd;letter-spacing:0.04em;">NEDEN / MEKANİZMA</div>
                <div style="font-size:0.7rem;color:#b0c4de;line-height:1.3;">{data['cause']}</div>
            </div>
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:8px;padding:8px;">
                <div style="font-size:0.65rem;font-weight:600;color:#c7b897;letter-spacing:0.04em;">KÜRESEL ETKİ</div>
                <div style="font-size:0.7rem;color:#b0c4de;line-height:1.3;">{data['effect']}</div>
            </div>
        </div>

        <div style="font-size:0.7rem;color:#9ac2af;background:rgba(107,157,136,0.1);border:1px solid rgba(107,157,136,0.15);padding:6px 8px;border-radius:6px;">
            💡 <b>Ekolojik Önemi:</b> {data['importance']}
        </div>
    </div>
    """

    summary_text = (
        f"📚 **Okyanus Kavramı: {data['title']}**\n"
        f"- **Tanım:** {data['def']}\n"
        f"- **Neden/Mekanizma:** {data['cause']}\n"
        f"- **Etkileri:** {data['effect']}\n"
        f"- **Ekolojik Önemi:** {data['importance']}"
    )
    return {
        "status": "success",
        "message": summary_text,
        "widget_html": widget_html,
        "height": 280
    }

# -------------------------------------------------------------------------
# [TOOL 6] DENİZ SEVİYESİ YÜKSELİM SİMÜLATÖRÜ (Sea Level Rise Simulator)
# -------------------------------------------------------------------------
def simulate_sea_level_rise(temp_increase_c: float = 2.0):
    """IPCC küresel ısınma senaryolarına (+1.0°C - +4.0°C) göre deniz seviyesi artışını simüle eder."""
    try:
        t = float(temp_increase_c)
        if t <= 1.0:
            rise_cm = 20
            ice_loss_gt = 150
            risk_level = "Düşük / Yönetilebilir"
            risk_color = "#76a38f"
            affected = "Kıyı şeridi erozyonları, sığ resiflerde lokal ağarma."
        elif t <= 1.5:
            rise_cm = 40
            ice_loss_gt = 280
            risk_level = "Orta / Hassas Eşik"
            risk_color = "#c7b897"
            affected = "Maldivler ve Tuvalu'da kıyı su baskınları, mercanların %70 kaybı."
        elif t <= 2.0:
            rise_cm = 65
            ice_loss_gt = 420
            risk_level = "Yüksek Risk"
            risk_color = "#c9876a"
            affected = "Venedik, Miami, Bangladeş kıyı ovaları taşkınları, mercanların %99 yok oluşu."
        elif t <= 3.0:
            rise_cm = 110
            ice_loss_gt = 800
            risk_level = "Çok Yüksek / Tehlikeli"
            risk_color = "#b8686d"
            affected = "İstanbul Boğazı kıyı hatları, New York ve Şanghay gibi metropollerde göçler."
        else:
            rise_cm = 220
            ice_loss_gt = 1500
            risk_level = "Katastrofik Çöküş"
            risk_color = "#a8545a"
            affected = "Grönland ve Batı Antarktika buz örtüsünün geri dönülmez erimesi, yüz milyonlarca kıyı mültecisi."

        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0; padding: 4px; background: transparent; overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 24px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:0.72rem;font-weight:600;color:#b8686d;text-transform:uppercase;letter-spacing:0.12em;">🌡️ Sea Level Rise Simulator</div>
                <span style="font-size:0.65rem;background:{risk_color}18;color:{risk_color};border:1px solid {risk_color}35;padding:2px 8px;border-radius:10px;font-weight:600;">IPCC SENARYOSU</span>
            </div>
            
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
                <div style="font-size:1.55rem;font-weight:700;color:#e2e8f0;font-family:'JetBrains Mono',monospace;">+{t:.1f}°C Isınma</div>
                <div style="font-size:1.25rem;font-weight:700;color:#9ec0ce;font-family:'JetBrains Mono',monospace;">+{rise_cm} cm</div>
            </div>

            <!-- Deniz Seviyesi Göstergesi -->
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:10px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:0.72rem;margin-bottom:4px;">
                    <span style="color:#7b8f9e;">Yükselme Seviyesi:</span>
                    <span style="color:{risk_color};font-weight:600;">{risk_level}</span>
                </div>
                <div style="width:100%;height:7px;background:#111e28;border-radius:3px;overflow:hidden;">
                    <div style="width:{min(rise_cm/2.2, 100)}%;height:100%;background:linear-gradient(90deg, #6c93a3, {risk_color});border-radius:3px;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:#5e7383;margin-top:4px;">
                    <span>Buzul Kaybı: ~{ice_loss_gt} Gt/yıl</span>
                    <span>Termal Genleşme: %40 pay</span>
                </div>
            </div>

            <div style="font-size:0.7rem;color:#b0c4de;background:#061017;border-left:3px solid {risk_color};padding:8px;border-radius:6px;line-height:1.3;">
                ⚠️ <b>Risk Altındaki Alanlar:</b> {affected}
            </div>
        </div>
        """

        summary_text = (
            f"🌡️ **IPCC Küresel Isınma & Deniz Seviyesi Yükselim Simülasyonu (+{t:.1f}°C):**\n"
            f"- **Tahmini Deniz Seviyesi Artışı:** +{rise_cm} cm\n"
            f"- **Kutup Buzulu Erime Hızı:** ~{ice_loss_gt} Milyar Ton (Gt) / yıl\n"
            f"- **Risk Seviyesi:** {risk_level}\n"
            f"- **Karasal & Ekolojik Etki:** {affected}"
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html,
            "height": 270
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Simülasyon hatası: {str(e)}",
            "widget_html": None,
            "height": 0
        }

# -------------------------------------------------------------------------
# [TOOL 7] OKYANUS ÇUKURLARI & BATİMETRİ ATLASI (Ocean Trench Atlas)
# -------------------------------------------------------------------------
KNOWN_TRENCHES = {
    "mariana": {
        "name": "Mariana Çukuru (Challenger Derinliği)",
        "ocean": "Büyük Okyanus (Kuzeybatı Pasifik)",
        "depth": 10994,
        "pressure_bar": 1106,
        "plates": "Pasifik Levhası vs Mariana Levhası Dalma-Batma Zonu",
        "explorers": "1960 (Trieste - Piccard & Walsh), 2012 (James Cameron), 2019 (Victor Vescovo)",
        "features": "Dünyanın bilinen en derin noktası, kemosentetik amfipotlar ve salyangoz balıkları."
    },
    "tonga": {
        "name": "Tonga Çukuru (Horizon Derinliği)",
        "ocean": "Güney Pasifik Okyanusu",
        "depth": 10882,
        "pressure_bar": 1094,
        "plates": "Pasifik Levhası vs Hint-Avustralya Levhası",
        "explorers": "Horizon Seferi (1952), Victor Vescovo (2019)",
        "features": "Dünyanın en hızlı levha hareketine sahip dalma-batma kuşağı (24 cm/yıl)."
    },
    "porto riko": {
        "name": "Porto Riko Çukuru (Milwaukee Derinliği)",
        "ocean": "Atlas Okyanusu (Atlantik)",
        "depth": 8376,
        "pressure_bar": 842,
        "plates": "Karayip Levhası vs Kuzey Amerika Levhası",
        "explorers": "Archimède (1964), Victor Vescovo (2018)",
        "features": "Atlantik Okyanusu'nun en derin noktası, devasa tsunami üretme potansiyeli."
    },
    "java": {
        "name": "Java / Sunda Çukuru",
        "ocean": "Hint Okyanusu",
        "depth": 7450,
        "pressure_bar": 749,
        "plates": "Hint-Avustralya Levhası vs Avrasya Levhası",
        "explorers": "Five Deeps Expedition (2019)",
        "features": "Hint Okyanusu'nun en derin çukuru, 2004 Sumatra depreminin merkez üssü kuşağı."
    },
    "orta atlantik": {
        "name": "Orta Atlantik Sırtı (Mid-Atlantic Ridge)",
        "ocean": "Atlas Okyanusu Boyunca",
        "depth": 3000,
        "pressure_bar": 305,
        "plates": "Avrasya/Kuzey Amerika ve Afrika/Güney Amerika Ayrılma Zonu",
        "explorers": "HMS Challenger Seferi (1872)",
        "features": "16.000 km uzunluğunda dünyanın en uzun sualtı sıradağları zinciri ve hidrotermal bacalar."
    }
}

def get_ocean_trench_atlas(trench_name: str = "Mariana"):
    """Büyük okyanus çukurlarının, batimetrik derinliklerinin ve keşif tarihinin atlas kartını üretir."""
    clean = str(trench_name).lower().strip()
    data = None
    for k, v in KNOWN_TRENCHES.items():
        if k in clean:
            data = v
            break
            
    if not data:
        data = KNOWN_TRENCHES["mariana"]

    widget_html = f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0; padding: 4px; background: transparent; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center;
        }}
    </style>
    <div style="background:linear-gradient(145deg, #0d1b24 0%, #08121a 100%);color:#e2e8f0;border:1px solid rgba(148,180,196,0.16);border-radius:14px;padding:18px 24px;width:100%;max-width:400px;box-shadow:0 10px 28px rgba(0,0,0,0.45);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:0.72rem;font-weight:600;color:#8aaab8;text-transform:uppercase;letter-spacing:0.12em;">⚓ Ocean Trench & Bathymetry</div>
            <span style="font-size:0.65rem;background:rgba(138,170,184,0.12);color:#8aaab8;border:1px solid rgba(138,170,184,0.2);padding:2px 8px;border-radius:10px;font-weight:600;">HADAL ATLAS</span>
        </div>
        
        <div style="font-size:1.15rem;font-weight:700;color:#e2e8f0;margin-bottom:2px;">{data['name']}</div>
        <div style="font-size:0.75rem;color:#7e93a2;margin-bottom:8px;">📍 {data['ocean']}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                <div style="font-size:0.68rem;color:#7b8f9e;">Maksimum Derinlik</div>
                <div style="font-size:1.25rem;font-weight:700;color:#b8686d;font-family:'JetBrains Mono',monospace;">{data['depth']:,} m</div>
            </div>
            <div style="background:#061017;border:1px solid rgba(255,255,255,0.04);border-radius:9px;padding:8px 10px;">
                <div style="font-size:0.68rem;color:#7b8f9e;">Taban Basıncı</div>
                <div style="font-size:1.25rem;font-weight:700;color:#c7b897;font-family:'JetBrains Mono',monospace;">{data['pressure_bar']} Bar</div>
            </div>
        </div>

        <div style="background:#061017;border-left:3px solid #6c94a6;padding:6px 10px;border-radius:6px;font-size:0.68rem;color:#b0c4de;line-height:1.3;margin-bottom:6px;">
            🧭 <b>Levha Tektoniği:</b> {data['plates']}
        </div>
        <div style="font-size:0.65rem;color:#5e7383;">🚀 <b>Keşifler:</b> {data['explorers']}</div>
    </div>
    """

    summary_text = (
        f"⚓ **{data['name']} Batimetrik Atlası:**\n"
        f"- **Konum:** {data['ocean']}\n"
        f"- **Maksimum Derinlik:** {data['depth']:,} metre\n"
        f"- **Taban Basıncı:** ~{data['pressure_bar']} Bar\n"
        f"- **Jeoloji:** {data['plates']}\n"
        f"- **Önemli Keşif Seferleri:** {data['explorers']}\n"
        f"- **Biyolojik & Fiziksel Nitelik:** {data['features']}"
    )
    return {
        "status": "success",
        "message": summary_text,
        "widget_html": widget_html,
        "height": 270
    }

# =========================================================================
# 2. AKILLI OKYANUS ARAÇLARI YÖNLENDİRİCİSİ (OCEAN TOOL ROUTER)
# =========================================================================
def detect_and_execute_ocean_tool(query: str):
    """Kullanıcı sorgusunu analiz ederek uygun okyanus aracını otonom olarak tetikler."""
    q = str(query).lower()
    
    # 1. Deniz Hava Durumu & Dalga
    if any(k in q for k in ["dalga", "deniz sıcaklığı", "deniz suyu sıcaklığı", "deniz hava", "akdeniz hava", "karadeniz hava", "ege dalga", "marmara dalga", "marine weather"]):
        for s in KNOWN_SEAS.keys():
            if s in q:
                return get_marine_weather_and_currents(s)
        return get_marine_weather_and_currents(query)

    # 2. Deniz Biyolojisi & Canlı Keşfi
    if any(k in q for k in ["balina", "köpekbalığı", "fener balığı", "mürekkep balığı", "megalodon", "orka", "canlısı", "hangi katmanda yaşar", "hangi derinlikte yaşar"]):
        for sp in KNOWN_SPECIES.keys():
            if sp in q:
                return get_marine_species_explorer(sp)
        return get_marine_species_explorer(query)

    # 3. Gelgit & Ay Evresi
    if any(k in q for k in ["gelgit", "ay evresi", "dolunay", "hilal", "medcezir", "tide", "moon phase"]):
        return get_tide_and_moon_phase()

    # 4. Derinlik Basıncı & Simülasyon
    if any(k in q for k in ["basınç", "kaç bar", "kaç metre derinlik", "hidrostatik basınç", "derinlikte basınç", "11000 metre", "10000 metre", "metre basınç"]):
        numbers = re.findall(r'\d+', query)
        depth_val = float(numbers[0]) if numbers else 10994.0
        return calculate_ocean_depth_pressure(depth_val)

    # 5. Okyanus Terimleri & Kavramlar
    if any(k in q for k in ["termohalin", "asitlenme", "upwelling", "hidrotermal", "termoklin", "çöp girdabı", "ötrofikasyon"]):
        return get_ocean_concept_glossary(query)

    # 6. Deniz Seviyesi Yükselimi & İklim
    if any(k in q for k in ["deniz seviyesi", "buzul erimesi", "küresel ısınma okyanus", "derece artarsa", "sea level rise"]):
        temp_val = 2.0
        if "1.5" in q: temp_val = 1.5
        elif "1" in q: temp_val = 1.0
        elif "3" in q: temp_val = 3.0
        elif "4" in q: temp_val = 4.0
        return simulate_sea_level_rise(temp_val)

    # 7. Okyanus Çukurları & Batimetri
    if any(k in q for k in ["çukuru", "challenger deep", "trench", "orta atlantik sırtı", "batimetri"]):
        return get_ocean_trench_atlas(query)

    return None

# -------------------------------------------------------------------------
# 1. KATMAN: SORGU BAĞLAMLAŞTIRMA (Query Reformulation & Entity Linking)
# -------------------------------------------------------------------------
def contextualize_query(query: str, chat_history: list, llm_url: str, model: str) -> str:
    """Geçmiş konuşmalardaki ana varlığı (örn: Mariana Çukuru) takip sorusuna enjekte eder."""
    if not chat_history:
        return query
    
    # 1. Kural Tabanlı Hızlı Varlık Tespiti (Pekin veya alakasız kelimeleri eler)
    pronouns = ["orası", "oraya", "orada", "oranın", "bunun", "buna", "bunda", "bunlar", "onlar", "o", "burası", "bu"]
    words = [w.lower().strip("?!.,") for w in query.split()]
    has_pronoun = any(p in words for p in pronouns)
    
    # Geçmişteki gerçek varlıkları tara (ilk kullanıcı sorusu genelde asıl varlıktır)
    main_subject = ""
    for m in chat_history:
        if m.get("role") == "user":
            user_text = m.get("content", "")
            # "Mariana Çukuru", "Mercan Resifleri", "Pasifik" vb.
            clean_subject = clean_search_text(user_text)
            if clean_subject and "pekin" not in clean_subject.lower() and len(clean_subject) > 3:
                main_subject = clean_subject
                break
    
    # Eğer zamir varsa ve geçmişte bir konu bulunduysa doğrudan enjekte et
    if has_pronoun and main_subject:
        cleaned_sub_q = clean_search_text(query)
        # Zamirleri temizle
        sub_tokens = [w for w in cleaned_sub_q.split() if w.lower() not in pronouns]
        merged_query = f"{main_subject} {' '.join(sub_tokens)}".strip()
        if len(merged_query) > len(query):
            return merged_query

    # 2. LLM Tabanlı Reformulation (Fallback)
    try:
        history_snippets = []
        for m in chat_history[-4:]:
            role = "Kullanıcı" if m["role"] == "user" else "Asistan"
            content = m["content"][:200]
            # Pekin hatasını prompta bulaştırma
            if "pekin" not in content.lower():
                history_snippets.append(f"{role}: {content}")
        
        if history_snippets:
            history_text = "\n".join(history_snippets)
            system_prompt = (
                "Sen bir arama sorgusu optimize edicisin. Sohbet geçmişini okuyarak kullanıcının son sorusundaki "
                "zamirleri ('orası', 'bunun' vb.) geçmişteki asıl konuyla değiştir. Sadece tek satır arama sorgusunu yaz."
            )
            user_prompt = f"SOHBET GEÇMİŞİ:\n{history_text}\n\nSON SORU: {query}\n\nDÜZELTİLMİŞ SORGUSU:"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 50,
                "stream": False
            }
            resp = requests.post(f"{llm_url}/v1/chat/completions", json=payload, timeout=3)
            if resp.status_code == 200:
                reformulated = resp.json()["choices"][0]["message"]["content"].strip()
                reformulated = re.sub(r'<think>.*?</think>', '', reformulated, flags=re.DOTALL).strip()
                reformulated = re.sub(r'^(Düzeltilmiş.*?:\s*|Çıktı:\s*|Soru:\s*)', '', reformulated, flags=re.IGNORECASE).strip()
                reformulated = fix_turkish_encoding(reformulated)
                first_line = reformulated.split("\n")[0].strip()
                if first_line and len(first_line) > 3 and "pekin" not in first_line.lower():
                    return first_line
    except Exception:
        pass
        
    return query

# -------------------------------------------------------------------------
# PYDANTIC YAPILANDIRILMIŞ ÇIKTI MODELİ
# -------------------------------------------------------------------------
class RAGResponse(BaseModel):
    """LLM'in her zaman bu şemaya uygun JSON döndürmesi beklenir."""
    answer: str = Field(description="Soruya verilen Türkçe cevap. Sadece bağlamdaki bilgilerle.")
    sources: list[str] = Field(default=[], description="Cevabı destekleyen kaynak dosya adları veya web siteleri.")
    confidence: str = Field(default="Orta", description="Cevabın güven seviyesi: Düşük | Orta | Yüksek")
    in_context: bool = Field(default=True, description="Sorunun cevabı bağlamda bulundu mu?")
    mode: str = Field(default="local", description="Cevap kaynağı: 'local' (yerel döküman) | 'web' (internet)")

# UTF-8 Bozuk Karakter Onarıcı (Mojibake Fixer)
def fix_turkish_encoding(text: str) -> str:
    """UTF-8 baytlarının latin-1 olarak yanlış yorumlanmasını (Ã¼ -> ü vb.) düzeltir."""
    if not text:
        return ""
    try:
        # Eğer çift encode/latin-1 bozulması varsa düzelt
        fixed = text.encode('latin1').decode('utf-8')
        return fixed
    except Exception:
        # Hata durumunda karakter bazlı yaygın bozulmaları düzelt
        replacements = {
            "Ã¼": "ü", "Ãœ": "Ü",
            "Ä±": "ı", "Ä°": "İ",
            "ÅŸ": "ş", "Åž": "Ş",
            "Ã§": "ç", "Ã‡": "Ç",
            "Ã¶": "ö", "Ã–": "Ö",
            "ÄŸ": "ğ", "Äž": "Ğ"
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

# Few-Shot Örnekler — modele beklenen JSON formatını öğretir
FEW_SHOT_EXAMPLES = """
### ÖRNEK 1
SORU: Okyanus yüzeyinde hangi organizmalar yaşar?
CEVAP:
{
  "answer": "Okyanus yüzeyinde serbest yaşayan organizmalara 'neuston' adı verilir. Bunlar arasında altın deniz yosunu Sargassum, süzgeç kabukluları, deniz salyangozları ve cnidarians bulunur. [Kaynak: wiki_394_marine_ecosystem.txt]",
  "sources": ["wiki_394_marine_ecosystem.txt"],
  "confidence": "Yüksek",
  "in_context": true
}

### ÖRNEK 2
SORU: Mercan resifleri nasıl oluşur?
CEVAP:
{
  "answer": "Mercan resifleri, mercan polipleri tarafından oluşturulur. Bu polipler, sığ tropikal sularda sert iskeletler inşa ederek zamanla büyük resif yapıları meydana getirir. [Kaynak: wiki_390_marine_coastal_ecosystem.txt]",
  "sources": ["wiki_390_marine_coastal_ecosystem.txt"],
  "confidence": "Yüksek",
  "in_context": true
}

### ÖRNEK 3
SORU: Okyanuslardaki cıva kirliliği hangi canlıları etkiler?
CEVAP:
{
  "answer": "Cıva kirliliği fitoplankton bolluğuna ve yüzey suyu sıcaklığına bağlı olarak değişir. Deniz ekosistemlerinde organik cıva türlerinin kaderi bu faktörlere göre şekillenir. [Kaynak: ocean_165_mercury_in_marine_and_oceanic_watersa_review.pdf]",
  "sources": ["ocean_165_mercury_in_marine_and_oceanic_watersa_review.pdf"],
  "confidence": "Orta",
  "in_context": true
}
"""

# Model ve Veritabanı Yükleme (Cache kullanarak hızlandırıyoruz)
@st.cache_resource(show_spinner="Embedding modeli yükleniyor (BAAI/bge-m3)...")
def load_embedding_model():
    try:
        # BGE-M3 modelini yükle
        model = SentenceTransformer("BAAI/bge-m3")
        return model
    except Exception as e:
        st.error(f"Embedding modeli yüklenirken hata oluştu: {str(e)}")
        model = SentenceTransformer("BAAI/bge-m3", device="cpu")
        return model

@st.cache_resource(show_spinner="ChromaDB Bağlantısı kuruluyor...")
def load_chroma_db(db_path):
    if not os.path.exists(db_path):
        st.warning(f"Belirtilen veritabanı klasörü bulunamadı: '{db_path}'. Lütfen zip dosyasını açtığınızdan emin olun.")
    client = chromadb.PersistentClient(path=db_path)
    
    # Colab üzerinde oluşturulan varsayılan koleksiyon adı: ocean_collection
    try:
        collection = client.get_collection(name="ocean_collection")
        return collection
    except Exception as e:
        # Koleksiyonları listele ve ilkini seç veya kullanıcıyı uyar
        cols = client.list_collections()
        if cols:
            st.info(f"Orijinal 'ocean_collection' bulunamadı, mevcut ilk koleksiyon seçiliyor: {cols[0].name}")
            return client.get_collection(name=cols[0].name)
        else:
            st.error("ChromaDB içerisinde aktif bir koleksiyon bulunamadı.")
            return None

# -------------------------------------------------------------------------
# SIDEBAR (Ayarlar ve Donanım Paneli)
# -------------------------------------------------------------------------
# NOT: 2025-12-31 sonrasındaki Streamlit sürümlerinde use_container_width yerine width="stretch" kullanılır.
st.sidebar.image(
    "https://images.unsplash.com/photo-1518156677180-95a2893f3e9f?w=300&auto=format&fit=crop", 
    caption="Tilikum Ocean AI Engine", 
    width="stretch"
)

st.sidebar.title("🛠️ Sistem Konfigürasyonu")

# Veritabanı Klasör Yolu
db_dir = st.sidebar.text_input(
    "1. ChromaDB Klasör Yolu", 
    value="./ocean_chroma_db",
    help="Google Colab'den indirdiğiniz zipten çıkan klasörün yerel yolu."
)

# Yerel LLM Sunucu Ayarları (LM Studio, Ollama, LocalAI, vLLM vb.)
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Yerel LLM (Local LLM) Ayarları")
llm_api_url = st.sidebar.text_input("Yerel API Sunucusu", value="http://127.0.0.1:1234", help="LM Studio, Ollama veya yerel OpenAI uyumlu sunucu adresi.")

# Sunucudan yüklü modelleri otomatik çekme
def get_available_models(base_url):
    try:
        resp = requests.get(f"{base_url}/v1/models", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("id") for m in data.get("data", []) if m.get("id")]
            return models
    except Exception:
        pass
    return []

available_models = get_available_models(llm_api_url)

if available_models:
    model_name = st.sidebar.selectbox(
        "Yüklü Model Seçin",
        options=available_models,
        help="Yerel sunucunuzda aktif olan modeller otomatik algılandı."
    )
else:
    model_name = st.sidebar.text_input(
        "Yerel Model Adı", 
        value="qwen2.5:3b", 
        help="Sunucunuzda yüklü olan modelin adını girin (Örn: gemma, qwen2.5:3b, llama-3.1-8b vb.)."
    )

temperature = st.sidebar.slider("Sıcaklık (Temperature)", min_value=0.0, max_value=1.0, value=0.0, step=0.1, help="Doğruluk için 0.0 önerilir.")

# Gating & Hafıza Parametreleri
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Güvenlik Kapısı & Hafıza")
distance_threshold = st.sidebar.slider(
    "Maksimum Mesafe Eşiği (Distance)", 
    min_value=0.1, 
    max_value=0.9, 
    value=0.42, 
    step=0.01,
    help="Sorgunun en yakın dökümana uzaklığı bu değerin ÜZERİNDEYSE yerel dökümanlar kullanılmaz."
)

enable_web_fallback = st.sidebar.toggle(
    "🌐 Otomatik Canlı Web Arama (Fallback)",
    value=True,
    help="Yerel okyanus arşivinde bulunamayan sorular için internette DuckDuckGo üzerinden canlı arama yapar."
)

memory_window = st.sidebar.slider(
    "🧠 Sohbet Hafızası Derinliği (Mesaj Sayısı)",
    min_value=0,
    max_value=8,
    value=4,
    step=2,
    help="Modelin hatırlayacağı geçmiş mesaj çifti sayısı (0 = Hafızasız / Bağımsız)."
)

# Okyanus Araçları Hızlı Test Paneli
st.sidebar.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
st.sidebar.subheader("🌊 Okyanus Araçları Paneli")
st.sidebar.caption("Okyanus ve derinlik araçlarını tek tıkla test edin:")

col_a, col_b = st.sidebar.columns(2)
with col_a:
    if st.sidebar.button("🌊 Akdeniz Dalga", key="btn_akdeniz"):
        st.session_state.quick_tool_prompt = "Akdeniz'de şu an dalga boyu ve deniz durumu nasıl?"
    if st.sidebar.button("🐋 Mavi Balina", key="btn_balina"):
        st.session_state.quick_tool_prompt = "Mavi Balina hangi okyanus katmanında yaşar ve özellikleri nedir?"
    if st.sidebar.button("🌡️ +2°C İklim", key="btn_iklim"):
        st.session_state.quick_tool_prompt = "Küresel sıcaklık 2 derece artarsa deniz seviyesi ne kadar yükselir?"
with col_b:
    if st.sidebar.button("🌔 Ay & Gelgit", key="btn_ay"):
        st.session_state.quick_tool_prompt = "Bugün ayın hangi evresindeyiz ve okyanus gelgit durumu nedir?"
    if st.sidebar.button("⚓ Mariana Basınç", key="btn_mariana"):
        st.session_state.quick_tool_prompt = "Mariana Çukurunda 11000 metrede basınç kaç bardır?"
    if st.sidebar.button("📚 Termohalin", key="btn_termo"):
        st.session_state.quick_tool_prompt = "Termohalin dolaşımı nedir ve neden önemlidir?"
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# Sohbet Sıfırlama ve Donanım Durumu
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Sohbet Geçmişini Sıfırla"):
    st.session_state.messages = []
    st.session_state.ocean_active_widgets = {}
    st.rerun()

if st.sidebar.button("🔄 Önbelleği Temizle"):
    st.cache_resource.clear()
    st.session_state.messages = []
    st.session_state.ocean_active_widgets = {}
    st.success("Önbellek ve sohbet sıfırlandı!")
    st.rerun()

st.sidebar.info("💡 **İpucu:** LM Studio'da herhangi bir modeli (Gemma, Llama, Mistral, Qwen vb.) yükleyip Local Server'ı başlatmanız yeterlidir.")

# Modeli ve Veritabanını Başlat
embed_model = load_embedding_model()
collection = load_chroma_db(db_dir)

# -------------------------------------------------------------------------
# SOHBET ARAYÜZÜ VE HİBRİT AJAN DÖNGÜSÜ
# -------------------------------------------------------------------------

# Chat geçmişini ekranda göster
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Eğer bu mesaja ait bir okyanus aracı kartı varsa render et
        if idx in st.session_state.ocean_active_widgets:
            w_info = st.session_state.ocean_active_widgets[idx]
            w_html = w_info.get("html", "")
            w_height = w_info.get("height", 270)
            if w_html:
                components.html(w_html, height=w_height)
                
        if "web_sources" in message and message["web_sources"]:
            with st.expander("🌐 Canlı Web Kaynakları"):
                for src in message["web_sources"]:
                    st.markdown(f"- 🔗 [{src.get('title', 'Web Kaynağı')}]({src.get('href', '#')})")
        if "debug_info" in message:
            with st.expander("🔍 Arama Motoru Detayları (Metadata & Scores)"):
                st.json(message["debug_info"])

# Hızlı araç tetikleyicisi kontrolü
user_prompt_input = st.chat_input("Okyanuslar, deniz canlıları veya dalga durumu hakkında bir soru sorun...")
if "quick_tool_prompt" in st.session_state and st.session_state.quick_tool_prompt:
    user_prompt_input = st.session_state.quick_tool_prompt
    st.session_state.quick_tool_prompt = None

# Kullanıcı girişi
if prompt := user_prompt_input:
    
    # 1. Kullanıcının sorusunu ekrana yazdır
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Sistem yanıtı süreci
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        msg_idx = len(st.session_state.messages)
        
        # [AŞAMA 1] ÖZEL OKYANUS ARACI TESPİTİ (INTENT ROUTER)
        tool_result = detect_and_execute_ocean_tool(prompt)
        
        if tool_result and tool_result.get("status") == "success":
            # 🌊 Özel Okyanus Aracı Devrede!
            w_html = tool_result.get("widget_html")
            w_height = tool_result.get("height", 270)
            sci_msg = tool_result.get("message", "")
            
            st.markdown(
                "<div class='tool-mode'>🌊 <b>Özel Okyanus & Bilim Aracı Devrede:</b> Telemetri ve interaktif kart üretildi.</div>",
                unsafe_allow_html=True
            )
            
            if w_html:
                components.html(w_html, height=w_height)
                st.session_state.ocean_active_widgets[msg_idx] = {"html": w_html, "height": w_height}
                
            # Modele bilimsel veri bağlamını aktarıp uzman Türkçe açıklama ürettir
            system_prompt = (
                "Sen Tilikum AI Okyanus & Deniz Bilimleri Uzmanısın. "
                "Sana sağlanan bilimsel okyanus aracı verilerini kullanarak kullanıcıya doğrudan, net, kapsamlı ve akıcı bir Türkçe açıklama yap."
            )
            user_prompt = f"BİLİMSEL OKYANUS ARACI VERİLERİ:\n{sci_msg}\n\nKULLANICI SORUSU: {prompt}\n\nYukarıdaki verilere dayanarak detaylı ve profesyonel Türkçe yanıt üret:"
            
            try:
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                with requests.post(
                    f"{llm_api_url}/v1/chat/completions",
                    json={"model": model_name, "messages": llm_messages, "temperature": 0.1, "max_tokens": 1000, "stream": True},
                    stream=True, timeout=120
                ) as response:
                    if response.status_code == 200:
                        raw_stream = ""
                        for line in response.iter_lines(decode_unicode=True):
                            if line and line.startswith("data: "):
                                d_str = line[6:].strip()
                                if d_str == "[DONE]": break
                                try:
                                    ch = json.loads(d_str).get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if ch:
                                        raw_stream += ch
                                        display = fix_turkish_encoding(re.sub(r'<think>.*?</think>', '', raw_stream, flags=re.DOTALL))
                                        response_placeholder.markdown(display + "▌")
                                except Exception: pass
                        
                        final_text = fix_turkish_encoding(re.sub(r'<think>.*?</think>', '', raw_stream, flags=re.DOTALL).strip())
                        if not final_text: final_text = sci_msg
                        response_placeholder.markdown(final_text)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": final_text
                        })
                    else:
                        response_placeholder.markdown(sci_msg)
                        st.session_state.messages.append({"role": "assistant", "content": sci_msg})
            except Exception:
                response_placeholder.markdown(sci_msg)
                st.session_state.messages.append({"role": "assistant", "content": sci_msg})
                
        else:
            # [AŞAMA 2] STANDART RAG & WEB FALLBACK MİMARİSİ
            if collection is None:
                err_msg = "❌ Hata: ChromaDB koleksiyonu yüklenemedi. Sidebar'daki dosya yolunu kontrol edin."
                response_placeholder.markdown(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
            else:
                # 1. KATMAN: SORGU BAĞLAMLAŞTIRMA (Hafızadan Arama Sorgusu Çıkarma)
                search_query = prompt
                if memory_window > 0 and len(st.session_state.messages) > 1:
                    with st.spinner("Sorgu geçmiş konuşmalarla bağlamlaştırılıyor..."):
                        search_query = contextualize_query(prompt, st.session_state.messages[:-1], llm_api_url, model_name)
                        if search_query != prompt:
                            st.caption(f"🧠 **Bağlamsal Optimize Edilmiş Arama Sorgusu:** *\"{search_query}\"*")

                with st.spinner("Anlamsal arama yapılıyor ve güvenlik kapısı sorgulanıyor..."):
                    query_vector = embed_model.encode(search_query, normalize_embeddings=True).tolist()
                    results = collection.query(
                        query_embeddings=[query_vector],
                        n_results=4
                    )
                    
                distances = results['distances'][0] if 'distances' in results and results['distances'] else []
                documents = results['documents'][0] if 'documents' in results and results['documents'] else []
                metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else []
                
                closest_dist_str = f"{distances[0]:.4f}" if distances else "N/A"
                
                # GÜVENLİK KAPISI (GATING) KONTROLÜ
                gating_failed = False
                if not distances or distances[0] > distance_threshold:
                    gating_failed = True
                    
                current_mode = "local"
                context_text = ""
                web_sources_list = []
                
                # HİBRİT KARAR MEKANİZMASI
                if gating_failed:
                    if enable_web_fallback:
                        # 🌐 WEB FALLBACK MODU DEVREYE GİRİYOR
                        current_mode = "web"
                        st.markdown(
                            f"<div class='web-mode'>🌐 <b>Otonom Web Arama Modu:</b> Soru yerel arşivde bulunamadı (Mesafe: {closest_dist_str} > {distance_threshold}). İnternette canlı aranıyor...</div>", 
                            unsafe_allow_html=True
                        )
                        with st.spinner("DuckDuckGo ile internet taranıyor..."):
                            web_results = search_web_duckduckgo(search_query, max_results=4)
                        
                        if web_results:
                            web_contexts = []
                            for r in web_results:
                                title = r.get("title", "Web Sayfası")
                                url = r.get("href", "")
                                snippet = r.get("body", "")
                                web_contexts.append(f"[Kaynak: {title} | Link: {url}] {snippet}")
                                web_sources_list.append({"title": title, "href": url})
                            context_text = "\n\n".join(web_contexts)
                            
                            system_prompt = (
                                "Sen internetten gelen güncel web arama sonuçlarını kullanarak doğrudan Türkçe cevap veren bir uzmansın.\n"
                                "KURALLAR:\n"
                                "1. Sadece sana verilen 'İNTERNET ARAMA SONUÇLARI' içindeki bilgileri kullan.\n"
                                "2. Cümlelerinin sonunda [Kaynak: Web Sayfası Başlığı] etiketini belirt.\n"
                                "3. Doğrudan ve net bir Türkçe ile özetle."
                            )
                            user_prompt = f"İNTERNET ARAMA SONUÇLARI:\n{context_text}\n\nSORU: {prompt}\n\nYukarıdaki web sonuçlarına dayanarak soruyu Türkçe olarak cevapla:"
                        else:
                            gating_failed = True
                            context_text = ""
                    else:
                        context_text = ""

                if not gating_failed and current_mode == "local":
                    # 📂 YEREL RAG MODU
                    st.markdown(
                        f"<div class='gating-passed'>📂 <b>Yerel RAG Modu:</b> En yakın döküman mesafesi ({closest_dist_str}) belirlenen sınırın altında. Bilgi yerel okyanus arşivinden çekiliyor.</div>", 
                        unsafe_allow_html=True
                    )
                    valid_contexts = []
                    for doc, dist, meta in zip(documents, distances, metadatas):
                        valid_contexts.append(f"[Kaynak: {meta.get('source', 'Okyanus Belgesi')}] {doc}")
                    context_text = "\n\n".join(valid_contexts)
                    
                    system_prompt = (
                        "Sen yalnızca sana verilen okyanus dökümanlarını okuyarak doğrudan Türkçe cevap veren bir uzmansın.\n"
                        "KURALLAR:\n"
                        "1. Sadece sana verilen 'BAĞLAM' içindeki bilgileri kullan.\n"
                        "2. Cümlelerinin sonunda mutlaka [Kaynak: dosya_adi] etiketini belirt.\n"
                        "3. Doğrudan ve net bir Türkçe ile cevap ver."
                    )
                    user_prompt = f"BAĞLAM:\n{context_text}\n\nSORU: {prompt}\n\nYukarıdaki bağlama dayanarak soruyu Türkçe olarak cevapla:"

                # Debug Verisini Hazırla
                debug_data = {
                    "Orijinal Soru": prompt,
                    "Bağlamsal Arama Sorgusu": search_query,
                    "Çalışma Modu": "🌐 Canlı Web Arama" if current_mode == "web" else "📂 Yerel Okyanus Veritabanı",
                    "En Yakın Döküman Mesafesi": distances[0] if distances else "Bulunamadı",
                    "Eşik Değeri Limit": distance_threshold,
                    "Yerel Sonuçlar": [
                        {"Metin": doc[:150] + "...", "Mesafe": dist, "Kaynak": meta.get("source", "Bilinmiyor")}
                        for doc, dist, meta in zip(documents, distances, metadatas)
                    ],
                    "Web Kaynakları": web_sources_list if current_mode == "web" else []
                }

                # Eğer her iki modda da bağlam yoksa (güvenlik reddi)
                if not context_text.strip():
                    refusal_msg = "🤖 **Asistan:** Bilmiyorum, bu bilgi ne yerel okyanus verilerinde ne de internet aramasında bulunamadı."
                    st.markdown(
                        f"<div class='gating-failed'>🛡️ <b>Güvenlik Kapısı Tetiklendi:</b> En yakın döküman mesafesi ({closest_dist_str}) belirlenen sınırı ({distance_threshold}) aştı. Yerel LLM çalıştırılmadan yanıt engellendi.</div>", 
                        unsafe_allow_html=True
                    )
                    response_placeholder.markdown(refusal_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": refusal_msg,
                        "debug_info": debug_data
                    })
                    with st.expander("🔍 Arama Motoru Detayları (Metadata & Scores)"):
                        st.json(debug_data)
                else:
                    # LLM ÇAĞRISI (STREAMING - CANLI AKIŞ + 2. KATMAN: KAYAN PENCERE BELLEĞİ)
                    try:
                        # 2. KATMAN: Kayan Pencere Sohbet Geçmişi (Sliding Window Memory)
                        llm_messages = [{"role": "system", "content": system_prompt}]
                        
                        if memory_window > 0 and len(st.session_state.messages) > 1:
                            history_slice = st.session_state.messages[-(memory_window + 1):-1]
                            for msg in history_slice:
                                llm_messages.append({
                                    "role": msg["role"],
                                    "content": msg["content"]
                                })
                        
                        llm_messages.append({"role": "user", "content": user_prompt})

                        payload = {
                            "model": model_name,
                            "messages": llm_messages,
                            "temperature": 0.0,
                            "max_tokens": 1500,
                            "stream": True
                        }

                        with requests.post(
                            f"{llm_api_url}/v1/chat/completions",
                            json=payload,
                            stream=True,
                            timeout=300
                        ) as response:
                            if response.status_code == 200:
                                raw_stream_text = ""
                                
                                for line in response.iter_lines(decode_unicode=True):
                                    if not line:
                                        continue
                                    
                                    if line.startswith("data: "):
                                        data_str = line[6:].strip()
                                        if data_str == "[DONE]":
                                            break
                                        
                                        try:
                                            chunk_json = json.loads(data_str)
                                            delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                                            content_chunk = delta.get("content", "")
                                            
                                            if content_chunk:
                                                raw_stream_text += content_chunk
                                                display_text = re.sub(r'<think>.*?</think>', '', raw_stream_text, flags=re.DOTALL)
                                                display_text = re.sub(r'<think>.*', '', display_text, flags=re.DOTALL)
                                                display_text = fix_turkish_encoding(display_text)
                                                response_placeholder.markdown(display_text + "▌")
                                        except Exception:
                                            continue

                                final_clean_text = raw_stream_text
                                final_clean_text = re.sub(r'<think>.*?</think>', '', final_clean_text, flags=re.DOTALL).strip()
                                final_clean_text = re.sub(r'<think>.*', '', final_clean_text, flags=re.DOTALL).strip()
                                final_clean_text = fix_turkish_encoding(final_clean_text)

                                if not final_clean_text:
                                    final_clean_text = "❌ Model boş yanıt üretti. Lütfen tekrar deneyin."

                                response_placeholder.markdown(final_clean_text)

                                # Pydantic Doğrulama & Rozetler
                                detected_sources = []
                                src_matches = re.findall(r'\[Kaynak:\s*([^\]]+)\]', final_clean_text)
                                if src_matches:
                                    detected_sources = list(set([s.strip() for s in src_matches]))

                                try:
                                    validated_pydantic = RAGResponse(
                                        answer=final_clean_text,
                                        sources=detected_sources,
                                        confidence="Yüksek" if current_mode == "local" else "Orta",
                                        in_context=True,
                                        mode=current_mode
                                    )
                                    
                                    col1, col2 = st.columns([1, 2])
                                    with col1:
                                        if current_mode == "local":
                                            st.caption("🟢 Mod: **📂 Yerel Okyanus Arşivi**")
                                        else:
                                            st.caption("🌐 Mod: **Canlı Web Arama**")
                                    with col2:
                                        if validated_pydantic.sources:
                                            st.caption("📄 " + " · ".join(f"`{s}`" for s in validated_pydantic.sources))
                                except Exception:
                                    pass

                                # Web Modundaysa Canlı Tıklanabilir Bağlantıları Göster
                                if current_mode == "web" and web_sources_list:
                                    with st.expander("🌐 Canlı Web Kaynakları (Tıklanabilir Bağlantılar)", expanded=True):
                                        for src in web_sources_list:
                                            st.markdown(f"- 🔗 [{src.get('title', 'Web Sayfası')}]({src.get('href', '#')})")

                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": final_clean_text,
                                    "web_sources": web_sources_list if current_mode == "web" else [],
                                    "debug_info": debug_data
                                })

                                with st.expander("🔍 Arama Motoru Detayları (Metadata & Scores)"):
                                    st.json(debug_data)

                            else:
                                st.error(f"Yerel LLM Sunucu Hatası: {response.status_code} - {response.text}")
                                st.info("Lütfen yerel sunucunuzun açık olduğundan emin olun.")

                    except requests.exceptions.ReadTimeout:
                        st.error("⏱️ Hata: Model yanıt süresi aşıldı (300 sn)!")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Hata: Yerel LLM sunucusuna bağlanılamadı!")
                        st.info(f"LM Studio / Yerel sunucunuzu açın, model yükleyin ve sunucuyu başlatın. API Adresi: {llm_api_url}")
                    except Exception as e:
                        st.error(f"Beklenmeyen bir hata oluştu: {str(e)}")


