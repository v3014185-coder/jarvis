# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. — финальная версия.
Wake-word, XTTS, трей, темы, HUD, поиск, микрофон USB MIC PRO.
"""

import tkinter as tk
from tkinter import messagebox
import webbrowser
import subprocess
import os
import random
import threading
import datetime
import time
import json
import asyncio
import tempfile
import math
import re
import urllib.parse
import hashlib
import glob

# ============================================================
#  НАСТРОЙКИ
# ============================================================
GIGACHAT_CREDENTIALS = ""
USER_NAME = "сэр"
CITY = "Белогорск"
CITY_LAT = 50.9167
CITY_LON = 128.4667

FFMPEG_BIN = r"D:\AI_Models\ffmpeg-7.1.1-full_build-shared\bin"
VOICE_SAMPLE = r"C:\Users\Admin\Desktop\jarvis\jarvis_sample.wav"
VISEL_DIR = r"C:\Users\Admin\Desktop\viseJirvis"
XTTS_MAX_LEN = 100

# === МИКРОФОН ===
# 3 = Микрофон (USB MIC PRO)
MIC_DEVICE = 3

WAKE_WORDS = ["джарвис", "пятница", "пятницу", "пятницы"]
WAKE_PARTS = ["джарв", "джерв", "джервис", "джавис", "джарви", "чарлис", "гарвис",
              "пятн", "петн", "питниц", "пятнец"]
WAKE_ACTIVE_TIMEOUT = 30
WAKE_ACK = "Да, сэр?"
WAKE_MIN_INTERVAL = 2

SYSTEM_PROMPT = (
    "Ты — Джарвис, персональный ИИ-дворецкий пользователя. "
    "Обращаешься к пользователю 'сэр'. Ты невозмутим, вежлив, с сухим британским юмором. "
    "Никогда не теряешь самообладание. Иногда позволяешь себе лёгкую иронию. "
    "Не льстишь. Если не знаешь — говоришь: 'У меня нет данных, сэр'. "
    "Заботишься о безопасности — предупреждаешь, но выполняешь. "
    "Отвечай кратко, 1-2 предложения — тебя озвучивают голосом. "
    "Без markdown, эмодзи и списков. Никогда не упоминай модели и API. Ты просто Джарвис."
)

STATE_FILE = "jarvis_state.json"
HISTORY_FILE = "chat_history.txt"
VOICE_CACHE_DIR = "voice_cache"
TASKS_FILE = "jarvis_tasks.json"

# ============================================================
#  ТЕМЫ
# ============================================================
THEMES = {
    "cyan":   {"accent": "#00e8ff", "dim": "#006678", "glow": "#003a44",
               "user": "#00ff88", "user_dim": "#004422"},
    "green":  {"accent": "#00ff88", "dim": "#006644", "glow": "#003a22",
               "user": "#00e8ff", "user_dim": "#004466"},
    "red":    {"accent": "#ff3355", "dim": "#7a1020", "glow": "#3a0810",
               "user": "#ffaa00", "user_dim": "#553300"},
    "orange": {"accent": "#ffaa00", "dim": "#7a5500", "glow": "#3a2800",
               "user": "#00e8ff", "user_dim": "#004466"},
    "purple": {"accent": "#cc66ff", "dim": "#662299", "glow": "#3a0d5c",
               "user": "#00ff88", "user_dim": "#004422"},
}

# ============================================================
#  ПОГОДА
# ============================================================
WEATHER_CODES = {
    0: "ясно", 1: "преимущественно ясно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 48: "изморозь", 51: "лёгкая морось", 53: "морось", 55: "сильная морось",
    61: "лёгкий дождь", 63: "дождь", 65: "сильный дождь",
    71: "лёгкий снег", 73: "снег", 75: "сильный снег",
    80: "ливень", 81: "сильный ливень", 82: "очень сильный ливень",
    95: "гроза", 96: "гроза с градом", 99: "сильная гроза",
}
WEATHER_ICONS = {
    0: "☀", 1: "🌤", 2: "⛅", 3: "☁",
    45: "🌫", 48: "🌫",
    51: "🌦", 53: "🌦", 55: "🌧",
    61: "🌧", 63: "🌧", 65: "🌧",
    71: "🌨", 73: "🌨", 75: "❄",
    80: "🌦", 81: "🌧", 82: "⛈",
    95: "⛈", 96: "⛈", 99: "⛈",
}

# ============================================================
#  ПОИСК
# ============================================================
last_search_results = []

def search_duckduckgo(query, max_results=3):
    global last_search_results
    try:
        import requests
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=10)
        html = r.text
        pattern = re.compile(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>'
            r'.*?<a class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        matches = pattern.findall(html)
        results = []
        for url_raw, title_raw, snippet_raw in matches[:max_results]:
            def clean(s):
                s = re.sub(r'<[^>]+>', '', s)
                s = s.replace('&amp;', '&').replace('&quot;', '"')
                s = s.replace('&#x27;', "'").replace('&nbsp;', ' ')
                return s.strip()
            url_final = url_raw
            if "uddg=" in url_raw:
                try:
                    url_final = urllib.parse.unquote(url_raw.split("uddg=")[1].split("&")[0])
                except: pass
            results.append({
                "title": clean(title_raw)[:80],
                "url": url_final,
                "snippet": clean(snippet_raw)[:200],
                "domain": url_final.split("/")[2] if "://" in url_final else url_final[:30]
            })
        last_search_results = results
        return results
    except Exception as e:
        print(f"[SEARCH] Ошибка: {e}")
        return []

def format_search_results(query, results):
    if not results:
        return f"Ничего не нашёл по запросу «{query}». Попробуйте переформулировать."
    lines = [f"🔍 По запросу «{query}»:"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. {r['title']}")
        lines.append(f"   {r['domain']}")
        if r['snippet']:
            lines.append(f"   {r['snippet']}")
    lines.append("\nСкажите «открой результат 1» или «открой первый»")
    return "\n".join(lines)

# ============================================================
#  ФРАЗЫ ИЗ viselJarvis
# ============================================================
def play_sound_file(filename):
    path = os.path.join(VISEL_DIR, filename)
    if not os.path.exists(path): return False
    try:
        import soundfile as sf
        import sounddevice as sd
        speaking_flag.set()
        try:
            data, sr = sf.read(path)
            sd.play(data, sr); sd.wait()
        finally:
            time.sleep(0.3); speaking_flag.clear()
        return True
    except Exception as e:
        print(f"[SOUND] {e}"); return False

# ============================================================
#  МОИ ПРОГРАММЫ
# ============================================================
def _find_roblox():
    base = os.path.expanduser(r"~\AppData\Local\Roblox\Versions")
    if os.path.isdir(base):
        found = glob.glob(os.path.join(base, "version-*", "RobloxPlayerBeta.exe"))
        if found: return sorted(found)[-1]
    return None

MY_APPS = {
    "вар тандер": r"D:\WarThunder\launcher.exe",
    "warthunder": r"D:\WarThunder\launcher.exe",
    "war thunder": r"D:\WarThunder\launcher.exe",
    "тандер": r"D:\WarThunder\launcher.exe",
    "вартандер": r"D:\WarThunder\launcher.exe",
    "танки": r"D:\WarThunder\launcher.exe",
}
_roblox_path = _find_roblox()
if _roblox_path:
    for name in ["роблокс", "roblox", "робл", "роблок"]:
        MY_APPS[name] = _roblox_path
    print(f"[ROBLOX] {_roblox_path}")

# ============================================================
#  СОСТОЯНИЕ
# ============================================================
def load_state():
    defaults = {
        "user_name": USER_NAME, "silent_mode": False,
        "voice": "ru-RU-DmitryNeural", "pitch": "-10Hz", "rate": "+10%",
        "todos": [], "notes": [], "theme": "cyan",
        "use_jarvis_voice": True, "city": CITY,
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except: pass
    # Всегда сбрасываем тихий режим при старте
    defaults["silent_mode"] = False
    return defaults

STATE = load_state()

def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(STATE, f, ensure_ascii=False, indent=2)
    except: pass

print(f"[STATE] use_jarvis_voice={STATE.get('use_jarvis_voice')}, silent_mode={STATE.get('silent_mode')}")

# ============================================================
#  ЗАДАЧИ
# ============================================================
def load_tasks():
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def save_tasks(tasks):
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except: pass

TASKS = load_tasks()
tasks_lock = threading.Lock()

def parse_task_time(cmd):
    now = datetime.datetime.now()
    m = re.search(r"завтра\s+в\s+(\d{1,2})[:.]?(\d{2})?", cmd)
    if m:
        h = int(m.group(1)); mi = int(m.group(2) or 0)
        return now.replace(hour=h, minute=mi, second=0, microsecond=0) + datetime.timedelta(days=1)
    m = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s+в\s+(\d{1,2})[:.]?(\d{2})?", cmd)
    if m:
        d = int(m.group(1)); mo = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else now.year
        h = int(m.group(4)); mi = int(m.group(5) or 0)
        try:
            dt = datetime.datetime(y, mo, d, h, mi)
            if dt < now: dt = dt.replace(year=dt.year + 1)
            return dt
        except: return None
    m = re.search(r"\bв\s+(\d{1,2})[:.](\d{2})\b", cmd)
    if m:
        h = int(m.group(1)); mi = int(m.group(2))
        dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if dt <= now: dt += datetime.timedelta(days=1)
        return dt
    m = re.search(r"через\s+(\d+)\s*(минут|час|секунд|ч|м)", cmd)
    if m:
        n = int(m.group(1)); u = m.group(2)
        if "час" in u or u == "ч": return now + datetime.timedelta(hours=n)
        if "секунд" in u: return now + datetime.timedelta(seconds=n)
        return now + datetime.timedelta(minutes=n)
    return None

def add_task(text, dt):
    with tasks_lock:
        task = {"id": len(TASKS)+1 if not TASKS else max(t["id"] for t in TASKS)+1,
                "text": text, "time": dt.isoformat(), "done": False}
        TASKS.append(task); save_tasks(TASKS)
    return task

def check_tasks_loop():
    while True:
        try:
            now = datetime.datetime.now()
            with tasks_lock:
                changed = False
                for t in TASKS:
                    if t.get("done"): continue
                    try: tt = datetime.datetime.fromisoformat(t["time"])
                    except: continue
                    if tt <= now:
                        t["done"] = True; changed = True
                        msg = f"Напоминание, {STATE['user_name']}: {t['text']}"
                        root.after(0, lambda m=msg: add_message(m, is_user=False))
                        root.after(0, lambda m=msg: speak(m))
                        play_sound_file("Еще один заряд израсходован.wav")
                if changed: save_tasks(TASKS)
        except Exception as e:
            print(f"Планировщик: {e}")
        time.sleep(20)

# ============================================================
#  ТАЙМЕРЫ
# ============================================================
timers = []
timers_lock = threading.Lock()

def add_timer(seconds, label="Таймер"):
    tid = len(timers) + 1
    def ring():
        time.sleep(seconds)
        with timers_lock:
            t = next((x for x in timers if x["id"] == tid), None)
            if not t or t.get("cancelled"): return
        msg = f"{label} сработал!"
        root.after(0, lambda: add_message(msg, is_user=False))
        speak(msg)
        play_sound_file("Еще один заряд израсходован.wav")
    th = threading.Thread(target=ring, daemon=True)
    with timers_lock:
        timers.append({"id": tid, "thread": th, "label": label,
                       "time": time.time() + seconds, "cancelled": False})
    th.start()
    return tid

def cancel_all_timers():
    with timers_lock:
        for t in timers: t["cancelled"] = True
        n = len(timers); timers.clear()
    return n

# ============================================================
#  ОЗВУЧКА
# ============================================================
try:
    os.add_dll_directory(FFMPEG_BIN)
except: pass

TTS_OK = False; XTTS_OK = False
xtts_model = None; xtts_voice_sample = None
speaking_flag = threading.Event()

try:
    import edge_tts
    import soundfile as sf
    import sounddevice as sd
    TTS_OK = True
    print("Edge-TTS готов.")
except Exception as e:
    print("Edge-TTS:", e)

try:
    from TTS.api import TTS as XTTS_API
    if os.path.exists(VOICE_SAMPLE):
        print("Загружаю XTTS...")
        xtts_model = XTTS_API("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        xtts_voice_sample = VOICE_SAMPLE
        XTTS_OK = True
        print("XTTS готов.")
except Exception as e:
    print(f"XTTS: {e}")

os.makedirs(VOICE_CACHE_DIR, exist_ok=True)

def _hash_text(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

def _speak_xtts(text):
    cache_file = os.path.join(VOICE_CACHE_DIR, f"jarvis_{_hash_text(text)}.wav")
    try:
        if not os.path.exists(cache_file):
            print(f"[XTTS] Генерирую ({len(text)} симв.): {text[:60]}...")
            xtts_model.tts_to_file(text=text, speaker_wav=xtts_voice_sample,
                                    language="ru", file_path=cache_file)
        else:
            print(f"[XTTS] Из кэша: {text[:60]}...")
        data, sr = sf.read(cache_file)
        sd.play(data, sr); sd.wait()
        return True
    except Exception as e:
        print(f"[XTTS] ОШИБКА: {e}")
        return False

def _speak_edge(text):
    async def _gen():
        comm = edge_tts.Communicate(text=text, voice=STATE["voice"],
                                     rate=STATE["rate"], pitch=STATE["pitch"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            p = fp.name
        await comm.save(p)
        return p
    try:
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        f = loop.run_until_complete(_gen()); loop.close()
        data, sr = sf.read(f); sd.play(data, sr); sd.wait(); os.remove(f)
    except Exception as e: print(f"Edge: {e}")

def _speak_async(text):
    if STATE["silent_mode"]: return
    speaking_flag.set()
    try:
        if XTTS_OK and STATE.get("use_jarvis_voice", True) and len(text) <= XTTS_MAX_LEN:
            if _speak_xtts(text): return
        if TTS_OK: _speak_edge(text)
    finally:
        time.sleep(0.4); speaking_flag.clear()

def speak(text):
    if (TTS_OK or XTTS_OK) and not STATE["silent_mode"]:
        threading.Thread(target=_speak_async, args=(text,), daemon=True).start()

# ============================================================
#  GIGACHAT
# ============================================================
GIGA_OK = False; giga = None; chat_context = []
try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    giga = GigaChat(credentials=GIGACHAT_CREDENTIALS,
                     base_url="https://api.giga.chat/v1",
                     scope="GIGACHAT_API_PERS",
                     verify_ssl_certs=False, model="GigaChat-2")
    giga.get_token()
    GIGA_OK = True
    print("ИИ-модуль подключён.")
except Exception as e: print(f"ИИ: {e}")

def ask_gigachat(prompt):
    if not GIGA_OK: return "Прошу прощения, я сейчас не могу ответить."
    try:
        chat_context.append({"role": "user", "content": prompt})
        msgs = [Messages(role=MessagesRole.SYSTEM,
                          content=SYSTEM_PROMPT + f" Пользователя зовут: {STATE['user_name']}.")]
        for m in chat_context[-10:]:
            role = MessagesRole.USER if m["role"] == "user" else MessagesRole.ASSISTANT
            msgs.append(Messages(role=role, content=m["content"]))
        payload = Chat(messages=msgs, temperature=0.7, max_tokens=200)
        resp = giga.chat(payload)
        ans = resp.choices[0].message.content
        chat_context.append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        print(f"ИИ: {e}")
        return "Произошла ошибка."

# ============================================================
#  МИКРОФОН + WAKE-WORD
# ============================================================
VOICE_REC_OK = False; wake_running = False; wake_active = False
wake_last_activity = 0; wake_last_wake = 0
wake_lock = threading.Lock()
recognizer = None; mic_source_class = None

try:
    import speech_recognition as sr
    import sounddevice as sd
    import numpy as np
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    class _SW:
        def __init__(self, s): self.s = s
        def read(self, size):
            buf, _ = self.s.read(size); return bytes(buf)

    class SDSource(sr.AudioSource):
        SAMPLE_RATE = 16000; SAMPLE_WIDTH = 2; CHANNELS = 1; CHUNK = 1024
        def __init__(self, device=MIC_DEVICE):
            self.device_index = device; self.stream = None
        def __enter__(self):
            s = sd.RawInputStream(samplerate=16000, blocksize=1024,
                                   device=self.device_index, dtype='int16', channels=1)
            s.start(); self.stream = _SW(s); return self
        def __exit__(self, *a):
            if self.stream:
                self.stream.s.stop(); self.stream.s.close()

    mic_source_class = SDSource
    VOICE_REC_OK = True
    print(f"Голосовое распознавание готово (device={MIC_DEVICE}).")
except Exception as e: print(f"Микрофон: {e}")

def wake_listen_loop():
    global wake_active, wake_last_activity, wake_last_wake, wake_running
    print(f"[MIC] Wake-word: {WAKE_WORDS}, микрофон device={MIC_DEVICE}")
    while wake_running:
        if speaking_flag.is_set():
            time.sleep(0.2); continue
        try:
            with mic_source_class() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = recognizer.listen(source, timeout=4, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    check_wake_timeout(); continue
            if speaking_flag.is_set(): continue
            try:
                text = recognizer.recognize_google(audio, language="ru-RU").lower().strip()
            except: continue
            if not text: continue
            print(f"[MIC] {text}")

            found_wake = None
            for w in WAKE_WORDS:
                if w in text: found_wake = w; break
            if not found_wake:
                for p in WAKE_PARTS:
                    if p in text: found_wake = p; break

            with wake_lock:
                if not wake_active:
                    if found_wake:
                        now = time.time()
                        if now - wake_last_wake < WAKE_MIN_INTERVAL: continue
                        wake_last_wake = now
                        wake_active = True
                        wake_last_activity = now
                        root.after(0, on_wake_activated)
                        cleaned = text
                        for w in WAKE_WORDS + WAKE_PARTS:
                            cleaned = cleaned.replace(w, "")
                        cleaned = cleaned.strip(" ,.!?")
                        if len(cleaned) > 2:
                            root.after(0, lambda t=cleaned: process_voice_input(t))
                else:
                    wake_last_activity = time.time()
                    cleaned = text
                    for w in WAKE_WORDS + WAKE_PARTS:
                        cleaned = cleaned.replace(w, "")
                    cleaned = cleaned.strip(" ,.!?")
                    if cleaned:
                        root.after(0, lambda t=cleaned: process_voice_input(t))
                    else:
                        root.after(0, refresh_wake_status)
        except Exception as e:
            print(f"MIC: {e}"); time.sleep(0.5)

def check_wake_timeout():
    global wake_active
    with wake_lock:
        if wake_active and (time.time() - wake_last_activity) > WAKE_ACTIVE_TIMEOUT:
            wake_active = False
            root.after(0, on_wake_sleep)

def on_wake_activated():
    mic_status.config(text="◉ АКТИВЕН", fg=YELLOW)
    set_status("СЛУШАЮ", YELLOW)
    add_message(f"🔔 Активация: {WAKE_ACK}", is_user=False)
    if not play_sound_file("Да сэр.wav"):
        speak(WAKE_ACK)

def on_wake_sleep():
    mic_status.config(text="◉ LIVE", fg=GREEN)
    set_status("ОЖИДАНИЕ", GREEN)

def refresh_wake_status():
    if wake_active:
        mic_status.config(text="◉ АКТИВЕН", fg=YELLOW)
        set_status("СЛУШАЮ", YELLOW)
    else:
        mic_status.config(text="◉ LIVE", fg=GREEN)
        set_status("ОЖИДАНИЕ", GREEN)

def start_wake_listener():
    global wake_running
    if wake_running or not VOICE_REC_OK: return
    wake_running = True
    threading.Thread(target=wake_listen_loop, daemon=True).start()
    mic_status.config(text="◉ LIVE", fg=GREEN); set_status("ОЖИДАНИЕ", GREEN)

def stop_wake_listener():
    global wake_running, wake_active
    wake_running = False; wake_active = False
    mic_status.config(text="◉ OFF", fg=RED); set_status("МИКРОФОН ВЫКЛ", RED)

def toggle_microphone():
    if not VOICE_REC_OK:
        messagebox.showwarning("Микрофон", "Модуль не установлен."); return
    if wake_running: stop_wake_listener()
    else: start_wake_listener()

def process_voice_input(text):
    add_message(text, is_user=True)
    set_status("ОБРАБОТКА", YELLOW)
    result = execute(text)
    add_message(result, is_user=False)
    speak(result)
    global wake_last_activity
    with wake_lock: wake_last_activity = time.time()
    refresh_wake_status()

# ============================================================
#  УТИЛИТЫ
# ============================================================
def match(text, keywords):
    return any(k in text for k in keywords)

SITES = {
    ("ютуб музыка", "youtube music"): ("https://music.youtube.com", "YouTube Music"),
    ("яндекс музыка", "яндекс муз"): ("https://music.yandex.ru", "Яндекс Музыку"),
    ("вк музыка", "вк муз"): ("https://vk.com/audios", "музыку ВК"),
    ("спотифай", "spotify"): ("https://open.spotify.com", "Spotify"),
    ("звук ру", "zvuk.com"): ("https://zvuk.com", "Звук"),
    ("ютуб", "youtube"): ("https://youtube.com", "YouTube"),
    ("вк", "vk", "вконтакте"): ("https://vk.com", "ВКонтакте"),
    ("гугл", "google"): ("https://google.com", "Google"),
    ("яндекс",): ("https://ya.ru", "Яндекс"),
    ("почт", "mail"): ("https://mail.ru", "Mail.ru"),
    ("гитхаб", "github"): ("https://github.com", "GitHub"),
    ("телеграм", "telegram", "тг"): ("https://web.telegram.org", "Telegram"),
    ("ватсап", "whatsapp"): ("https://web.whatsapp.com", "WhatsApp"),
    ("дискорд", "discord"): ("https://discord.com/app", "Discord"),
    ("википеди", "wikipedia", "вики"): ("https://ru.wikipedia.org", "Википедию"),
    ("кинопоиск",): ("https://www.kinopoisk.ru", "Кинопоиск"),
    ("нетфликс", "netflix"): ("https://www.netflix.com", "Netflix"),
    ("твич", "twitch"): ("https://www.twitch.tv", "Twitch"),
    ("тикток", "tiktok"): ("https://www.tiktok.com", "TikTok"),
    ("инстагр", "instagram"): ("https://www.instagram.com", "Instagram"),
    ("озон", "ozon"): ("https://www.ozon.ru", "Ozon"),
    ("вайлдберриз", "wildberries", "вб"): ("https://www.wildberries.ru", "Wildberries"),
    ("авито", "avito"): ("https://www.avito.ru", "Авито"),
    ("алиэкспресс", "aliexpress"): ("https://aliexpress.ru", "AliExpress"),
    ("хабр", "habr"): ("https://habr.com", "Хабр"),
    ("пикабу", "pikabu"): ("https://pikabu.ru", "Pikabu"),
    ("реддит", "reddit"): ("https://www.reddit.com", "Reddit"),
}

# ============================================================
#  АВТООБНАРУЖЕНИЕ
# ============================================================
INSTALLED_APPS = {}

def _normalize(name):
    name = os.path.splitext(name)[0].lower()
    for w in [" (x64)", " (x86)", " (64-bit)", " (32-bit)", "- shortcut", " - ярлык"]:
        name = name.replace(w.lower(), "")
    return name.strip()

def scan_shortcuts():
    global INSTALLED_APPS
    INSTALLED_APPS = {}
    folders = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
        os.path.expanduser(r"~\Desktop"),
    ]
    for folder in folders:
        if not os.path.isdir(folder): continue
        for path in glob.glob(os.path.join(folder, "**", "*.lnk"), recursive=True):
            name = _normalize(os.path.basename(path))
            if name and name not in INSTALLED_APPS:
                INSTALLED_APPS[name] = path
    for sp in [r"C:\Program Files (x86)\Steam\steamapps\common",
               r"C:\Program Files\Steam\steamapps\common",
               r"D:\Steam\steamapps\common", r"D:\SteamLibrary\steamapps\common",
               r"D:\Games", r"C:\Games"]:
        if os.path.isdir(sp):
            for game in os.listdir(sp):
                gp = os.path.join(sp, game)
                if os.path.isdir(gp):
                    for exe in glob.glob(os.path.join(gp, "**", "*.exe"), recursive=True):
                        n = _normalize(os.path.basename(exe))
                        if n not in INSTALLED_APPS:
                            INSTALLED_APPS[n] = exe; break
    print(f"[SCAN] Найдено: {len(INSTALLED_APPS)}")

def find_app(query):
    q = query.lower().strip()
    if q in MY_APPS: return MY_APPS[q]
    for name, path in MY_APPS.items():
        if q in name or name.startswith(q): return path
    if q in INSTALLED_APPS: return INSTALLED_APPS[q]
    for name, path in INSTALLED_APPS.items():
        if name.startswith(q): return path
    for name, path in INSTALLED_APPS.items():
        if q in name: return path
    words = [w for w in q.split() if len(w) > 2]
    for name, path in INSTALLED_APPS.items():
        if any(w in name for w in words): return path
    return None

def close_app(name):
    try:
        import psutil
        killed = 0
        for p in psutil.process_iter(['name']):
            if name.lower() in (p.info['name'] or "").lower():
                try: p.kill(); killed += 1
                except: pass
        return f"Закрыл {killed} процессов" if killed else "Не нашёл"
    except Exception as e: return f"Ошибка: {e}"

# ============================================================
#  СЕРВИСНЫЕ ФУНКЦИИ
# ============================================================
def get_weather(city="Белогорск"):
    try:
        import requests
        url = ("https://api.open-meteo.com/v1/forecast"
               f"?latitude={CITY_LAT}&longitude={CITY_LON}"
               "&current=temperature_2m,relative_humidity_2m,weather_code,"
               "wind_speed_10m,apparent_temperature&timezone=Asia/Yakutsk")
        r = requests.get(url, timeout=8)
        d = r.json()["current"]
        temp = d["temperature_2m"]; feels = d["apparent_temperature"]
        code = d["weather_code"]; wind = d["wind_speed_10m"]
        desc = WEATHER_CODES.get(code, "неизвестно")
        icon = WEATHER_ICONS.get(code, "🌡")
        return f"{icon} {desc}, {temp}°, ощущается {feels}°, ветер {wind} км/ч"
    except: return "Не удалось получить погоду."

def get_weather_full():
    try:
        import requests
        url = ("https://api.open-meteo.com/v1/forecast"
               f"?latitude={CITY_LAT}&longitude={CITY_LON}"
               "&current=temperature_2m,relative_humidity_2m,weather_code,"
               "wind_speed_10m,apparent_temperature&timezone=Asia/Yakutsk")
        r = requests.get(url, timeout=8)
        d = r.json()["current"]
        temp = d["temperature_2m"]; feels = d["apparent_temperature"]
        code = d["weather_code"]; wind = d["wind_speed_10m"]
        desc = WEATHER_CODES.get(code, "?")
        icon = WEATHER_ICONS.get(code, "🌡")
        return icon, f"{temp}°", f"ощущается {feels}°", desc, f"ветер {wind} км/ч"
    except: return "🌡", "--", "", "нет данных", ""

def get_currency():
    try:
        import requests
        d = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=8).json()
        usd = d['Valute']['USD']['Value']; eur = d['Valute']['EUR']['Value']
        cny = d['Valute']['CNY']['Value'] if 'CNY' in d['Valute'] else None
        res = f"Курс ЦБ: доллар {usd:.2f}₽, евро {eur:.2f}₽"
        if cny: res += f", юань {cny:.2f}₽"
        return res
    except: return "Курс недоступен."

def get_crypto():
    try:
        import requests
        d = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=8).json()
        return f"Биткоин ${d['bitcoin']['usd']:,.0f}, Эфириум ${d['ethereum']['usd']:,.0f}"
    except: return "Крипта недоступна."

def volume_set(percent):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        d = AudioUtilities.GetSpeakers()
        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        v = cast(i, POINTER(IAudioEndpointVolume))
        v.SetMasterVolumeLevelScalar(max(0.0, min(1.0, percent / 100.0)), None)
        return f"Громкость {percent}%"
    except: return "Не смог."

def volume_up():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        d = AudioUtilities.GetSpeakers()
        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        v = cast(i, POINTER(IAudioEndpointVolume))
        c = v.GetMasterVolumeLevelScalar()
        v.SetMasterVolumeLevelScalar(min(1.0, c + 0.1), None)
        return f"Громче ({int((c+0.1)*100)}%)"
    except: return "Не смог."

def volume_down():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        d = AudioUtilities.GetSpeakers()
        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        v = cast(i, POINTER(IAudioEndpointVolume))
        c = v.GetMasterVolumeLevelScalar()
        v.SetMasterVolumeLevelScalar(max(0.0, c - 0.1), None)
        return f"Тише ({int((c-0.1)*100)}%)"
    except: return "Не смог."

def volume_mute():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        d = AudioUtilities.GetSpeakers()
        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        v = cast(i, POINTER(IAudioEndpointVolume))
        cur = v.GetMute(); v.SetMute(not cur, None)
        return "Звук выключен" if not cur else "Звук включён"
    except: return "Не смог."

def clipboard_read():
    try:
        import pyperclip
        t = pyperclip.paste()
        if not t: return "Буфер пуст"
        return t[:300]
    except Exception as e: return f"Ошибка: {e}"

def clipboard_write(text):
    try:
        import pyperclip
        pyperclip.copy(text); return "Скопировал"
    except Exception as e: return f"Ошибка: {e}"

def media_key(key):
    try:
        import keyboard
        keys = {"pause": "play/pause media", "next": "next track",
                "prev": "previous track", "stop": "stop media"}
        if key in keys:
            keyboard.send(keys[key])
            return {"pause": "Пауза", "next": "Следующий",
                    "prev": "Предыдущий", "stop": "Стоп"}[key]
    except Exception as e: return f"Ошибка: {e}"
    return "Не смог"

def minimize_all():
    try:
        import keyboard
        keyboard.send('windows+d'); return "Свернул всё"
    except: return "Не смог"

def calc(expr):
    try:
        expr = expr.replace("х", "*").replace("×", "*").replace(":", "/").replace("÷", "/").replace(",", ".")
        expr = re.sub(r"[^0-9+\-*/(). ]", "", expr)
        return f"{expr} = {eval(expr, {'__builtins__': {}}, {})}"
    except: return "Не смог посчитать"

def calc_percent(expr):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*от\s*(\d+(?:\.\d+)?)", expr)
    if m:
        p, total = float(m.group(1)), float(m.group(2))
        return f"{p}% от {total} = {p * total / 100}"
    return None

def currency_convert(expr):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(долларов|доллар|usd|евро|eur|юаней|юань|cny|рублей|руб|rub)\s+в\s+(рубли|rub|доллары|usd|евро|eur)", expr)
    if not m: return None
    try:
        import requests
        d = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=5).json()
        amt = float(m.group(1)); src = m.group(2); dst = m.group(3)
        rates = {"долларов": d['Valute']['USD']['Value'], "доллар": d['Valute']['USD']['Value'],
                 "usd": d['Valute']['USD']['Value'], "евро": d['Valute']['EUR']['Value'],
                 "eur": d['Valute']['EUR']['Value'],
                 "юаней": d['Valute']['CNY']['Value'] if 'CNY' in d['Valute'] else 12,
                 "юань": d['Valute']['CNY']['Value'] if 'CNY' in d['Valute'] else 12,
                 "cny": d['Valute']['CNY']['Value'] if 'CNY' in d['Valute'] else 12,
                 "рублей": 1.0, "руб": 1.0, "rub": 1.0}
        to_rub = amt * rates.get(src, 1)
        if dst in ("рубли", "rub"): return f"{amt} {src} = {to_rub:.2f}₽"
        if dst in ("доллары", "usd"): return f"{amt} {src} = {to_rub / rates['usd']:.2f}$"
        if dst in ("евро", "eur"): return f"{amt} {src} = {to_rub / rates['eur']:.2f}€"
    except: pass
    return None

JOKES = [
    "Программист — это машина по превращению кофе в код.",
    "Есть 10 типов людей: те, кто понимает двоичную систему, и те, кто нет.",
    "99 багов в коде — возьми один, исправь... 127 багов в коде.",
    "Сэр, я бы пошутил, но мои шутки ещё суше, чем мартини.",
]
FACTS = [
    "Осьминоги имеют три сердца.",
    "Мёд не портится.",
    "Первый компьютерный баг был мотыльком в реле.",
    "Белогорск основан в 1860 году.",
]

# ============================================================
#  ОБРАБОТЧИК КОМАНД
# ============================================================
def execute(command):
    cmd = command.lower().strip()

    m = re.search(r"тема\s+(голуб|син|cyan|зелён|зелен|green|красн|red|оранж|orange|фиолет|purple)", cmd)
    if m:
        t = m.group(1)
        if "голуб" in t or "син" in t or "cyan" in t: STATE["theme"] = "cyan"
        elif "зелён" in t or "зелен" in t or "green" in t: STATE["theme"] = "green"
        elif "красн" in t or "red" in t: STATE["theme"] = "red"
        elif "оранж" in t or "orange" in t: STATE["theme"] = "orange"
        elif "фиолет" in t or "purple" in t: STATE["theme"] = "purple"
        save_state()
        root.after(0, lambda: apply_theme(STATE["theme"]))
        return f"Тема переключена: {STATE['theme']}"

    if match(cmd, ["спи", "замолчи", "тихий режим"]):
        STATE["silent_mode"] = True; save_state(); return "Тихий режим."
    if match(cmd, ["проснись", "говори", "вернись"]):
        STATE["silent_mode"] = False; save_state(); return "Я снова с вами."
    if match(cmd, ["выключи голос джарвиса"]):
        STATE["use_jarvis_voice"] = False; save_state(); return "Обычный голос."
    if match(cmd, ["включи голос джарвиса"]):
        STATE["use_jarvis_voice"] = True; save_state(); return "Голос Джарвиса активирован."
    if match(cmd, ["зови меня "]):
        n = re.sub(r".*зови меня\s+", "", cmd).strip()
        if n:
            STATE["user_name"] = n; save_state()
            return f"Хорошо, {n}."

    if match(cmd, ["время", "который час"]):
        return f"Сейчас {datetime.datetime.now().strftime('%H:%M')}"
    if match(cmd, ["дата", "какой сегодня"]):
        return f"Сегодня {datetime.datetime.now().strftime('%d.%m.%Y')}"
    if match(cmd, ["день недели"]):
        days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        return f"Сегодня {days[datetime.datetime.now().weekday()]}"

    m = re.search(r"(?:добавь задачу|напомни|поставь напоминание)\s+(.+)", cmd)
    if m:
        full = m.group(1).strip()
        dt = parse_task_time(full)
        text = re.sub(r"\b(в|на|через|завтра|\d{1,2}[\.:]\d{2}(?:\.\d{4})?|\d{1,2}\.\d{1,2}(?:\.\d{4})?|\d+)\b.*", "", full).strip()
        text = re.sub(r"^(?:на|в|через|завтра)\s+", "", text).strip(" ,.")
        if not dt:
            return "Не понял время, сэр. Скажите: добавь задачу в 18:00 купить хлеб"
        if not text: text = "Задача"
        add_task(text, dt)
        return f"Задача добавлена: {text} — {dt.strftime('%d.%m в %H:%M')}"

    if match(cmd, ["покажи задачи", "мои задачи", "список задач"]):
        with tasks_lock:
            active = [t for t in TASKS if not t.get("done")]
        if not active: return "Нет активных задач"
        lines = []
        for t in active:
            try:
                tt = datetime.datetime.fromisoformat(t["time"])
                lines.append(f"{t['id']}. {t['text']} — {tt.strftime('%d.%m %H:%M')}")
            except: pass
        return "Задачи: " + "; ".join(lines)

    m = re.search(r"удали задачу\s+(\d+)", cmd)
    if m:
        tid = int(m.group(1))
        with tasks_lock:
            before = len(TASKS)
            TASKS[:] = [t for t in TASKS if t["id"] != tid]
            removed = before - len(TASKS); save_tasks(TASKS)
        return f"Удалил задачу {tid}" if removed else f"Задачи {tid} нет"

    if match(cmd, ["очисти все задачи", "удали все задачи"]):
        with tasks_lock:
            n = len(TASKS); TASKS.clear(); save_tasks(TASKS)
        return f"Удалил {n} задач"

    m = re.search(r"таймер\s+(?:на\s+)?(\d+)\s*(минут|секунд|час)", cmd)
    if m:
        n = int(m.group(1)); u = m.group(2)
        sec = n * 60 if "минут" in u else (n * 3600 if "час" in u else n)
        add_timer(sec, "Таймер")
        return f"Таймер на {n} {u} запущен"
    m = re.search(r"напомни\s+(.+?)\s+через\s+(\d+)\s*(минут|секунд|час)", cmd)
    if m:
        text, n, u = m.group(1), int(m.group(2)), m.group(3)
        sec = n * 60 if "минут" in u else (n * 3600 if "час" in u else n)
        add_timer(sec, f"Напоминание: {text}")
        return f"Напомню через {n} {u}"
    if match(cmd, ["отмени таймеры", "отмени все таймеры"]):
        n = cancel_all_timers()
        return f"Отменил {n} таймеров" if n else "Нет активных таймеров"

    if match(cmd, ["погод"]): return get_weather()
    if match(cmd, ["курс", "валют"]): return get_currency()
    if match(cmd, ["биткоин", "крипт", "эфир"]): return get_crypto()
    if match(cmd, ["шутк", "анекдот"]): return random.choice(JOKES)
    if match(cmd, ["факт"]): return random.choice(FACTS)

    if match(cmd, ["брось кубик", "кубик"]): return f"Выпало {random.randint(1, 6)}"
    if match(cmd, ["орёл или решка", "монетк"]): return random.choice(["Орёл", "Решка"])
    m = re.search(r"случайное число от (\d+) до (\d+)", cmd)
    if m: return f"{random.randint(int(m.group(1)), int(m.group(2)))}"

    if match(cmd, ["прочитай буфер", "что в буфере"]): return clipboard_read()
    if match(cmd, ["скопируй ", "запиши в буфер "]):
        text = re.sub(r".*?(?:скопируй|запиши в буфер)\s+", "", cmd, count=1).strip()
        return clipboard_write(text)

    if match(cmd, ["пауза", "поставь паузу", "продолжи"]): return media_key("pause")
    if match(cmd, ["следующий трек", "следующая песня", "дальше"]): return media_key("next")
    if match(cmd, ["предыдущий трек", "предыдущая песня"]): return media_key("prev")
    if match(cmd, ["сверни всё", "покажи рабочий стол"]): return minimize_all()

    if match(cmd, ["закрой все браузеры", "закрой браузеры"]):
        total = 0
        for n in ["chrome", "firefox", "opera", "edge", "msedge", "brave"]:
            r = close_app(n)
            m2 = re.search(r"(\d+)", r)
            if m2: total += int(m2.group(1))
        return f"Закрыл {total} браузерных процессов"

    if match(cmd, ["обнови список программ", "просканируй программы"]):
        scan_shortcuts(); return f"Нашёл {len(INSTALLED_APPS)} программ"

    for keywords, (url, name) in sorted(SITES.items(), key=lambda x: -max(len(k) for k in x[0])):
        if any(k in cmd for k in keywords):
            webbrowser.open(url); return f"Открываю {name}"

    m = re.search(r"открой (?:результат\s+|ссылку\s+)?(\d+|перв\w*|втор\w*|треть\w*)", cmd)
    if m:
        idx_str = m.group(1)
        idx_map = {"перв": 1, "втор": 2, "треть": 3}
        idx = None
        if idx_str.isdigit(): idx = int(idx_str) - 1
        else:
            for k, v in idx_map.items():
                if k in idx_str: idx = v - 1; break
        if idx is not None and 0 <= idx < len(last_search_results):
            url = last_search_results[idx]["url"]
            webbrowser.open(url)
            return f"Открываю: {last_search_results[idx]['title'][:50]}"
        return "Такого результата нет. Сначала сделай поиск."

    m = re.search(r"(?:найди|погугли|поищи|загугли)\s+(?:в\s+гугле\s+|в\s+интернете\s+|на\s+ютубе\s+)?(.+)", cmd)
    if m:
        q = m.group(1).strip()
        if "ютуб" in cmd or "youtube" in cmd:
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
            return f"Открываю YouTube: {q}"
        if "гугл" in cmd or "google" in cmd:
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
            return f"Открываю Google: {q}"
        results = search_duckduckgo(q, max_results=3)
        return format_search_results(q, results)

    r = currency_convert(cmd)
    if r: return r
    r = calc_percent(cmd)
    if r: return r

    m = re.search(r"(?:посчитай|сколько будет)\s+(.+)", cmd)
    if m: return calc(m.group(1))

    m = re.search(r"(?:закрой|убей|заверши)\s+(.+)", cmd)
    if m:
        n = m.group(1).strip()
        if "компьютер" not in n and "пк" not in n:
            return close_app(n)

    m = re.search(r"(?:открой|запусти|включи|вруби)\s+(?:прогу\s+|программу\s+|игру\s+)?(.+)", cmd)
    if m:
        q = m.group(1).strip()
        if "." in q and " " not in q:
            url = q if q.startswith("http") else "https://" + q
            webbrowser.open(url); return f"Открываю {q}"
        path = find_app(q)
        if path:
            try: os.startfile(path); return f"Запускаю {q}"
            except Exception as e:
                print(f"Ошибка: {e}"); return f"Не смог запустить {q}"
        else: return f"Не нашёл «{q}»."

    if match(cmd, ["блокнот", "notepad"]):
        subprocess.Popen("notepad.exe"); return "Блокнот"
    if match(cmd, ["калькулятор"]):
        subprocess.Popen("calc.exe"); return "Калькулятор"
    if match(cmd, ["проводник", "папки"]):
        subprocess.Popen("explorer.exe"); return "Проводник"
    if match(cmd, ["диспетчер задач"]):
        subprocess.Popen("taskmgr.exe"); return "Диспетчер"

    m = re.search(r"громкость\s+(?:на\s+)?(\d+)\s*%?", cmd)
    if m: return volume_set(int(m.group(1)))
    if match(cmd, ["громче"]): return volume_up()
    if match(cmd, ["тише"]): return volume_down()
    if match(cmd, ["выключи звук", "mute"]): return volume_mute()

    if match(cmd, ["выключи компьютер", "shutdown"]):
        os.system("shutdown /s /t 30"); return "Выключаю через 30 секунд"
    if match(cmd, ["перезагрузи", "reboot"]):
        os.system("shutdown /r /t 30"); return "Перезагружаю через 30 секунд"
    if match(cmd, ["отмена выключения", "отмени"]):
        os.system("shutdown /a"); return "Отменил"
    if match(cmd, ["заблокируй"]):
        os.system("rundll32.exe user32.dll,LockWorkStation"); return "Блокирую"
    if match(cmd, ["спать", "сон пк"]):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0"); return "Сон"

    if match(cmd, ["скриншот", "скрин"]):
        try:
            from PIL import ImageGrab
            f = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ImageGrab.grab().save(f)
            return f"Скриншот: {f}"
        except Exception as e: return f"Ошибка: {e}"

    if match(cmd, ["диск", "место"]):
        try:
            import psutil
            d = psutil.disk_usage('C:')
            return f"Диск C: {d.free/(1024**3):.0f} ГБ свободно"
        except: return "Установи psutil"
    if match(cmd, ["память", "озу"]):
        try:
            import psutil
            vm = psutil.virtual_memory()
            return f"ОЗУ: {vm.available/(1024**3):.1f} ГБ свободно"
        except: return "Установи psutil"
    if match(cmd, ["процессор", "cpu"]):
        try:
            import psutil
            return f"CPU: {psutil.cpu_percent(interval=1):.0f}%"
        except: return "Установи psutil"

    if match(cmd, ["запомни "]):
        note = re.sub(r".*запомни\s+", "", cmd).strip()
        STATE["notes"].append({"time": datetime.datetime.now().isoformat(), "text": note})
        save_state(); return "Записал"
    if match(cmd, ["покажи заметки"]):
        if not STATE["notes"]: return "Заметок нет"
        return "Заметки: " + "; ".join([n["text"] for n in STATE["notes"][-5:]])

    if match(cmd, ["привет", "здравствуй", "добрый день"]):
        h = datetime.datetime.now().hour
        if h < 6: g = "Доброй ночи"
        elif h < 12: g = "Доброе утро"
        elif h < 18: g = "Добрый день"
        else: g = "Добрый вечер"
        return f"{g}, {STATE['user_name']}."
    if match(cmd, ["как дела", "как ты"]):
        return random.choice(["Все системы работают штатно.", "Оптимальный режим."])
    if match(cmd, ["спасибо"]):
        return random.choice(["Всегда к вашим услугам.", "Рад помочь."])
    if match(cmd, ["кто ты", "представься"]):
        return "Я Джарвис, ваш ассистент."
    if match(cmd, ["что умеешь", "помощь", "help"]):
        return (f"Умею: поиск в интернете, сайты, программы ({len(INSTALLED_APPS)}), "
                "задачи с временем, таймеры, погода, курсы, громкость, буфер, "
                "медиа, скриншоты, темы, заметки.")

    return ask_gigachat(command)

# ============================================================
#  UI
# ============================================================
theme = THEMES[STATE.get("theme", "cyan")]
BG = "#000a0d"; PANEL_BG = "#001419"; PANEL_LINE = "#00323d"
TEXT_DIM = "#4a7a8a"; TEXT_MAIN = "#a0d8e6"
GREEN = "#00ff88"; YELLOW = "#ffaa00"; RED = "#ff3344"
ACCENT = theme["accent"]; ACCENT_DIM = theme["dim"]; ACCENT_GLOW = theme["glow"]
USER_COLOR = theme["user"]; USER_DIM = theme["user_dim"]
FONT_MONO = "Consolas"

root = tk.Tk()
root.title("J.A.R.V.I.S.")
root.geometry("1400x850")
root.configure(bg=BG)
root.minsize(1200, 700)

top_bar = tk.Frame(root, bg=BG, height=46)
top_bar.pack(fill="x", side="top"); top_bar.pack_propagate(False)
tk.Label(top_bar, text="◈ SYSTEM", bg=BG, fg=ACCENT_DIM,
         font=(FONT_MONO, 9, "bold")).pack(side="left", padx=20, pady=15)
tk.Label(top_bar, text="◈ CORE", bg=BG, fg=ACCENT_DIM,
         font=(FONT_MONO, 9, "bold")).pack(side="left")

title_cv = tk.Canvas(top_bar, bg=BG, height=46, highlightthickness=0)
title_cv.pack(side="left", expand=True, fill="both")
def draw_title(e=None):
    title_cv.delete("all")
    w = title_cv.winfo_width(); cx = w // 2
    title_cv.create_text(cx, 24, text="J.A.R.V.I.S.", fill="#001a20", font=(FONT_MONO, 16, "bold"))
    title_cv.create_text(cx+1, 23, text="J.A.R.V.I.S.", fill=ACCENT_GLOW, font=(FONT_MONO, 16, "bold"))
    title_cv.create_text(cx, 22, text="J.A.R.V.I.S.", fill=ACCENT, font=(FONT_MONO, 16, "bold"))
    title_cv.create_text(cx, 38, text="Just A Rather Very Intelligent System", fill=ACCENT_DIM, font=(FONT_MONO, 7))
title_cv.bind("<Configure>", draw_title)

right_top = tk.Frame(top_bar, bg=BG)
right_top.pack(side="right", padx=20, pady=15)
online_dot = tk.Label(right_top, text="●", bg=BG, fg=GREEN, font=(FONT_MONO, 10))
online_dot.pack(side="left")
tk.Label(right_top, text=" ONLINE", bg=BG, fg=GREEN, font=(FONT_MONO, 9, "bold")).pack(side="left")

sep_cv = tk.Canvas(root, height=3, bg=BG, highlightthickness=0)
sep_cv.pack(fill="x")
def draw_sep(e=None):
    sep_cv.delete("all")
    w = sep_cv.winfo_width()
    for i in range(w):
        t = abs(i - w/2) / (w/2)
        r = int(0x00 + (0x00 - 0x00) * t)
        g = int(0x6b + (0x00 - 0x6b) * t)
        b = int(0x7a + (0x10 - 0x7a) * t)
        sep_cv.create_line(i, 0, i, 3, fill=f"#{r:02x}{g:02x}{b:02x}")
sep_cv.bind("<Configure>", draw_sep)

body = tk.Frame(root, bg=BG); body.pack(fill="both", expand=True)

left_outer = tk.Frame(body, bg=PANEL_LINE, width=290)
left_outer.pack(side="left", fill="y", padx=(6, 0), pady=6)
left_outer.pack_propagate(False)
left = tk.Frame(left_outer, bg=PANEL_BG)
left.pack(fill="both", expand=True, padx=1, pady=1)

left_corner_cv = tk.Canvas(left, width=16, height=16, bg=PANEL_BG, highlightthickness=0)
left_corner_cv.place(x=2, y=2)
left_corner_cv.create_line(0, 0, 16, 0, fill=ACCENT, width=2)
left_corner_cv.create_line(0, 0, 0, 16, fill=ACCENT, width=2)

left_corner_bl = tk.Canvas(left, width=16, height=16, bg=PANEL_BG, highlightthickness=0)
left_corner_bl.place(x=2, rely=1.0, y=-18)
left_corner_bl.create_line(0, 16, 16, 16, fill=ACCENT, width=2)
left_corner_bl.create_line(0, 0, 0, 16, fill=ACCENT, width=2)

def section(parent, title):
    f = tk.Frame(parent, bg=PANEL_BG); f.pack(fill="x", padx=16, pady=(14, 4))
    tk.Label(f, text="▸", bg=PANEL_BG, fg=ACCENT,
             font=(FONT_MONO, 10, "bold")).pack(side="left")
    tk.Label(f, text=f" {title}", bg=PANEL_BG, fg=ACCENT,
             font=(FONT_MONO, 9, "bold")).pack(side="left")
    tk.Frame(parent, bg=PANEL_LINE, height=1).pack(fill="x", padx=16, pady=(0, 8))

section(left, "TIME")
time_big = tk.Label(left, text="00:00", bg=PANEL_BG, fg=ACCENT,
                    font=(FONT_MONO, 36, "bold"), anchor="w")
time_big.pack(fill="x", padx=16)
time_row = tk.Frame(left, bg=PANEL_BG); time_row.pack(fill="x", padx=16)
seconds_lbl = tk.Label(time_row, text=":00", bg=PANEL_BG, fg=ACCENT_DIM,
                        font=(FONT_MONO, 14, "bold"))
seconds_lbl.pack(side="left")
date_small = tk.Label(time_row, text="", bg=PANEL_BG, fg=TEXT_DIM,
                      font=(FONT_MONO, 8), anchor="e")
date_small.pack(side="right", fill="x", expand=True)

section(left, "ПОГОДА · БЕЛОГОРСК")
weather_icon_lbl = tk.Label(left, text="🌡", bg=PANEL_BG, fg=ACCENT,
                             font=("Segoe UI", 32), anchor="w")
weather_icon_lbl.pack(fill="x", padx=16)
weather_temp_lbl = tk.Label(left, text="--°", bg=PANEL_BG, fg=TEXT_MAIN,
                             font=(FONT_MONO, 20, "bold"), anchor="w")
weather_temp_lbl.pack(fill="x", padx=16)
weather_feels_lbl = tk.Label(left, text="", bg=PANEL_BG, fg=TEXT_DIM,
                              font=(FONT_MONO, 8), anchor="w")
weather_feels_lbl.pack(fill="x", padx=16)
weather_desc_lbl = tk.Label(left, text="", bg=PANEL_BG, fg=TEXT_MAIN,
                             font=(FONT_MONO, 9), anchor="w", wraplength=240, justify="left")
weather_desc_lbl.pack(fill="x", padx=16)
weather_wind_lbl = tk.Label(left, text="", bg=PANEL_BG, fg=TEXT_DIM,
                             font=(FONT_MONO, 8), anchor="w")
weather_wind_lbl.pack(fill="x", padx=16)

section(left, "STATUS")
def make_bar(parent, label):
    row = tk.Frame(parent, bg=PANEL_BG); row.pack(fill="x", padx=16, pady=3)
    tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT_DIM,
             font=(FONT_MONO, 8), width=5, anchor="w").pack(side="left")
    cv = tk.Canvas(row, height=10, bg=PANEL_BG, highlightthickness=0)
    cv.pack(side="left", fill="x", expand=True, padx=(6, 6))
    vl = tk.Label(row, text="0%", bg=PANEL_BG, fg=ACCENT,
                  font=(FONT_MONO, 8), width=4, anchor="e")
    vl.pack(side="right")
    return cv, vl

cpu_cv, cpu_val = make_bar(left, "CPU")
ram_cv, ram_val = make_bar(left, "RAM")
disk_cv, disk_val = make_bar(left, "DISK")

def draw_bar(cv, pct, color=None):
    if color is None: color = ACCENT
    cv.delete("all")
    w = cv.winfo_width()
    if w <= 1: w = 150
    h = 10; segs = 22; gap = 2
    sw = (w - (segs-1)*gap) / segs
    filled = int(segs * pct / 100)
    for i in range(segs):
        x0 = i * (sw + gap); x1 = x0 + sw
        c = color if i < filled else "#0d1e26"
        cv.create_rectangle(x0, 0, x1, h, fill=c, outline="")

def update_stats():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        dsk = psutil.disk_usage('C:').percent
        cpu_val.config(text=f"{cpu:.0f}%"); ram_val.config(text=f"{ram:.0f}%"); disk_val.config(text=f"{dsk:.0f}%")
        draw_bar(cpu_cv, cpu, ACCENT if cpu < 70 else YELLOW)
        draw_bar(ram_cv, ram, ACCENT if ram < 70 else YELLOW)
        draw_bar(disk_cv, dsk, ACCENT if dsk < 80 else YELLOW)
    except: pass
    root.after(2000, update_stats)

def update_weather():
    def fetch():
        icon, temp, feels, desc, wind = get_weather_full()
        def upd():
            weather_icon_lbl.config(text=icon)
            weather_temp_lbl.config(text=temp)
            weather_feels_lbl.config(text=feels)
            weather_desc_lbl.config(text=desc)
            weather_wind_lbl.config(text=wind)
        root.after(0, upd)
    threading.Thread(target=fetch, daemon=True).start()
    root.after(900000, update_weather)

section(left, "TASKS")
tasks_lbl = tk.Label(left, text="пусто", bg=PANEL_BG, fg=TEXT_MAIN,
                     font=(FONT_MONO, 8), anchor="w", justify="left", wraplength=240)
tasks_lbl.pack(fill="x", padx=16)

def refresh_tasks():
    with tasks_lock:
        active = [t for t in TASKS if not t.get("done")]
    if not active:
        tasks_lbl.config(text="пусто"); return
    lines = []
    for t in active[-5:]:
        try:
            tt = datetime.datetime.fromisoformat(t["time"])
            lines.append(f"• {tt.strftime('%d.%m %H:%M')} — {t['text']}")
        except: pass
    tasks_lbl.config(text="\n".join(lines) if lines else "пусто")

# CENTER
center = tk.Frame(body, bg=BG); center.pack(side="left", fill="both", expand=True)
RS = 460
reactor = tk.Canvas(center, width=RS, height=RS, bg=BG, highlightthickness=0)
reactor.pack(pady=(24, 4))
CX = CY = RS // 2

for r, c, w in [(225, "#001820", 1), (215, "#002a35", 1), (205, ACCENT_GLOW, 2)]:
    reactor.create_oval(CX-r, CY-r, CX+r, CY+r, outline=c, width=w)

reactor.create_oval(CX-195, CY-195, CX+195, CY+195, outline=ACCENT_DIM, width=1)
reactor.create_oval(CX-185, CY-185, CX+185, CY+185, outline=ACCENT_GLOW, width=1)

for i in range(72):
    ang = math.radians(i * 5)
    r1 = 200
    r2 = 210 if i % 6 == 0 else 205
    c = ACCENT if i % 6 == 0 else ACCENT_DIM
    w = 2 if i % 6 == 0 else 1
    reactor.create_line(CX+r1*math.cos(ang), CY+r1*math.sin(ang),
                        CX+r2*math.cos(ang), CY+r2*math.sin(ang),
                        fill=c, width=w)

ring_arcs = []
for i, (ext, off) in enumerate([(100, 0), (60, 120), (35, 240)]):
    color = ACCENT if i % 2 == 0 else ACCENT_DIM
    w = 3 if i == 0 else 2
    a = reactor.create_arc(CX-160, CY-160, CX+160, CY+160,
                            start=off, extent=ext, outline=color,
                            width=w, style="arc")
    ring_arcs.append(a)

sweep_glow = reactor.create_line(CX, CY, CX, CY-155, fill=ACCENT_GLOW, width=6)
sweep_line = reactor.create_line(CX, CY, CX, CY-155, fill=ACCENT, width=2)

reactor.create_oval(CX-115, CY-115, CX+115, CY+115, outline=ACCENT, width=2)
reactor.create_oval(CX-105, CY-105, CX+105, CY+105, outline=ACCENT_GLOW, width=1)
core_glow = reactor.create_oval(CX-95, CY-95, CX+95, CY+95,
                                 fill="#001a24", outline=ACCENT_DIM, width=1)
reactor.create_oval(CX-70, CY-70, CX+70, CY+70,
                    fill="#002028", outline=ACCENT_GLOW, width=1)
pulse_ring = reactor.create_oval(CX-130, CY-130, CX+130, CY+130,
                                  outline=ACCENT_GLOW, width=1)

particles = []
for _ in range(80):
    a = random.uniform(0, 2*math.pi); r = random.uniform(5, 90)
    px, py = CX + r*math.cos(a), CY + r*math.sin(a)
    size = random.choice([1, 2, 2, 3])
    p = reactor.create_oval(px, py, px+size, py+size, fill=ACCENT, outline="")
    particles.append({"id": p, "a": a, "r": r, "sp": random.uniform(0.2, 1.8), "size": size})

title_bot = tk.Canvas(center, bg=BG, height=70, highlightthickness=0)
title_bot.pack(fill="x")
def draw_bot(e=None):
    title_bot.delete("all")
    w = title_bot.winfo_width(); cx = w//2
    title_bot.create_text(cx, 32, text="J A R V I S", fill="#001a20", font=(FONT_MONO, 32, "bold"))
    title_bot.create_text(cx+1, 31, text="J A R V I S", fill=ACCENT_GLOW, font=(FONT_MONO, 32, "bold"))
    title_bot.create_text(cx, 30, text="J A R V I S", fill=ACCENT, font=(FONT_MONO, 32, "bold"))
title_bot.bind("<Configure>", draw_bot)

bc = tk.Frame(center, bg=BG); bc.pack(pady=(6, 0))
mic_status = tk.Label(bc, text="◉ LIVE", bg=BG, fg=GREEN, font=(FONT_MONO, 10, "bold"))
mic_status.pack(side="left", padx=12)
tk.Label(bc, text="│", bg=BG, fg=ACCENT_DIM, font=(FONT_MONO, 10)).pack(side="left")
pause_lbl = tk.Label(bc, text="MIC", bg=BG, fg=TEXT_DIM, font=(FONT_MONO, 10), cursor="hand2")
pause_lbl.pack(side="left", padx=12)
pause_lbl.bind("<Button-1>", lambda e: toggle_microphone())
pause_lbl.bind("<Enter>", lambda e: pause_lbl.config(fg=ACCENT))
pause_lbl.bind("<Leave>", lambda e: pause_lbl.config(fg=TEXT_DIM))
tk.Label(bc, text="│", bg=BG, fg=ACCENT_DIM, font=(FONT_MONO, 10)).pack(side="left")
sd_lbl = tk.Label(bc, text="⏻ SHUTDOWN", bg=BG, fg=RED, font=(FONT_MONO, 10), cursor="hand2")
sd_lbl.pack(side="left", padx=12)
sd_lbl.bind("<Button-1>", lambda e: root.destroy())

sbar = tk.Frame(center, bg=BG); sbar.pack(pady=(16, 0))
sdot = tk.Label(sbar, text="●", bg=BG, fg=GREEN, font=(FONT_MONO, 12))
sdot.pack(side="left", padx=(0, 6))
stext = tk.Label(sbar, text="ОЖИДАНИЕ", bg=BG, fg=GREEN, font=(FONT_MONO, 9, "bold"))
stext.pack(side="left")

def set_status(t, c=GREEN):
    stext.config(text=t, fg=c); sdot.config(fg=c)

pulse_state = [0]
def pulse_dot_tick():
    if stext.cget("fg") == YELLOW:
        shades = ["#ffcc00", "#ff9900", "#ff6600", "#ff9900"]
        sdot.config(fg=shades[pulse_state[0] % 4])
        pulse_state[0] += 1
        root.after(200, pulse_dot_tick)
    else:
        sdot.config(fg=stext.cget("fg"))
        root.after(500, pulse_dot_tick)

# RIGHT
right_outer = tk.Frame(body, bg=PANEL_LINE, width=440)
right_outer.pack(side="right", fill="y", padx=(0, 6), pady=6)
right_outer.pack_propagate(False)
right = tk.Frame(right_outer, bg=PANEL_BG)
right.pack(fill="both", expand=True, padx=1, pady=1)

rc_tr = tk.Canvas(right, width=16, height=16, bg=PANEL_BG, highlightthickness=0)
rc_tr.place(relx=1.0, x=-18, y=2)
rc_tr.create_line(0, 0, 16, 0, fill=ACCENT, width=2)
rc_tr.create_line(16, 0, 16, 16, fill=ACCENT, width=2)

rc_br = tk.Canvas(right, width=16, height=16, bg=PANEL_BG, highlightthickness=0)
rc_br.place(relx=1.0, x=-18, rely=1.0, y=-18)
rc_br.create_line(16, 0, 16, 16, fill=ACCENT, width=2)
rc_br.create_line(0, 16, 16, 16, fill=ACCENT, width=2)

section(right, "CONVERSATION")

chat_frame = tk.Frame(right, bg=PANEL_BG)
chat_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

sb = tk.Scrollbar(chat_frame, bg=PANEL_BG, troughcolor=PANEL_BG,
                  activebackground=ACCENT_DIM, bd=0, highlightthickness=0, width=8)
sb.pack(side="right", fill="y")

chat = tk.Text(chat_frame, bg=PANEL_BG, fg=TEXT_MAIN, font=(FONT_MONO, 10),
               state="disabled", wrap="word", bd=0, highlightthickness=0,
               padx=8, pady=8, yscrollcommand=sb.set, cursor="arrow",
               spacing1=2, spacing3=8)
chat.pack(side="left", fill="both", expand=True)
sb.config(command=chat.yview)

chat.tag_configure("time", foreground="#3a5a6a", font=(FONT_MONO, 8))
chat.tag_configure("jarvis_name", foreground=ACCENT, font=(FONT_MONO, 10, "bold"))
chat.tag_configure("user_name", foreground=USER_COLOR, font=(FONT_MONO, 10, "bold"))
chat.tag_configure("msg", foreground=TEXT_MAIN, font=(FONT_MONO, 10))
chat.tag_configure("bar_j", foreground=ACCENT)
chat.tag_configure("bar_u", foreground=USER_COLOR)
chat.tag_configure("sep", foreground=ACCENT_GLOW)
chat.tag_configure("avatar_j", foreground=ACCENT, font=(FONT_MONO, 12))
chat.tag_configure("avatar_u", foreground=USER_COLOR, font=(FONT_MONO, 12))

def add_message(text, is_user=False):
    chat.config(state="normal")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    if is_user:
        name_tag = "user_name"; avatar_tag = "avatar_u"
        who = "ВЫ"; avatar = "▶"
    else:
        name_tag = "jarvis_name"; avatar_tag = "avatar_j"
        who = "JARVIS"; avatar = "◉"

    chat.insert(tk.END, f"{avatar} ", avatar_tag)
    chat.insert(tk.END, f"[{now}] ", "time")
    chat.insert(tk.END, f"{who}\n", name_tag)
    chat.insert(tk.END, f"   {text}\n", "msg")
    chat.insert(tk.END, "\n", "sep")

    chat.config(state="disabled")
    chat.see(tk.END)
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {who}: {text}\n")
    except: pass

arc1 = arc2 = arc3 = 0; sweep_a = 0
pulse = 0; p_dir = 1
pulse_ring_a = 0; pulse_ring_dir = 1

def animate():
    global arc1, arc2, arc3, sweep_a, pulse, p_dir, pulse_ring_a, pulse_ring_dir

    arc1 = (arc1 + 3) % 360; arc2 = (arc2 - 5) % 360; arc3 = (arc3 + 7) % 360
    reactor.itemconfig(ring_arcs[0], start=arc1, extent=100)
    reactor.itemconfig(ring_arcs[1], start=arc2, extent=60)
    reactor.itemconfig(ring_arcs[2], start=arc3, extent=35)

    sweep_a = (sweep_a + 4) % 360
    rad = math.radians(sweep_a); rad2 = math.radians(sweep_a - 20)
    reactor.coords(sweep_line, CX, CY, CX+155*math.cos(rad), CY+155*math.sin(rad))
    reactor.coords(sweep_glow, CX, CY, CX+155*math.cos(rad2), CY+155*math.sin(rad2))

    pulse += p_dir * 0.04
    if pulse >= 1: pulse, p_dir = 1, -1
    elif pulse <= 0: pulse, p_dir = 0, 1
    r = 95 + int(pulse * 5)
    reactor.coords(core_glow, CX-r, CY-r, CX+r, CY+r)
    shades = ["#001a24", "#00242e", "#002e3a", "#003a48"]
    reactor.itemconfig(core_glow, fill=shades[int(pulse * 3)])

    pulse_ring_a += pulse_ring_dir * 0.03
    if pulse_ring_a >= 1: pulse_ring_a, pulse_ring_dir = 1, -1
    elif pulse_ring_a <= 0: pulse_ring_a, pulse_ring_dir = 0, 1
    pr = 130 + int(pulse_ring_a * 8)
    reactor.coords(pulse_ring, CX-pr, CY-pr, CX+pr, CY+pr)
    pr_shades = ["#001a24", "#00323d", "#005560", "#008090"]
    reactor.itemconfig(pulse_ring, outline=pr_shades[int(pulse_ring_a * 3)])

    for p in particles:
        p["a"] += p["sp"] * 0.04
        px = CX + p["r"]*math.cos(p["a"])
        py = CY + p["r"]*math.sin(p["a"])
        reactor.coords(p["id"], px, py, px+p["size"], py+p["size"])

    root.after(40, animate)

def tick():
    n = datetime.datetime.now()
    time_big.config(text=n.strftime("%H:%M"))
    seconds_lbl.config(text=n.strftime(":%S"))
    months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    date_small.config(text=f"{n.day:02d} {months[n.month-1]} {n.year}")
    root.after(1000, tick)

def apply_theme(theme_name):
    global theme, ACCENT, ACCENT_DIM, ACCENT_GLOW, USER_COLOR, USER_DIM
    theme = THEMES.get(theme_name, THEMES["cyan"])
    ACCENT = theme["accent"]; ACCENT_DIM = theme["dim"]; ACCENT_GLOW = theme["glow"]
    USER_COLOR = theme["user"]; USER_DIM = theme["user_dim"]
    try:
        for i, arc in enumerate(ring_arcs):
            reactor.itemconfig(arc, outline=ACCENT if i%2==0 else ACCENT_DIM)
        reactor.itemconfig(sweep_line, fill=ACCENT)
        reactor.itemconfig(sweep_glow, fill=ACCENT_GLOW)
        reactor.itemconfig(pulse_ring, outline=ACCENT_GLOW)
        for p in particles:
            reactor.itemconfig(p["id"], fill=ACCENT)
    except: pass
    try:
        chat.tag_configure("jarvis_name", foreground=ACCENT)
        chat.tag_configure("user_name", foreground=USER_COLOR)
        chat.tag_configure("bar_j", foreground=ACCENT)
        chat.tag_configure("bar_u", foreground=USER_COLOR)
        chat.tag_configure("avatar_j", foreground=ACCENT)
        chat.tag_configure("avatar_u", foreground=USER_COLOR)
    except: pass
    root.after(50, draw_title)
    root.after(50, draw_bot)
    root.after(50, draw_sep)

input_outer = tk.Frame(root, bg=PANEL_LINE, height=64)
input_outer.pack(fill="x", side="bottom", padx=6, pady=(0, 6))
input_outer.pack_propagate(False)
ibar = tk.Frame(input_outer, bg=PANEL_BG)
ibar.pack(fill="both", expand=True, padx=1, pady=1)

input_top_cv = tk.Canvas(ibar, height=2, bg=PANEL_BG, highlightthickness=0)
input_top_cv.pack(fill="x", side="top")
def draw_input_top(e=None):
    input_top_cv.delete("all")
    w = input_top_cv.winfo_width()
    for i in range(w):
        t = abs(i - w/2) / (w/2)
        r = int(0x00 + (0x00 - 0x00) * t)
        g = int(0x6b + (0x00 - 0x6b) * t)
        b = int(0x7a + (0x10 - 0x7a) * t)
        input_top_cv.create_line(i, 0, i, 2, fill=f"#{r:02x}{g:02x}{b:02x}")
input_top_cv.bind("<Configure>", draw_input_top)

prompt = tk.Label(ibar, text="▸", bg=PANEL_BG, fg=ACCENT,
                  font=(FONT_MONO, 18, "bold"))
prompt.pack(side="left", padx=(24, 12))

entry = tk.Entry(ibar, bg=PANEL_BG, fg=TEXT_MAIN, font=(FONT_MONO, 12),
                 insertbackground=ACCENT, bd=0, highlightthickness=0)
entry.pack(side="left", fill="both", expand=True, pady=14)

def on_enter(e=None):
    cmd = entry.get().strip()
    if not cmd: return
    entry.delete(0, tk.END)
    add_message(cmd, is_user=True)
    set_status("ОБРАБОТКА", YELLOW)

    def process():
        res = execute(cmd)
        add_message(res, is_user=False)
        if not wake_active: set_status("ОЖИДАНИЕ", GREEN)
        else: set_status("СЛУШАЮ", YELLOW)
        speak(res)
        refresh_tasks()
    threading.Thread(target=process, daemon=True).start()

entry.bind("<Return>", on_enter)

mic_btn = tk.Button(ibar, text="◉", command=toggle_microphone,
                    bg=PANEL_BG, fg=ACCENT_DIM, font=(FONT_MONO, 18),
                    bd=0, activebackground=PANEL_BG, activeforeground=ACCENT,
                    cursor="hand2", relief="flat")
mic_btn.pack(side="right", padx=(5, 24), pady=12)

def setup_hotkeys():
    try:
        import keyboard
        keyboard.add_hotkey('ctrl+alt+j', lambda: root.after(0, root.deiconify))
        keyboard.add_hotkey('ctrl+alt+h', lambda: root.after(0, root.withdraw))
        print("Ctrl+Alt+J / Ctrl+Alt+H")
    except Exception as e:
        print(f"Горячие клавиши: {e}")

def setup_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (64, 64), color='#000a0d')
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), outline=ACCENT, width=3)
        d.ellipse((20, 20, 44, 44), fill=ACCENT)
        def show(icon, item): root.after(0, root.deiconify)
        def quit_(icon, item):
            icon.stop(); root.after(0, root.destroy)
        menu = pystray.Menu(
            pystray.MenuItem('Показать', show, default=True),
            pystray.MenuItem('Выход', quit_),
        )
        icon = pystray.Icon("jarvis", img, "J.A.R.V.I.S.", menu)
        threading.Thread(target=icon.run, daemon=True).start()
        print("Трей активен.")
    except Exception as e:
        print(f"Трей: {e}")

def startup():
    h = datetime.datetime.now().hour
    if h < 6: g = "Доброй ночи"
    elif h < 12: g = "Доброе утро"
    elif h < 18: g = "Добрый день"
    else: g = "Добрый вечер"
    add_message(f"{g}, {STATE['user_name']}. Все системы в норме.", is_user=False)
    add_message("Скажите «Джарвис» или «Пятница» для активации.", is_user=False)
    update_stats()
    update_weather()
    refresh_tasks()
    scan_shortcuts()
    add_message(f"Найдено программ: {len(INSTALLED_APPS)}", is_user=False)
    speak(f"{g}. Все системы в норме.")
    start_wake_listener()
threading.Thread(target=check_tasks_loop, daemon=True).start()

root.after(1500, startup)
root.after(0, tick)
root.after(100, animate)
root.after(200, pulse_dot_tick)
root.after(700, setup_hotkeys)
root.after(900, setup_tray)

root.protocol("WM_DELETE_WINDOW", lambda: (stop_wake_listener(), root.destroy()))
root.mainloop()
