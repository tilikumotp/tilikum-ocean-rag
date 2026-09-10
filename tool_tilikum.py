import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import re
import os
import platform
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

# Sayfa Yapılandırması ve Premium Tema Ayarları
st.set_page_config(
    page_title="Tilikum AI: Executive Widget Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium, Profesyonel ve Minimalist CSS Arayüz Tasarımı
st.markdown("""
<style>
    /* Global Streamlit UI Overrides */
    .stApp {
        background-color: #030712;
    }
    
    /* Premium Header and Card Design */
    .main-header {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #f8fafc 30%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 28px;
        font-weight: 400;
        letter-spacing: -0.01em;
    }
    
    /* Premium Glassmorphic Widget Container */
    .widget-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 2px;
        margin-top: 15px;
        margin-bottom: 15px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), 
                    inset 0 1px 1px rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
    }
    
    /* Elegant Developer Terminal Log */
    .system-log-container {
        background: #090d16;
        border-left: 3px solid #10b981;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .system-log-title {
        color: #10b981;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 4px;
    }
    .system-log-content {
        color: #e2e8f0;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        line-height: 1.5;
    }
    
    /* Sidebar styling refinements */
    .sidebar-section {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Başlık Bölümü
st.markdown("<div class='main-header'>💼 Tilikum AI: Executive Widget Agent</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Minimalist, Profesyonel Tasarımlı Otonom Arayüz, Canlı Widget ve Web Ajanı (v6)</div>", unsafe_allow_html=True)

# =========================================================================
# 1. PREMIUM WIDGET ŞABLONLARI VE GERÇEK PYTHON FONKSİYONLARI (ALTIN 6'LI)
# =========================================================================

# -------------------------------------------------------------------------
# [WIDGET 1] DÜNYA VE YEREL SAAT WIDGET'I (World & Local Chronograph Clock)
# -------------------------------------------------------------------------
CITY_TIMEZONE_MAP = {
    'tokyo': ('Asia/Tokyo', 'Tokyo', 'Japonya'),
    'japonya': ('Asia/Tokyo', 'Tokyo', 'Japonya'),
    'istanbul': ('Europe/Istanbul', 'İstanbul', 'Türkiye'),
    'ankara': ('Europe/Istanbul', 'Ankara', 'Türkiye'),
    'izmir': ('Europe/Istanbul', 'İzmir', 'Türkiye'),
    'turkiye': ('Europe/Istanbul', 'İstanbul', 'Türkiye'),
    'türkiye': ('Europe/Istanbul', 'İstanbul', 'Türkiye'),
    'londra': ('Europe/London', 'Londra', 'Birleşik Krallık'),
    'london': ('Europe/London', 'Londra', 'Birleşik Krallık'),
    'ingiltere': ('Europe/London', 'Londra', 'Birleşik Krallık'),
    'uk': ('Europe/London', 'Londra', 'Birleşik Krallık'),
    'new york': ('America/New_York', 'New York', 'ABD'),
    'newyork': ('America/New_York', 'New York', 'ABD'),
    'amerika': ('America/New_York', 'New York', 'ABD'),
    'abd': ('America/New_York', 'New York', 'ABD'),
    'usa': ('America/New_York', 'New York', 'ABD'),
    'paris': ('Europe/Paris', 'Paris', 'Fransa'),
    'fransa': ('Europe/Paris', 'Paris', 'Fransa'),
    'berlin': ('Europe/Berlin', 'Berlin', 'Almanya'),
    'almanya': ('Europe/Berlin', 'Berlin', 'Almanya'),
    'roma': ('Europe/Rome', 'Roma', 'İtalya'),
    'rome': ('Europe/Rome', 'Roma', 'İtalya'),
    'italya': ('Europe/Rome', 'Roma', 'İtalya'),
    'madrid': ('Europe/Madrid', 'Madrid', 'İspanya'),
    'ispanya': ('Europe/Madrid', 'Madrid', 'İspanya'),
    'dubai': ('Asia/Dubai', 'Dubai', 'BAE'),
    'bae': ('Asia/Dubai', 'Dubai', 'BAE'),
    'moskova': ('Europe/Moscow', 'Moskova', 'Rusya'),
    'moscow': ('Europe/Moscow', 'Moskova', 'Rusya'),
    'rusya': ('Europe/Moscow', 'Moskova', 'Rusya'),
    'pekin': ('Asia/Shanghai', 'Pekin', 'Çin'),
    'beijing': ('Asia/Shanghai', 'Pekin', 'Çin'),
    'cin': ('Asia/Shanghai', 'Pekin', 'Çin'),
    'çin': ('Asia/Shanghai', 'Pekin', 'Çin'),
    'singapur': ('Asia/Singapore', 'Singapur', 'Singapur'),
    'singapore': ('Asia/Singapore', 'Singapur', 'Singapur'),
    'sydney': ('Australia/Sydney', 'Sidney', 'Avustralya'),
    'sidney': ('Australia/Sydney', 'Sidney', 'Avustralya'),
    'avustralya': ('Australia/Sydney', 'Sidney', 'Avustralya'),
    'los angeles': ('America/Los_Angeles', 'Los Angeles', 'ABD'),
    'chicago': ('America/Chicago', 'Chicago', 'ABD'),
    'toronto': ('America/Toronto', 'Toronto', 'Kanada'),
    'seul': ('Asia/Seoul', 'Seul', 'Güney Kore'),
    'seoul': ('Asia/Seoul', 'Seul', 'Güney Kore'),
    'kore': ('Asia/Seoul', 'Seul', 'Güney Kore'),
    'baku': ('Asia/Baku', 'Bakü', 'Azerbaycan'),
    'bakü': ('Asia/Baku', 'Bakü', 'Azerbaycan'),
    'azerbaycan': ('Asia/Baku', 'Bakü', 'Azerbaycan'),
    'kahire': ('Africa/Cairo', 'Kahire', 'Mısır'),
    'cairo': ('Africa/Cairo', 'Kahire', 'Mısır'),
    'misir': ('Africa/Cairo', 'Kahire', 'Mısır'),
    'mısır': ('Africa/Cairo', 'Kahire', 'Mısır'),
    'riyad': ('Asia/Riyadh', 'Riyad', 'Suudi Arabistan'),
    'riyadh': ('Asia/Riyadh', 'Riyad', 'Suudi Arabistan'),
    'amsterdam': ('Europe/Amsterdam', 'Amsterdam', 'Hollanda'),
    'hollanda': ('Europe/Amsterdam', 'Amsterdam', 'Hollanda'),
    'brüksel': ('Europe/Brussels', 'Brüksel', 'Belçika'),
    'brussels': ('Europe/Brussels', 'Brüksel', 'Belçika'),
    'atina': ('Europe/Athens', 'Atina', 'Yunanistan'),
    'athens': ('Europe/Athens', 'Atina', 'Yunanistan'),
    'viyana': ('Europe/Vienna', 'Viyana', 'Avusturya'),
    'vienna': ('Europe/Vienna', 'Viyana', 'Avusturya'),
    'zürich': ('Europe/Zurich', 'Zürih', 'İsviçre'),
    'zurih': ('Europe/Zurich', 'Zürih', 'İsviçre'),
    'isvicre': ('Europe/Zurich', 'Zürih', 'İsviçre'),
    'utc': ('UTC', 'UTC (Evrensel Zaman)', 'Dünya'),
    'gmt': ('GMT', 'GMT', 'Dünya')
}

def resolve_timezone_and_city(city_or_timezone: str):
    """Girilen şehir veya zaman dilimini IANA standart timezone ve başlığına dönüştürür."""
    if not city_or_timezone:
        return ('Europe/Istanbul', 'İstanbul (Yerel)', 'Türkiye')
    
    clean = str(city_or_timezone).lower().strip()
    
    for k, v in CITY_TIMEZONE_MAP.items():
        if k in clean:
            return v
            
    # IANA doğrudan zaman dilimi kontrolü (örn: 'Asia/Tokyo')
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(city_or_timezone.strip())
        name = city_or_timezone.split('/')[-1].replace('_', ' ')
        return (city_or_timezone.strip(), name, '')
    except Exception:
        pass
        
    return ('Europe/Istanbul', city_or_timezone.title(), '')

def create_js_clock_widget(city_or_timezone: str = "İstanbul", theme: str = "dark"):
    """
    Dünya üzerindeki herhangi bir şehrin (Tokyo, Londra, New York, vb.) veya yerel bölgenin
    gerçek canlı akıcı saatini hesaplar ve lüks JS saat widgetı (HTML/CSS/JS) olarak oluşturur.
    """
    iana_tz, display_city, country = resolve_timezone_and_city(city_or_timezone)
    
    # Python tarafında kesin ve anlık zaman hesaplaması
    try:
        from zoneinfo import ZoneInfo
        tz_obj = ZoneInfo(iana_tz)
        now_dt = datetime.now(tz_obj)
    except Exception:
        now_dt = datetime.now()
        
    time_str = now_dt.strftime("%H:%M:%S")
    date_str = now_dt.strftime("%d %B %Y")
    offset_raw = now_dt.strftime("%z")
    offset_formatted = f"UTC{offset_raw[:3]}:{offset_raw[3:]}" if len(offset_raw) == 5 else "UTC"

    bg_gradient = "linear-gradient(135deg, #0f172a 0%, #020617 100%)" if theme == "dark" else "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)"
    text_color = "#f8fafc" if theme == "dark" else "#0f172a"
    sub_text_color = "#64748b" if theme == "dark" else "#475569"
    border_color = "rgba(255, 255, 255, 0.08)" if theme == "dark" else "rgba(15, 23, 42, 0.08)"
    accent_gold = "#d4af37"
    
    country_badge = f" • {country}" if country else ""
    
    widget_html = f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0;
            padding: 4px;
            background: transparent;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
        }}
    </style>
    <div style="background:{bg_gradient};color:{text_color};border:1px solid {border_color};border-radius:16px;padding:20px 24px;width:100%;max-width:380px;text-align:center;box-shadow:0 12px 30px rgba(0,0,0,0.35);position:relative;overflow:hidden;">
        <div style="position:absolute;top:-30px;right:-30px;width:100px;height:100px;background:radial-gradient(circle,rgba(212,175,55,0.12) 0%,transparent 70%);pointer-events:none;"></div>
        
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:0.75rem;font-weight:700;color:{accent_gold};text-transform:uppercase;letter-spacing:0.2em;">Tilikum Chronograph</div>
            <span style="font-size:0.65rem;background:rgba(212,175,55,0.15);color:{accent_gold};padding:2px 8px;border-radius:10px;font-weight:600;">{offset_formatted}</span>
        </div>
        
        <div style="font-size:1rem;font-weight:600;color:#f8fafc;margin-bottom:4px;">📍 {display_city}{country_badge}</div>
        
        <div id="clock-display" style="font-size:3.2rem;font-weight:300;font-family:'Inter',monospace;letter-spacing:-0.03em;line-height:1;margin:6px 0 8px 0;color:#f8fafc;">{time_str}</div>
        
        <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:6px;">
            <span style="display:inline-block;width:6px;height:6px;background-color:#10b981;border-radius:50%;box-shadow:0 0 6px #10b981;"></span>
            <div id="date-display" style="font-size:0.85rem;font-weight:500;color:{sub_text_color};text-transform:capitalize;">{date_str}</div>
        </div>
    </div>
    <script>
        const tz = "{iana_tz}";
        function updateClock() {{
            const now = new Date();
            try {{
                const timeStr = now.toLocaleTimeString('tr-TR', {{ timeZone: tz, hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }});
                const dateStr = now.toLocaleDateString('tr-TR', {{ timeZone: tz, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }});
                document.getElementById('clock-display').textContent = timeStr;
                document.getElementById('date-display').textContent = dateStr;
            }} catch(e) {{
                document.getElementById('clock-display').textContent = now.toLocaleTimeString('tr-TR');
            }}
        }}
        setInterval(updateClock, 1000);
        updateClock();
    </script>
    """
    
    summary_text = (
        f"{display_city} ({country_badge.strip(' •')}, {iana_tz}, {offset_formatted}) için canlı saat widgetı arayüzde oluşturuldu. "
        f"Şu an {display_city}'da gerçek canlı saat: {time_str}, tarih: {date_str}."
    )
    return {
        "status": "success",
        "widget_html": widget_html,
        "message": summary_text,
        "city": display_city,
        "timezone": iana_tz,
        "current_time": time_str
    }


# -------------------------------------------------------------------------
# [WIDGET 2] GERİ SAYIM SAYACI & POMODORO WIDGET'I (Countdown Timer)
# -------------------------------------------------------------------------
def create_countdown_timer_widget(minutes: int = 25, label: str = "Pomodoro Odaklanma"):
    """Ekranda canlı geri sayan, Başlat/Duraklat/Sıfırla butonlarına sahip interaktif Pomodoro kartı."""
    total_seconds = max(1, int(minutes)) * 60
    accent_emerald = "#10b981"
    accent_gold = "#d4af37"
    
    return f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0;
            padding: 4px;
            background: transparent;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
        }}
    </style>
    <div style="background:linear-gradient(135deg, #0f172a 0%, #020617 100%);color:#f8fafc;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:18px 24px;width:100%;max-width:380px;text-align:center;box-shadow:0 12px 30px rgba(0,0,0,0.4);position:relative;overflow:hidden;">
        <div style="font-size:0.75rem;font-weight:700;color:{accent_emerald};text-transform:uppercase;letter-spacing:0.2em;margin-bottom:6px;">⏱️ {label}</div>
        <div id="timer-display" style="font-size:3.2rem;font-weight:300;font-family:'Inter',monospace;letter-spacing:-0.02em;line-height:1;margin:6px 0;color:#f8fafc;">{int(minutes):02d}:00</div>
        
        <div style="width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;margin-bottom:12px;overflow:hidden;">
            <div id="progress-bar" style="width:100%;height:100%;background:linear-gradient(90deg, {accent_emerald}, {accent_gold});transition:width 1s linear;"></div>
        </div>

        <div style="display:flex;justify-content:center;gap:10px;margin-bottom:6px;">
            <button id="btn-toggle" onclick="toggleTimer()" style="background:#1e293b;border:1px solid rgba(255,255,255,0.15);color:#f8fafc;padding:6px 16px;border-radius:8px;font-size:0.85rem;cursor:pointer;font-weight:600;transition:all 0.2s;">⏸ Duraklat</button>
            <button id="btn-reset" onclick="resetTimer()" style="background:#0f172a;border:1px solid rgba(255,255,255,0.1);color:#94a3b8;padding:6px 16px;border-radius:8px;font-size:0.85rem;cursor:pointer;transition:all 0.2s;">↺ Sıfırla</button>
        </div>
        <div id="timer-status" style="font-size:0.75rem;color:#64748b;">Sayaç aktif olarak geri sayıyor...</div>
    </div>
    <script>
        let total = {total_seconds};
        let remaining = total;
        let isRunning = true;
        let timerInterval = null;

        function updateDisplay() {{
            const m = Math.floor(remaining / 60);
            const s = remaining % 60;
            document.getElementById('timer-display').textContent = String(m).padStart(2, '0') + ":" + String(s).padStart(2, '0');
            const pct = (remaining / total) * 100;
            document.getElementById('progress-bar').style.width = pct + "%";
        }}

        function tick() {{
            if (isRunning && remaining > 0) {{
                remaining--;
                updateDisplay();
                if (remaining === 0) {{
                    clearInterval(timerInterval);
                    document.getElementById('timer-status').textContent = "🔔 Süre Doldu! Tebrikler.";
                    document.getElementById('timer-status').style.color = "#10b981";
                    playBeep();
                }}
            }}
        }}

        function toggleTimer() {{
            isRunning = !isRunning;
            const btn = document.getElementById('btn-toggle');
            const status = document.getElementById('timer-status');
            if (isRunning) {{
                btn.textContent = "⏸ Duraklat";
                status.textContent = "Sayaç aktif...";
            }} else {{
                btn.textContent = "▶ Devam Et";
                status.textContent = "Sayaç duraklatıldı.";
            }}
        }}

        function resetTimer() {{
            remaining = total;
            isRunning = true;
            document.getElementById('btn-toggle').textContent = "⏸ Duraklat";
            document.getElementById('timer-status').textContent = "Sayaç sıfırlandı ve başlatıldı.";
            document.getElementById('timer-status').style.color = "#64748b";
            updateDisplay();
        }}

        function playBeep() {{
            try {{
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.5);
            }} catch(e) {{}}
        }}

        timerInterval = setInterval(tick, 1000);
        updateDisplay();
    </script>
    """

# -------------------------------------------------------------------------
# [WIDGET 3] İNTERAKTİF HESAP MAKİNESİ (Interactive JS Calculator)
# -------------------------------------------------------------------------
def create_calculator_widget(initial_expression: str = ""):
    """Kullanıcının ekranda tıklayarak veya tuşlayarak anında hesap yapabileceği lüks hesap makinesi."""
    init_val = str(initial_expression).replace('"', '').strip()
    return f"""
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{
            margin: 0;
            padding: 4px;
            background: transparent;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
        }}
    </style>
    <div style="background:linear-gradient(135deg, #0f172a 0%, #020617 100%);color:#f8fafc;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:16px;width:100%;max-width:320px;box-shadow:0 15px 35px rgba(0,0,0,0.5);">
        <div style="font-size:0.7rem;font-weight:700;color:#d4af37;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;text-align:center;">🧮 Tilikum Calculator</div>
        <div id="calc-screen" style="background:#090d16;border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 12px;text-align:right;font-size:1.6rem;font-family:'JetBrains Mono',monospace;color:#f8fafc;min-height:50px;overflow-x:auto;margin-bottom:10px;box-shadow:inset 0 2px 4px rgba(0,0,0,0.5);">{init_val if init_val else '0'}</div>
        
        <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:8px;">
            <button onclick="calcClear()" style="background:#334155;color:#fca5a5;border:none;border-radius:8px;padding:12px;font-size:1rem;font-weight:700;cursor:pointer;">C</button>
            <button onclick="calcBack()" style="background:#334155;color:#e2e8f0;border:none;border-radius:8px;padding:12px;font-size:1rem;cursor:pointer;">⌫</button>
            <button onclick="calcInput('%')" style="background:#1e293b;color:#38bdf8;border:none;border-radius:8px;padding:12px;font-size:1rem;cursor:pointer;">%</button>
            <button onclick="calcInput('/')" style="background:#1e293b;color:#38bdf8;border:none;border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">÷</button>
            
            <button onclick="calcInput('7')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">7</button>
            <button onclick="calcInput('8')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">8</button>
            <button onclick="calcInput('9')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">9</button>
            <button onclick="calcInput('*')" style="background:#1e293b;color:#38bdf8;border:none;border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">×</button>
            
            <button onclick="calcInput('4')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">4</button>
            <button onclick="calcInput('5')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">5</button>
            <button onclick="calcInput('6')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">6</button>
            <button onclick="calcInput('-')" style="background:#1e293b;color:#38bdf8;border:none;border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">-</button>
            
            <button onclick="calcInput('1')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">1</button>
            <button onclick="calcInput('2')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">2</button>
            <button onclick="calcInput('3')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">3</button>
            <button onclick="calcInput('+')" style="background:#1e293b;color:#38bdf8;border:none;border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">+</button>
            
            <button onclick="calcInput('0')" style="grid-column:span 2;background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">0</button>
            <button onclick="calcInput('.')" style="background:#0f172a;color:#f8fafc;border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:12px;font-size:1.1rem;cursor:pointer;">.</button>
            <button onclick="calcEval()" style="background:#10b981;color:#022c22;border:none;border-radius:8px;padding:12px;font-size:1.2rem;font-weight:700;cursor:pointer;">=</button>
        </div>
    </div>
    <script>
        let currentExpr = "{init_val}";
        function renderScreen() {{
            document.getElementById('calc-screen').textContent = currentExpr.length ? currentExpr : '0';
        }}
        function calcInput(ch) {{
            if (currentExpr === '0' && ch !== '.') currentExpr = '';
            currentExpr += ch;
            renderScreen();
        }}
        function calcClear() {{
            currentExpr = '';
            renderScreen();
        }}
        function calcBack() {{
            currentExpr = currentExpr.slice(0, -1);
            renderScreen();
        }}
        function calcEval() {{
            try {{
                const clean = currentExpr.replace(/×/g, '*').replace(/÷/g, '/');
                const res = Function('"use strict"; return (' + clean + ')')();
                currentExpr = String(Number(res.toFixed(6)));
                renderScreen();
            }} catch(e) {{
                document.getElementById('calc-screen').textContent = 'Hata';
                currentExpr = '';
            }}
        }}
    </script>
    """

# -------------------------------------------------------------------------
# [WIDGET 4] CANLI HAVA DURUMU & İKLİM KARTI (Live Weather & Forecast)
# -------------------------------------------------------------------------
def get_weather_forecast(city: str = "İstanbul"):
    """Open-Meteo API ile şehir bazlı gerçek zamanlı hava durumu verisi ve cam efektli kart üretir."""
    try:
        # 1. Şehir Koordinatlarını Bul
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=tr&format=json"
        geo_resp = requests.get(geo_url, timeout=4).json()
        
        if not geo_resp.get("results"):
            return {
                "status": "error",
                "message": f"'{city}' şehri için hava durumu konumu bulunamadı.",
                "widget_html": None
            }
            
        location = geo_resp["results"][0]
        city_name = location.get("name", city)
        country = location.get("country", "")
        lat = location["latitude"]
        lon = location["longitude"]
        
        # 2. Hava Durumunu Çek
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m&timezone=auto"
        w_data = requests.get(weather_url, timeout=4).json()
        current = w_data.get("current", {})
        
        temp = current.get("temperature_2m", "--")
        feels_like = current.get("apparent_temperature", "--")
        humidity = current.get("relative_humidity_2m", "--")
        wind = current.get("wind_speed_10m", "--")
        w_code = current.get("weather_code", 0)
        
        weather_conditions = {
            0: ("☀️", "Açık ve Güneşli"),
            1: ("🌤️", "Çoğunlukla Açık"),
            2: ("⛅", "Parçalı Bulutlu"),
            3: ("☁️", "Kapalı ve Bulutlu"),
            45: ("🌫️", "Sisli"),
            48: ("🌫️", "Kırağılı Sis"),
            51: ("🌦️", "Hafif Çisenti"),
            53: ("🌦️", "Çisenti"),
            55: ("🌧️", "Yoğun Çisenti"),
            61: ("🌧️", "Hafif Yağmurlu"),
            63: ("🌧️", "Yağmurlu"),
            65: ("🌧️", "Kuvvetli Yağmurlu"),
            71: ("🌨️", "Hafif Kar"),
            73: ("🌨️", "Kar Yağışlı"),
            75: ("❄️", "Yoğun Kar Yağışlı"),
            80: ("🌦️", "Sağanak Yağış"),
            95: ("⛈️", "Gök Gürültülü Fırtına")
        }
        icon, desc = weather_conditions.get(w_code, ("🌤️", "Normal"))
        
        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 4px;
                background: transparent;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(135deg, #0e1e38 0%, #030712 100%);color:#f8fafc;border:1px solid rgba(56,189,248,0.2);border-radius:16px;padding:20px 26px;width:100%;max-width:380px;box-shadow:0 12px 30px rgba(0,0,0,0.5);position:relative;overflow:hidden;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-size:1.2rem;font-weight:700;color:#f8fafc;">{city_name}</div>
                    <div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">{country}</div>
                </div>
                <div style="font-size:2.2rem;">{icon}</div>
            </div>
            
            <div style="display:flex;align-items:baseline;gap:12px;margin:10px 0 6px 0;">
                <div style="font-size:3rem;font-weight:300;font-family:'Inter',sans-serif;line-height:1;color:#38bdf8;">{temp}°C</div>
                <div style="font-size:0.95rem;color:#cbd5e1;font-weight:500;">{desc}</div>
            </div>
            
            <div style="display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,0.08);padding-top:10px;margin-top:10px;font-size:0.8rem;color:#94a3b8;">
                <div>Hissedilen: <b style="color:#f8fafc;">{feels_like}°C</b></div>
                <div>Nem: <b style="color:#f8fafc;">%{humidity}</b></div>
                <div>Rüzgar: <b style="color:#f8fafc;">{wind} km/s</b></div>
            </div>
        </div>
        """
        
        summary_text = f"{city_name} ({country}) için güncel hava durumu: {desc} ({icon}), Sıcaklık: {temp}°C, Hissedilen: {feels_like}°C, Nem: %{humidity}, Rüzgar: {wind} km/s."
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Hava durumu çekilirken hata oluştu: {str(e)}",
            "widget_html": None
        }

# -------------------------------------------------------------------------
# [WIDGET 5] CANLI DÖVİZ, ALTIN & KRİPTO TAKİPÇİSİ (Financial Rates)
# -------------------------------------------------------------------------
def get_financial_rates(base_currency: str = "USD"):
    """Canlı döviz kurları (USD, EUR, GBP, TRY) ve popüler kripto fiyatlarını (BTC, ETH) çeker."""
    try:
        rates_url = "https://open.er-api.com/v6/latest/USD"
        res = requests.get(rates_url, timeout=4).json()
        rates = res.get("rates", {})
        
        usd_try = rates.get("TRY", 0)
        usd_eur = rates.get("EUR", 0)
        usd_gbp = rates.get("GBP", 0)
        eur_try = (usd_try / usd_eur) if usd_eur else 0
        gbp_try = (usd_try / usd_gbp) if usd_gbp else 0
        
        # Kripto Fiyatları
        btc_usd = 0
        eth_usd = 0
        try:
            c_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd,try", timeout=3).json()
            btc_usd = c_res.get("bitcoin", {}).get("usd", 0)
            eth_usd = c_res.get("ethereum", {}).get("usd", 0)
        except Exception:
            pass
            
        accent_gold = "#d4af37"
        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 4px;
                background: transparent;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(135deg, #091224 0%, #020617 100%);color:#f8fafc;border:1px solid rgba(212,175,55,0.25);border-radius:16px;padding:18px 22px;width:100%;max-width:380px;box-shadow:0 12px 30px rgba(0,0,0,0.5);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-size:0.75rem;font-weight:700;color:{accent_gold};text-transform:uppercase;letter-spacing:0.15em;">📈 Tilikum Financial Ticker</div>
                <span style="font-size:0.7rem;background:rgba(16,185,129,0.15);color:#10b981;padding:2px 8px;border-radius:12px;font-weight:600;">CANLI</span>
            </div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
                <div style="background:#0c172e;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 10px;">
                    <div style="font-size:0.7rem;color:#94a3b8;">USD / TRY</div>
                    <div style="font-size:1.15rem;font-weight:700;color:#f8fafc;font-family:'JetBrains Mono',monospace;">₺{usd_try:.2f}</div>
                </div>
                <div style="background:#0c172e;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 10px;">
                    <div style="font-size:0.7rem;color:#94a3b8;">EUR / TRY</div>
                    <div style="font-size:1.15rem;font-weight:700;color:#f8fafc;font-family:'JetBrains Mono',monospace;">₺{eur_try:.2f}</div>
                </div>
                <div style="background:#0c172e;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 10px;">
                    <div style="font-size:0.7rem;color:#94a3b8;">GBP / TRY</div>
                    <div style="font-size:1.15rem;font-weight:700;color:#f8fafc;font-family:'JetBrains Mono',monospace;">₺{gbp_try:.2f}</div>
                </div>
                <div style="background:#0c172e;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 10px;">
                    <div style="font-size:0.7rem;color:#94a3b8;">Bitcoin (BTC)</div>
                    <div style="font-size:1.15rem;font-weight:700;color:#f59e0b;font-family:'JetBrains Mono',monospace;">${btc_usd:,.0f}</div>
                </div>
            </div>
            <div style="font-size:0.68rem;color:#64748b;text-align:right;">Global piyasa API verileri ile anlık senkronize.</div>
        </div>
        """
        
        summary_text = (
            f"Canlı Piyasa ve Döviz Kurları:\n"
            f"- Dolar (USD/TRY): ₺{usd_try:.2f}\n"
            f"- Euro (EUR/TRY): ₺{eur_try:.2f}\n"
            f"- Sterlin (GBP/TRY): ₺{gbp_try:.2f}\n"
            f"- Bitcoin (BTC/USD): ${btc_usd:,.0f}\n"
            f"- Ethereum (ETH/USD): ${eth_usd:,.0f}"
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Döviz kurları alınırken hata oluştu: {str(e)}",
            "widget_html": None
        }

# -------------------------------------------------------------------------
# [WIDGET 6] DONANIM & SİSTEM TELEMETRİ MONİTÖRÜ (Hardware Monitor)
# -------------------------------------------------------------------------
def get_system_metrics():
    """Bilgisayarın CPU, RAM, Disk doluluk oranlarını ve işletim sistemi telemetrisini raporlar."""
    if psutil is None:
        return {
            "status": "error",
            "message": "psutil kütüphanesi yüklü değil.",
            "widget_html": None
        }
    try:
        cpu_usage = psutil.cpu_percent(interval=0.2)
        cpu_count = psutil.cpu_count(logical=True)
        
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        mem_used_gb = mem.used / (1024 ** 3)
        mem_total_gb = mem.total / (1024 ** 3)
        
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        
        os_name = f"{platform.system()} {platform.release()}"
        
        widget_html = f"""
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 4px;
                background: transparent;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
            }}
        </style>
        <div style="background:linear-gradient(135deg, #09101d 0%, #020617 100%);color:#f8fafc;border:1px solid rgba(16,185,129,0.25);border-radius:16px;padding:18px 24px;width:100%;max-width:380px;box-shadow:0 12px 30px rgba(0,0,0,0.5);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-size:0.75rem;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:0.15em;">💻 System Telemetry</div>
                <span style="font-size:0.7rem;color:#64748b;">{os_name}</span>
            </div>
            
            <!-- CPU Bar -->
            <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:3px;">
                    <span style="color:#94a3b8;">İşlemci (CPU - {cpu_count} Çekirdek)</span>
                    <span style="color:#38bdf8;font-weight:700;">%{cpu_usage:.1f}</span>
                </div>
                <div style="width:100%;height:6px;background:#1e293b;border-radius:3px;overflow:hidden;">
                    <div style="width:{min(cpu_usage, 100)}%;height:100%;background:#38bdf8;border-radius:3px;"></div>
                </div>
            </div>

            <!-- RAM Bar -->
            <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:3px;">
                    <span style="color:#94a3b8;">Bellek (RAM - {mem_used_gb:.1f}/{mem_total_gb:.1f} GB)</span>
                    <span style="color:#a855f7;font-weight:700;">%{mem_percent:.1f}</span>
                </div>
                <div style="width:100%;height:6px;background:#1e293b;border-radius:3px;overflow:hidden;">
                    <div style="width:{min(mem_percent, 100)}%;height:100%;background:#a855f7;border-radius:3px;"></div>
                </div>
            </div>

            <!-- Disk Bar -->
            <div>
                <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:3px;">
                    <span style="color:#94a3b8;">Ana Disk ({disk_free_gb:.0f} GB Boş)</span>
                    <span style="color:#10b981;font-weight:700;">%{disk_percent:.1f}</span>
                </div>
                <div style="width:100%;height:6px;background:#1e293b;border-radius:3px;overflow:hidden;">
                    <div style="width:{min(disk_percent, 100)}%;height:100%;background:#10b981;border-radius:3px;"></div>
                </div>
            </div>
        </div>
        """

        
        summary_text = (
            f"Lokal Donanım Telemetrisi ({os_name}):\n"
            f"- CPU Kullanımı: %{cpu_usage:.1f} ({cpu_count} Mantıksal Çekirdek)\n"
            f"- RAM Kullanımı: %{mem_percent:.1f} ({mem_used_gb:.1f} GB / {mem_total_gb:.1f} GB)\n"
            f"- Disk Doluluğu: %{disk_percent:.1f} (Toplam {disk_total_gb:.1f} GB, Boş {disk_free_gb:.1f} GB)"
        )
        return {
            "status": "success",
            "message": summary_text,
            "widget_html": widget_html
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sistem verileri okunurken hata: {str(e)}",
            "widget_html": None
        }

# -------------------------------------------------------------------------
# [WEB 1] DUCKDUCKGO & VİKİPEDİ HİBRİT İNTERNET ARAMA MOTORU
# -------------------------------------------------------------------------
def clean_search_text(text: str) -> str:
    """Arama sorgusundaki dolgu kelimelerini ve noktalama işaretlerini temizler."""
    stop_words = [
        "hayır", "evet", "peki", "acaba", "lütfen", "bana", "anlat", "söyle",
        "nerede", "nerededir", "kaç", "kaçtır", "metre", "nedir", "nelerdir",
        "nasıl", "nasıldır", "ne kadar", "hakkında", "bilgi", "ver", "mıdır",
        "midir", "mu", "mü", "olan", "ve", "ile", "de", "da"
    ]
    cleaned = re.sub(r'[\?\!\.\,\:\;\"\'\(\)]', ' ', str(text))
    tokens = [w for w in cleaned.split() if w.lower() not in stop_words and len(w) > 1]
    return " ".join(tokens)

def search_web_duckduckgo(query: str, max_results: int = 4) -> list:
    """İnternette doğrudan, zengin ve asla boş dönmeyen canlı arama yapar."""
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    clean_q = clean_search_text(query)
    search_queries = [q for q in [clean_q, query] if q and len(q) > 2]
    
    # 1. DDGS ile Canlı Arama
    if DDGS is not None:
        try:
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
                                results.append({"title": title, "href": href, "body": body})
                        break
        except Exception:
            pass

    # 2. Wikipedia REST API Fallback
    if not results:
        for s_term in search_queries:
            try:
                wiki_search_url = "https://tr.wikipedia.org/w/api.php"
                params = {"action": "query", "list": "search", "srsearch": s_term, "format": "json", "srlimit": max_results}
                resp = requests.get(wiki_search_url, params=params, headers=headers, timeout=4)
                if resp.status_code == 200:
                    search_data = resp.json()
                    for item in search_data.get("query", {}).get("search", []):
                        title = item.get("title", "")
                        if title and "fuhuş" not in title.lower():
                            sum_api = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
                            s_resp = requests.get(sum_api, headers=headers, timeout=3)
                            if s_resp.status_code == 200:
                                ext = s_resp.json().get("extract", "")
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

def execute_web_search(query: str, max_results: int = 4) -> dict:
    """Ajanın çağıracağı web arama fonksiyonu ve çıktı biçimlendirici."""
    raw_results = search_web_duckduckgo(query, max_results=max_results)
    if not raw_results:
        return {
            "status": "not_found",
            "message": f"'{query}' sorgusu için internette doğrudan bir sonuç bulunamadı.",
            "results": []
        }
    
    formatted_text = f"İnternet Arama Sonuçları ('{query}'):\n\n"
    for i, r in enumerate(raw_results, 1):
        formatted_text += f"[{i}] Başlık: {r['title']}\nKaynak: {r['href']}\nÖzet: {r['body']}\n\n"
        
    return {
        "status": "success",
        "message": formatted_text,
        "results": raw_results
    }

# -------------------------------------------------------------------------
# [WEB 2] AKILLI WEB SCRAPER & MAKALE OKUYUCU (Article Reader)
# -------------------------------------------------------------------------
def scrape_web_page(url: str, max_chars: int = 3000) -> dict:
    """Bir web sayfasını reklamlardan ve karmaşadan arındırıp temiz makale metnine dönüştürür."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return {
                "status": "error",
                "message": f"Sayfa yüklenemedi (HTTP {resp.status_code}).",
                "content": "",
                "title": url,
                "url": url
            }
            
        if BeautifulSoup is not None:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript', 'svg']):
                tag.decompose()
                
            title = soup.title.string.strip() if soup.title else url
            paragraphs = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']) if len(p.get_text().strip()) > 20]
            clean_text = "\n\n".join(paragraphs)
            if not clean_text:
                clean_text = " ".join(soup.stripped_strings)
        else:
            title = url
            clean_text = re.sub(r'<[^>]+>', ' ', resp.text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
        clean_text = clean_text[:max_chars]
        
        return {
            "status": "success",
            "title": title,
            "url": url,
            "content": clean_text,
            "message": f"Web Sayfası Başarıyla Okundu: '{title}' ({url})\n\nİçerik Özeti:\n{clean_text[:1500]}..."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sayfa okunurken hata oluştu: {str(e)}",
            "content": "",
            "title": url,
            "url": url
        }

# =========================================================================
# 2. ARAÇ DISPATCHER VE OPENAI UYUMLU TOOL SCHEMAS
# =========================================================================
AVAILABLE_TOOLS = {
    "create_js_clock_widget": create_js_clock_widget,
    "create_countdown_timer_widget": create_countdown_timer_widget,
    "create_calculator_widget": create_calculator_widget,
    "get_weather_forecast": get_weather_forecast,
    "get_financial_rates": get_financial_rates,
    "get_system_metrics": get_system_metrics,
    "duckduckgo_search": execute_web_search,
    "search_web": execute_web_search,
    "scrape_web_page": scrape_web_page
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "create_js_clock_widget",
            "description": "Kullanıcı yerel saati veya dünya üzerindeki herhangi bir şehrin/ülkenin (Tokyo, Londra, New York, Paris, Berlin, Moskova, Dubai, Pekin, vb.) saatini sorduğunda o şehre ait canlı akıcı lüks saat widgetı (HTML/CSS/JS) oluşturur ve gerçek saati bildirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_or_timezone": {
                        "type": "string",
                        "description": "Saatini öğrenmek istediğiniz şehir veya zaman dilimi (örn: 'Tokyo', 'London', 'New York', 'Istanbul', 'Paris', 'Dubai', 'Pekin', 'Asia/Tokyo', 'UTC')",
                        "default": "İstanbul"
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["dark", "light"],
                        "description": "Widget görsel teması",
                        "default": "dark"
                    }
                },
                "required": ["city_or_timezone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_countdown_timer_widget",
            "description": "Kullanıcı geri sayım, Pomodoro veya odaklanma sayacı istediğinde (örn: '25 dakikalık Pomodoro başlat', '10 dakika geri say') ekranda canlı çalışan interaktif bir zamanlayıcı widgetı oluşturur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Geri sayım süresi (dakika cinsinden, örn: 25)",
                        "default": 25
                    },
                    "label": {
                        "type": "string",
                        "description": "Sayacın başlığı veya konusu (örn: 'Pomodoro Odaklanma', 'Mola', 'Çay Saati')",
                        "default": "Pomodoro Odaklanma"
                    }
                },
                "required": ["minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calculator_widget",
            "description": "Kullanıcı hesaplama yapmak istediğinde veya ekranda interaktif bir hesap makinesi görmek istediğinde çalışan şık bir JavaScript hesap makinesi widgetı oluşturur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "initial_expression": {
                        "type": "string",
                        "description": "Hesap makinesine önceden yüklenecek matematiksel ifade veya boş bırakılabilir (örn: '250 * 1.20')",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Belirtilen bir şehir veya bölge için gerçek zamanlı hava durumu, sıcaklık, hissedilen derece, nem ve rüzgar verilerini çeker ve şık bir hava durumu kartı çizer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Hava durumu öğrenilmek istenen şehir adı (örn: 'İstanbul', 'Ankara', 'İzmir', 'London', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_rates",
            "description": "Canlı döviz kurlarını (Dolar, Euro, Sterlin, TL) ve kripto para fiyatlarını (Bitcoin, Ethereum) anlık piyasa API'sinden çeker ve görsel finansal ticker kartı sunar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_currency": {
                        "type": "string",
                        "description": "Baz para birimi (varsayılan: 'USD')",
                        "default": "USD"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_metrics",
            "description": "Bilgisayarın işlemci (CPU), bellek (RAM), disk doluluk oranlarını ve sistem bilgilerini canlı olarak ölçer ve donanım paneli çizer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "duckduckgo_search",
            "description": "İnternette canlı arama yapar. Kullanıcı güncel olaylar, okyanus bilgileri, hava durumu, genel kültür, kişiler veya internet araştırması gerektiren sorular sorduğunda DuckDuckGo üzerinden en doğru bilgileri getirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Arama motorunda aranacak anahtar kelimeler (örn: 'Mariana Çukuru derinliği', 'en son teknoloji haberleri')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Getirilecek maksimum sonuç sayısı (varsayılan: 4)",
                        "default": 4
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_web_page",
            "description": "Verilen bir web sitesi veya makale linkindeki (URL) içeriği reklamlardan ve kod karmaşasından arındırıp temiz metin olarak okur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Okunacak web sayfasının tam adresi (örn: 'https://tr.wikipedia.org/wiki/Mariana_%C3%87ukuru')"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Çekilecek maksimum karakter sayısı (varsayılan: 3000)",
                        "default": 3000
                    }
                },
                "required": ["url"]
            }
        }
    }
]

# =========================================================================
# 3. SESSION STATE (GEÇMİŞ VE ÖNBELLEK YÖNETİMİ)
# =========================================================================
if "premium_widget_messages" not in st.session_state:
    st.session_state.premium_widget_messages = []
if "premium_active_widgets" not in st.session_state:
    st.session_state.premium_active_widgets = {} # Mesaj indexlerine göre çalışan aktif widgetlar (html + height)
if "premium_active_sources" not in st.session_state:
    st.session_state.premium_active_sources = {} # Mesaj indexlerine göre web arama sonuçları
if "premium_active_scrapes" not in st.session_state:
    st.session_state.premium_active_scrapes = {} # Mesaj indexlerine göre web makale okuma kartları

# =========================================================================
# 4. SIDEBAR (LM STUDIO KONFİGÜRASYONU VE SİSTEM BİLGİSİ)
# =========================================================================
st.sidebar.image(
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=300&auto=format&fit=crop", 
    caption="Tilikum Elite Tool Suite", 
    width="stretch"
)

st.sidebar.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
st.sidebar.title("💎 Elite Control Panel")

lm_url = st.sidebar.text_input(
    "LM Studio API Adresi", 
    value="http://localhost:1234/v1",
    help="LM Studio'nun yerel API adresi (varsayılan port: 1234)"
)

lm_model = st.sidebar.text_input(
    "Model Adı", 
    value="qwen2.5:3b",
    help="LM Studio'da yüklü olan Tool Calling destekli model."
)
st.sidebar.markdown("</div>", unsafe_allow_html=True)

st.sidebar.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
st.sidebar.markdown(
    "💼 **Altın 6'lı + Executive Yetenekler:**\n\n"
    "- ⏱️ **Lüks Saat & Pomodoro:** Canlı saat ve interaktif geri sayım sayacı.\n\n"
    "- 🌦️ **Canlı Hava Durumu:** Global şehirlerin anlık hava durumu ve tahminleri.\n\n"
    "- 📈 **Finans & Kripto:** USD, EUR, GBP, BTC, ETH canlı kurlar.\n\n"
    "- 🧮 **İnteraktif Hesap Makinesi:** Canlı JS hesaplayıcı kartı.\n\n"
    "- 💻 **Donanım Telemetrisi:** CPU, RAM ve disk doluluk takibi.\n\n"
    "- 🌐 **DuckDuckGo & Makale Okuyucu:** Canlı arama ve reklamdan arındırılmış web okuyucu."
)
st.sidebar.markdown("</div>", unsafe_allow_html=True)

if st.sidebar.button("Geçmişi ve Belleği Sıfırla"):
    st.session_state.premium_widget_messages = []
    st.session_state.premium_active_widgets = {}
    st.session_state.premium_active_sources = {}
    st.session_state.premium_active_scrapes = {}
    st.success("Elite bellek sıfırlandı!")

# =========================================================================
# 5. SOHBET AKIŞI VE AJAN DÖNGÜSÜ (AGENT LOOP)
# =========================================================================

# Eski mesajları listele
for idx, message in enumerate(st.session_state.premium_widget_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Eğer bu mesaja ait bir widget varsa tekrar render et
        if idx in st.session_state.premium_active_widgets:
            w_info = st.session_state.premium_active_widgets[idx]
            w_html = w_info.get("html", "")
            w_height = w_info.get("height", 260)
            if w_html:
                components.html(w_html, height=w_height)
            
        # Eğer bu mesaja ait web arama kaynakları varsa göster
        if idx in st.session_state.premium_active_sources:
            sources = st.session_state.premium_active_sources[idx]
            if sources:
                with st.expander(f"🌐 İnternet Arama Kaynakları ({len(sources)} Sonuç)", expanded=False):
                    for s in sources:
                        st.markdown(f"🔹 **[{s.get('title', 'Web Kaynağı')}]({s.get('href', '#')})**\n\n{s.get('body', '')}")

        # Eğer bu mesaja ait web makale okuma kartı varsa göster
        if idx in st.session_state.premium_active_scrapes:
            scrape_data = st.session_state.premium_active_scrapes[idx]
            if scrape_data:
                with st.expander(f"📄 Okunan Web Makalesi: {scrape_data.get('title', 'Makale')}", expanded=False):
                    st.markdown(f"**Kaynak:** [{scrape_data.get('url', '#')}]({scrape_data.get('url', '#')})")
                    st.markdown(scrape_data.get("content", "")[:1000] + "...")

# Kullanıcı Girişi
if prompt := st.chat_input("Saati sor, Pomodoro başlat, hava durumunu veya kurları öğren..."):
    
    # Kullanıcı mesajını kaydet ve göster
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.premium_widget_messages.append({"role": "user", "content": prompt})
    
    # Asistan süreci
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        log_placeholder = st.empty()
        
        SYSTEM_INSTRUCTION = {
            "role": "system",
            "content": (
                "Sen Tilikum AI adında lüks, yetenekli ve son derece profesyonel bir Executive Widget Asistanısın.\n\n"
                "ÖNEMLİ ÇALIŞMA KURALLARI:\n"
                "1. Kullanıcı yerel saati veya dünya üzerindeki HERHANGİ bir şehrin (Tokyo, Londra, New York, Paris, Berlin, Moskova, Dubai, Pekin vb.) "
                "saatini sorduğunda ('Tokyo da saat kaç', 'Londra saati nedir' vb.) ASLA 'internete bakın' veya 'siteye gidin' gibi cevaplar verme! "
                "MUTLAKA ve DOĞRUDAN 'create_js_clock_widget' aracını çağır ve 'city_or_timezone' parametresine ilgili şehri gir (örn: {\"city_or_timezone\": \"Tokyo\"}).\n"
                "2. Hava durumu için 'get_weather_forecast', döviz ve kripto için 'get_financial_rates', "
                "hesaplama için 'create_calculator_widget', sayaç/pomodoro için 'create_countdown_timer_widget', "
                "donanım/bilgisayar performansı için 'get_system_metrics', internet aramaları için 'duckduckgo_search' araçlarını kullan.\n"
                "3. Araç çalıştırıldıktan sonra dönen gerçek verileri kullanarak kullanıcıya net, doğrudan ve kibar Türkçe yanıt ver."
            )
        }
        
        # 1. Adım: LM Studio API'sine İstek Hazırlama
        api_headers = {"Content-Type": "application/json"}
        active_messages = [SYSTEM_INSTRUCTION] + [m for m in st.session_state.premium_widget_messages if m.get("role") != "system"]
        payload = {
            "model": lm_model,
            "messages": active_messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto"
        }
        
        try:
            # Premium Terminal Log Başlangıç
            log_placeholder.markdown(
                "<div class='system-log-container'>"
                "<div class='system-log-title'>🛰️ System Core Connection</div>"
                "<div class='system-log-content'>Initializing agent loop... Requesting analysis from LM Studio API.</div>"
                "</div>", 
                unsafe_allow_html=True
            )
            
            response = requests.post(
                f"{lm_url}/chat/completions",
                json=payload,
                headers=api_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                res_json = response.json()
                choice = res_json.get("choices", [{}])[0]
                message_data = choice.get("message", {})
                
                # Modelden normal bir metin yanıtı mı geldi yoksa TOOL CALL mu?
                tool_calls = message_data.get("tool_calls", [])
                
                if tool_calls:
                    # Model bir araç çağırmaya karar verdi!
                    tool_call = tool_calls[0]
                    func_name = tool_call.get("function", {}).get("name")
                    func_args_str = tool_call.get("function", {}).get("arguments", "{}")
                    
                    try:
                        func_args = json.loads(func_args_str)
                    except Exception:
                        func_args = {}
                    
                    # Premium Terminal Log - Karar Bildirimi
                    log_placeholder.markdown(
                        "<div class='system-log-container'>"
                        "<div class='system-log-title'>🎯 Agent Decision Synthesized</div>"
                        f"<div class='system-log-content'>Model selected active tool: <b>{func_name}</b><br>"
                        f"Allocated parameters: <code>{json.dumps(func_args)}</code></div>"
                        "</div>", 
                        unsafe_allow_html=True
                    )
                    
                    # 2. Adım: Python Tarafındaki Gerçek Fonksiyonu Tetikleme
                    if func_name in AVAILABLE_TOOLS:
                        msg_idx = len(st.session_state.premium_widget_messages)
                        tool_func = AVAILABLE_TOOLS[func_name]
                        tool_feedback_content = ""
                        
                        # --- [A] LÜKS SAAT WIDGET'I ---
                        if func_name == "create_js_clock_widget":
                            clock_res = tool_func(**func_args)
                            if isinstance(clock_res, dict):
                                widget_html = clock_res.get("widget_html", "")
                                tool_feedback_content = clock_res.get("message", "Saat widgetı oluşturuldu.")
                            else:
                                widget_html = str(clock_res)
                                tool_feedback_content = "Saat widgetı başarıyla oluşturuldu."
                                
                            components.html(widget_html, height=240)
                            st.session_state.premium_active_widgets[msg_idx] = {"html": widget_html, "height": 240}

                        # --- [B] POMODORO & GERİ SAYIM SAYACI ---
                        elif func_name == "create_countdown_timer_widget":
                            widget_html = tool_func(**func_args)
                            components.html(widget_html, height=250)
                            st.session_state.premium_active_widgets[msg_idx] = {"html": widget_html, "height": 250}
                            
                            tool_feedback_content = f"Geri sayım sayacı ({func_args.get('minutes', 25)} dakika) başlatıldı ve ekrana yerleştirildi."

                        # --- [C] HESAP MAKİNESİ ---
                        elif func_name == "create_calculator_widget":
                            widget_html = tool_func(**func_args)
                            components.html(widget_html, height=450)
                            st.session_state.premium_active_widgets[msg_idx] = {"html": widget_html, "height": 450}
                            
                            tool_feedback_content = "İnteraktif hesap makinesi başarıyla ekrana yerleştirildi."

                        # --- [D] HAVA DURUMU KARTI ---
                        elif func_name == "get_weather_forecast":
                            w_res = tool_func(**func_args)
                            if w_res.get("widget_html"):
                                components.html(w_res["widget_html"], height=260)
                                st.session_state.premium_active_widgets[msg_idx] = {"html": w_res["widget_html"], "height": 260}
                            tool_feedback_content = w_res.get("message", "Hava durumu verisi çekildi.")

                        # --- [E] CANLI DÖVİZ & KRİPTO ---
                        elif func_name == "get_financial_rates":
                            fin_res = tool_func(**func_args)
                            if fin_res.get("widget_html"):
                                components.html(fin_res["widget_html"], height=260)
                                st.session_state.premium_active_widgets[msg_idx] = {"html": fin_res["widget_html"], "height": 260}
                            tool_feedback_content = fin_res.get("message", "Finansal veriler çekildi.")

                        # --- [F] DONANIM & TELEMETRİ ---
                        elif func_name == "get_system_metrics":
                            sys_res = tool_func(**func_args)
                            if sys_res.get("widget_html"):
                                components.html(sys_res["widget_html"], height=250)
                                st.session_state.premium_active_widgets[msg_idx] = {"html": sys_res["widget_html"], "height": 250}
                            tool_feedback_content = sys_res.get("message", "Sistem telemetrisi ölçüldü.")

                        # --- [G] DUCKDUCKGO WEB ARAMASI ---
                        elif func_name in ["duckduckgo_search", "search_web"]:
                            search_res = tool_func(**func_args)
                            sources = search_res.get("results", [])
                            if sources:
                                with st.expander(f"🌐 İnternet Arama Kaynakları ({len(sources)} Sonuç)", expanded=True):
                                    for s in sources:
                                        st.markdown(f"🔹 **[{s.get('title', 'Web Kaynağı')}]({s.get('href', '#')})**\n\n{s.get('body', '')}")
                                st.session_state.premium_active_sources[msg_idx] = sources
                            tool_feedback_content = search_res.get("message", "Arama tamamlandı.")

                        # --- [H] WEB MAKALE OKUYUCU ---
                        elif func_name == "scrape_web_page":
                            scrape_res = tool_func(**func_args)
                            if scrape_res.get("status") == "success":
                                with st.expander(f"📄 Okunan Web Makalesi: {scrape_res.get('title', 'Makale')}", expanded=True):
                                    st.markdown(f"**Kaynak:** [{scrape_res.get('url', '#')}]({scrape_res.get('url', '#')})")
                                    st.markdown(scrape_res.get("content", "")[:1200] + "...")
                                st.session_state.premium_active_scrapes[msg_idx] = scrape_res
                            tool_feedback_content = scrape_res.get("message", "Web içeriği okundu.")

                        else:
                            tool_result = tool_func(**func_args)
                            tool_feedback_content = str(tool_result)

                        # 3. Adım: Sonucu LM Studio'ya geri besleme yapıp asistanın kapanış cümlesi üretmesini sağlama
                        st.session_state.premium_widget_messages.append(message_data)
                        st.session_state.premium_widget_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", "1"),
                            "name": func_name,
                            "content": tool_feedback_content
                        })
                        
                        # Premium Terminal Log - Tamamlama
                        log_placeholder.markdown(
                            "<div class='system-log-container'>"
                            "<div class='system-log-title'>⚙️ Pipeline Synchronization</div>"
                            "<div class='system-log-content'>Feeding execution token back to the language model. Completing loop.</div>"
                            "</div>", 
                            unsafe_allow_html=True
                        )
                        
                        followup_messages = [SYSTEM_INSTRUCTION] + [m for m in st.session_state.premium_widget_messages if m.get("role") != "system"]
                        final_response = requests.post(
                            f"{lm_url}/chat/completions",
                            json={
                                "model": lm_model,
                                "messages": followup_messages
                            },
                            headers=api_headers,
                            timeout=30
                        )
                        
                        if final_response.status_code == 200:
                            final_text = final_response.json()["choices"][0]["message"]["content"]
                            response_placeholder.markdown(final_text)
                            st.session_state.premium_widget_messages.append({"role": "assistant", "content": final_text})
                            log_placeholder.empty()
                        else:
                            st.error("Kapanış cümlesi alınırken hata oluştu.")
                    else:
                        st.error(f"Sistemde '{func_name}' isminde bir Python fonksiyonu bulunamadı!")
                else:
                    # Model araç çağırmadı, normal konuştu
                    llm_content = message_data.get("content", "")
                    response_placeholder.markdown(llm_content)
                    st.session_state.premium_widget_messages.append({"role": "assistant", "content": llm_content})
                    log_placeholder.empty()
                    
            else:
                st.error(f"LM Studio Hatası: {response.status_code}")
                st.info("Lütfen LM Studio'da API sunucusunun açık olduğundan ve modelin doğru yüklendiğinden emin olun.")
                log_placeholder.empty()
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Hata: Yerel LM Studio sunucusuna bağlanılamadı!")
            st.info(f"Lütfen LM Studio uygulamasında Developer/Server sekmesini açıp sunucuyu başlatın. Adres: {lm_url}")
            log_placeholder.empty()
        except Exception as e:
            st.error(f"Sistem Hatası: {str(e)}")
            log_placeholder.empty()

