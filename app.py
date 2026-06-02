import os
import re
import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

GIST_ID = os.environ.get("GIST_ID")
GIST_TOKEN = os.environ.get("GIST_TOKEN")
GIST_FILENAME = "retro-hunter-data.json"
GIST_HEADERS = {
    "Authorization": f"token {GIST_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def now_eastern():
    return (datetime.now() - timedelta(hours=4)).strftime("%d %b %Y, %H:%M")

def load_gist():
    try:
        r = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=GIST_HEADERS, timeout=10)
        content = r.json()["files"][GIST_FILENAME]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"Error loading gist: {e}")
        return {"data": {}, "collection": [], "updated": None}

def save_gist(payload):
    try:
        body = {
            "files": {
                GIST_FILENAME: {
                    "content": json.dumps(payload, indent=2)
                }
            }
        }
        requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=GIST_HEADERS, json=body, timeout=10)
    except Exception as e:
        print(f"Error saving gist: {e}")

def parse_price(price_str):
    try:
        return float(price_str.replace("$", "").replace(",", ""))
    except:
        return None

def calc_change(old_str, new_str):
    old = parse_price(old_str)
    new = parse_price(new_str)
    if old is None or new is None or old == 0:
        return None
    pct = ((new - old) / old) * 100
    if abs(pct) < 1:
        return None
    return round(pct, 1)

SLUG_TO_SYSTEM = {
    "nes": "NES", "super-nintendo": "SNES", "nintendo-64": "N64",
    "gamecube": "GAMECUBE", "wii": "WII", "wii-u": "WII U",
    "gameboy": "GAMEBOY", "gameboy-color": "GAMEBOY COLOR",
    "gameboy-advance": "GAMEBOY ADVANCE", "nintendo-ds": "DS",
    "nintendo-dsi": "DSI", "nintendo-3ds": "3DS", "virtual-boy": "VIRTUAL BOY",
    "playstation": "PS1", "playstation-2": "PS2", "playstation-3": "PS3",
    "playstation-4": "PS4", "psp": "PSP", "ps-vita": "PS VITA",
    "sega-master-system": "SEGA MASTER SYSTEM", "sega-genesis": "SEGA GENESIS",
    "sega-cd": "SEGA CD", "sega-32x": "SEGA 32X", "sega-saturn": "SATURN",
    "sega-dreamcast": "DREAMCAST", "sega-game-gear": "GAME GEAR", "sega-pico": "SEGA PICO",
    "pc-engine": "PC ENGINE", "turbografx-16": "TURBOGRAFX-16",
    "turbografx-cd": "PC ENGINE CD", "pc-fx": "PC-FX",
    "neo-geo-aes": "NEO GEO AES", "neo-geo-mvs": "NEO GEO MVS",
    "neo-geo-cd": "NEO GEO CD", "neo-geo-pocket": "NEO GEO POCKET",
    "neo-geo-pocket-color": "NEO GEO POCKET COLOR",
    "atari-2600": "ATARI 2600", "atari-5200": "ATARI 5200",
    "atari-7800": "ATARI 7800", "atari-jaguar": "ATARI JAGUAR",
    "atari-jaguar-cd": "ATARI JAGUAR CD", "atari-lynx": "ATARI LYNX",
    "atari-st": "ATARI ST", "atari-400": "ATARI 400", "atari-800": "ATARI 800",
    "xbox": "XBOX", "xbox-360": "XBOX 360", "xbox-one": "XBOX ONE",
    "3do": "3DO", "philips-cdi": "CDI",
    "commodore-64": "COMMODORE 64", "amiga": "AMIGA", "amiga-cd32": "AMIGA CD32",
    "colecovision": "COLECOVISION", "intellivision": "INTELLIVISION",
    "odyssey-2": "ODYSSEY 2", "vectrex": "VECTREX",
    "wonderswan": "WONDERSWAN", "wonderswan-color": "WONDERSWAN COLOR",
    "pc": "PC", "dos": "DOS", "windows": "WINDOWS",
    "famicom": "FAMICOM", "super-famicom": "SUPER FAMICOM",
    "famicom-disk-system": "FAMICOM DISK SYSTEM",
}

def parse_pricecharting_url(url):
    try:
        m = re.search(r'pricecharting\.com/game/([^/]+)/([^/?#]+)', url)
        if not m:
            return None, None
        sys_slug = m.group(1)
        game_slug = m.group(2)
        system = SLUG_TO_SYSTEM.get(sys_slug, sys_slug.replace("-", " ").upper())
        title = game_slug.replace("-", " ").replace("%27", "'").title()
        return system, title
    except:
        return None, None

def get_market_price(system, title):
    sys_map = {
        "NES": "nes", "SNES": "super-nintendo", "N64": "nintendo-64",
        "GAMECUBE": "gamecube", "WII": "wii", "WII U": "wii-u",
        "GAMEBOY": "gameboy", "GAME BOY": "gameboy",
        "GAMEBOY COLOR": "gameboy-color", "GAME BOY COLOR": "gameboy-color", "GBC": "gameboy-color",
        "GAMEBOY ADVANCE": "gameboy-advance", "GAME BOY ADVANCE": "gameboy-advance", "GBA": "gameboy-advance",
        "GAMEBOY ADVANCE SP": "gameboy-advance", "DS": "nintendo-ds", "NINTENDO DS": "nintendo-ds",
        "DSI": "nintendo-dsi", "3DS": "nintendo-3ds", "VIRTUAL BOY": "virtual-boy",
        "PS1": "playstation", "PSX": "playstation", "PLAYSTATION": "playstation",
        "PS2": "playstation-2", "PLAYSTATION 2": "playstation-2",
        "PS3": "playstation-3", "PLAYSTATION 3": "playstation-3",
        "PS4": "playstation-4", "PLAYSTATION 4": "playstation-4",
        "PSP": "psp", "PS VITA": "ps-vita", "PSVITA": "ps-vita",
        "SEGA MASTER SYSTEM": "sega-master-system", "MASTER SYSTEM": "sega-master-system",
        "SEGA GENESIS": "sega-genesis", "GENESIS": "sega-genesis",
        "MEGA DRIVE": "sega-genesis", "SEGA MEGA DRIVE": "sega-genesis",
        "SEGA CD": "sega-cd", "MEGA CD": "sega-cd",
        "SEGA 32X": "sega-32x", "32X": "sega-32x",
        "SEGA SATURN": "sega-saturn", "SATURN": "sega-saturn",
        "SEGA DREAMCAST": "sega-dreamcast", "DREAMCAST": "sega-dreamcast",
        "SEGA GAME GEAR": "sega-game-gear", "GAME GEAR": "sega-game-gear",
        "SEGA PICO": "sega-pico",
        "PC ENGINE": "pc-engine", "TURBOGRAFX-16": "turbografx-16",
        "TURBOGRAFX 16": "turbografx-16", "TURBOGRAFX": "turbografx-16",
        "PC ENGINE CD": "turbografx-cd", "TURBOGRAFX CD": "turbografx-cd", "PC-FX": "pc-fx",
        "NEO GEO AES": "neo-geo-aes", "NEO GEO": "neo-geo-aes",
        "NEO GEO MVS": "neo-geo-mvs", "NEO GEO CD": "neo-geo-cd",
        "NEO GEO POCKET": "neo-geo-pocket", "NEO GEO POCKET COLOR": "neo-geo-pocket-color", "NGPC": "neo-geo-pocket-color",
        "ATARI 2600": "atari-2600", "2600": "atari-2600",
        "ATARI 5200": "atari-5200", "ATARI 7800": "atari-7800",
        "ATARI JAGUAR": "atari-jaguar", "JAGUAR": "atari-jaguar",
        "ATARI JAGUAR CD": "atari-jaguar-cd", "ATARI LYNX": "atari-lynx", "LYNX": "atari-lynx",
        "ATARI ST": "atari-st", "ATARI 400": "atari-400", "ATARI 800": "atari-800",
        "XBOX": "xbox", "XBOX 360": "xbox-360", "XBOX ONE": "xbox-one",
        "3DO": "3do", "CDI": "philips-cdi", "PHILIPS CDI": "philips-cdi",
        "COMMODORE 64": "commodore-64", "C64": "commodore-64",
        "AMIGA": "amiga", "AMIGA CD32": "amiga-cd32", "CD32": "amiga-cd32",
        "COLECOVISION": "colecovision", "INTELLIVISION": "intellivision",
        "ODYSSEY 2": "odyssey-2", "VECTREX": "vectrex",
        "WONDERSWAN": "wonderswan", "WONDERSWAN COLOR": "wonderswan-color",
        "PC": "pc", "DOS": "dos", "WINDOWS": "windows",
        "FAMICOM": "famicom",
        "SUPER FAMICOM": "super-famicom",
        "FAMICOM DISK SYSTEM": "famicom-disk-system",
    }
    sys_key = system.upper().strip()
    sys_slug = sys_map.get(sys_key, sys_key.lower().replace(" ", "-"))
    game_slug = re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s\'-]", "", title.lower().strip())).replace("'", "%27")
    url = f"https://www.pricecharting.com/game/{sys_slug}/{game_slug}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        used_td = soup.find("td", id="used_price")
        complete_td = soup.find("td", id="complete_price")
        if not used_td or not complete_td:
            return "N/A", "N/A", url
        loose = used_td.find("span", class_="price").text.strip()
        cib = complete_td.find("span", class_="price").text.strip()
        return loose, cib, url
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return "N/A", "N/A", url

def get_price_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        used_td = soup.find("td", id="used_price")
        complete_td = soup.find("td", id="complete_price")
        if not used_td or not complete_td:
            return "N/A", "N/A"
        loose = used_td.find("span", class_="price").text.strip()
        cib = complete_td.find("span", class_="price").text.strip()
        return loose, cib
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return "N/A", "N/A"

def enrich_with_change(new_game, old_game):
    if not old_game:
        return new_game
    new_game["loose_change"] = calc_change(old_game.get("loose"), new_game.get("loose"))
    new_game["cib_change"] = calc_change(old_game.get("cib"), new_game.get("cib"))
    return new_game

def smart_fetch(current_data, saved_data):
    import time
    final_data = {}
    for system, titles in current_data.items():
        final_data[system] = []
        existing = {g["title"]: g for g in saved_data.get(system, [])}
        for title in titles:
            if title in existing and existing[title].get("loose") not in (None, "-", ""):
                final_data[system].append(existing[title])
            else:
                time.sleep(0.5)
                l, c, url = get_market_price(system, title)
                new_game = {"title": title, "loose": l, "cib": c, "url": url}
                new_game = enrich_with_change(new_game, existing.get(title))
                final_data[system].append(new_game)
        final_data[system] = sorted(final_data[system], key=lambda x: x["title"].lower())
    return final_data

def full_fetch(data):
    import time
    final_data = {}
    for system, games in data.items():
        final_data[system] = []
        for game in games:
            title = game["title"]
            old_loose = game.get("loose")
            old_cib = game.get("cib")
            time.sleep(0.5)
            l, c, url = get_market_price(system, title)
            new_game = {"title": title, "loose": l, "cib": c, "url": url}
            new_game = enrich_with_change(new_game, {"loose": old_loose, "cib": old_cib})
            final_data[system].append(new_game)
        final_data[system] = sorted(final_data[system], key=lambda x: x["title"].lower())
    return final_data

def refresh_collection(collection):
    import time
    updated = []
    for item in collection:
        time.sleep(0.5)
        if item.get("url"):
            l, c = get_price_from_url(item["url"])
        else:
            l, c, _ = get_market_price(item["system"], item["title"])
        item["loose"] = l
        item["cib"] = c
        updated.append(item)
    return updated

def parse_list_text(gamelist):
    data = {}
    current_system = "Unknown"
    for line in gamelist.splitlines():
        clean = line.strip().lstrip("*- ").strip()
        clean = clean.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        if not clean:
            continue
        if clean.endswith(":"):
            current_system = clean[:-1].strip()
            if current_system not in data:
                data[current_system] = []
        else:
            if current_system not in data:
                data[current_system] = []
            data[current_system].append({"title": clean, "loose": None, "cib": None, "url": None})
    return data

def parse_and_fetch(data_dict):
    import time
    final_data = {}
    for system, games in data_dict.items():
        final_data[system] = []
        for game in games:
            title = game["title"]
            time.sleep(0.5)
            l, c, url = get_market_price(system, title)
            final_data[system].append({"title": title, "loose": l, "cib": c, "url": url})
        final_data[system] = sorted(final_data[system], key=lambda x: x["title"].lower())
    return final_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Retro Hunter</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --red: #c00000;
  --dark: #1a1a2e;
  --gold: #7a5c1e;
  --gold-light: #c49a2a;
  --card-bg: #ffffff;
  --bg: #f0f1f5;
  --text: #1c1e21;
  --subtext: #666;
  --green: #1a7a3a;
  --border: #eaeaea;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "DM Sans", sans-serif; background: var(--bg); color: var(--text); padding: 20px 16px 40px; }
.container { max-width: 560px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 24px; padding-top: 8px; }
.header h1 { font-family: "Bebas Neue", sans-serif; font-size: 42px; letter-spacing: 3px; color: var(--dark); line-height: 1; }
.header h1 span { color: var(--red); }
.header p { font-size: 12px; color: var(--subtext); letter-spacing: 1px; text-transform: uppercase; margin-top: 4px; }
.action-bar { display: flex; gap: 8px; margin-bottom: 10px; }
.btn { border: 1.5px solid #ccc; padding: 11px 18px; border-radius: 8px; font-family: "DM Sans", sans-serif; font-weight: 600; font-size: 13px; cursor: pointer; white-space: nowrap; flex: 1; background: white; color: var(--dark); }
.btn:active { opacity: 0.7; }
.btn:disabled { opacity: 0.4; }
.btn-red { background: var(--red); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-family: "DM Sans", sans-serif; font-weight: 600; font-size: 13px; cursor: pointer; }
.btn-red:active { opacity: 0.7; }
.btn-red:disabled { opacity: 0.4; }
.import-toggle { text-align: center; margin-bottom: 6px; }
.import-toggle button { background: none; border: none; color: #aaa; font-size: 12px; font-family: "DM Sans", sans-serif; cursor: pointer; text-decoration: underline; padding: 4px; }
.import-card { background: var(--card-bg); border-radius: 14px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 10px; display: none; }
.import-card.open { display: block; }
.import-card label { display: block; font-size: 11px; font-weight: 600; color: var(--subtext); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
textarea { width: 100%; height: 100px; border: 1.5px solid var(--border); border-radius: 10px; padding: 10px 12px; font-family: "DM Sans", sans-serif; font-size: 14px; color: var(--text); outline: none; background: #fafafa; resize: none; display: block; margin-bottom: 10px; }
textarea:focus { border-color: var(--red); background: #fff; }
textarea::placeholder { color: #bbb; line-height: 1.6; }
.import-btn-row { display: flex; justify-content: flex-end; }
.last-updated { text-align: center; font-size: 11px; color: #aaa; margin-bottom: 22px; letter-spacing: 0.5px; }
.spinner { display: none; text-align: center; padding: 20px; font-size: 13px; color: var(--subtext); }
.system-card { background: var(--card-bg); border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 16px; overflow: hidden; }
.system-header { background: var(--dark); color: white; padding: 10px 16px; font-family: "Bebas Neue", sans-serif; font-size: 18px; letter-spacing: 2px; display: flex; align-items: center; gap: 8px; cursor: pointer; }
.system-header::before { content: ""; display: inline-block; width: 3px; height: 16px; background: var(--red); border-radius: 2px; flex-shrink: 0; }
.chevron { margin-left: auto; font-size: 12px; opacity: 0.6; transition: transform 0.2s; }
.system-header.open .chevron { transform: rotate(180deg); }
.system-body { display: none; }
.system-body.open { display: block; }
.game-row { display: flex; align-items: center; padding: 11px 16px; border-bottom: 1px solid var(--border); gap: 8px; }
.game-row:last-of-type { border-bottom: none; }
.game-title-wrap { flex: 1; min-width: 0; }
.game-title { font-weight: 600; color: var(--text); font-size: 14px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
.game-title:active { color: var(--red); }
.price-box { flex-shrink: 0; display: flex; align-items: center; gap: 6px; }
.price-link { text-decoration: none; display: block; }
.price-col { display: flex; flex-direction: column; align-items: flex-end; }
.price-row { display: flex; align-items: center; justify-content: flex-end; height: 22px; }
.change-col { display: flex; flex-direction: column; align-items: flex-end; min-width: 38px; }
.change { font-size: 10px; font-weight: 600; height: 22px; display: flex; align-items: center; justify-content: flex-end; }
.change.up { color: var(--green); }
.change.down { color: var(--red); }
.price-label { font-size: 10px; color: #bbb; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 3px; }
.loose { color: var(--green); font-weight: 600; font-size: 14px; }
.cib { color: var(--red); font-weight: 700; font-size: 14px; }
.na-link { color: #bbb; font-size: 11px; display: block; text-decoration: underline; text-align: right; }
.del-btn { background: none; border: none; color: #ccc; font-size: 20px; cursor: pointer; padding: 0 0 0 4px; line-height: 1; flex-shrink: 0; font-weight: 300; }
.del-btn:active { color: #e53935; }
.buy-btn { background: none; border: 1.5px solid #ccc; border-radius: 6px; color: #aaa; font-size: 11px; font-weight: 600; cursor: pointer; padding: 3px 7px; white-space: nowrap; font-family: "DM Sans", sans-serif; flex-shrink: 0; }
.buy-btn:active { background: var(--gold-light); color: white; border-color: var(--gold-light); }
.add-row { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-top: 1px solid var(--border); }
.add-input { flex: 1; border: none; outline: none; font-family: "DM Sans", sans-serif; font-size: 14px; color: var(--text); background: transparent; }
.add-input::placeholder { color: #bbb; }
.add-btn { background: none; border: none; color: var(--red); font-size: 22px; cursor: pointer; line-height: 1; padding: 0 4px; font-weight: 300; }
.fetching-label { font-size: 11px; color: #aaa; font-style: italic; }
.collection-gap { height: 32px; }
.collection-card { background: var(--card-bg); border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 16px; overflow: hidden; }
.collection-header { background: var(--gold); color: #fff8e7; padding: 10px 16px; font-family: "Bebas Neue", sans-serif; font-size: 18px; letter-spacing: 2px; display: flex; align-items: center; gap: 8px; cursor: pointer; }
.collection-header::before { content: ""; display: inline-block; width: 3px; height: 16px; background: var(--gold-light); border-radius: 2px; flex-shrink: 0; }
.collection-header .chevron { margin-left: auto; font-size: 12px; opacity: 0.6; transition: transform 0.2s; }
.collection-header.open .chevron { transform: rotate(180deg); }
.collection-body { display: none; }
.collection-body.open { display: block; }
.coll-row { display: flex; align-items: center; padding: 11px 16px; border-bottom: 1px solid var(--border); gap: 8px; }
.coll-row:last-of-type { border-bottom: none; }
.coll-title-wrap { flex: 1; min-width: 0; }
.coll-title { font-weight: 600; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); cursor: pointer; }
.coll-title:active { color: var(--gold-light); }
.coll-system { font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 1px; }
.coll-prices { flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.coll-paid { font-size: 11px; color: var(--subtext); }
.coll-market { font-size: 14px; font-weight: 700; color: var(--dark); }
.coll-diff { font-size: 12px; font-weight: 700; }
.coll-diff.profit { color: var(--green); }
.coll-diff.loss { color: var(--red); }
.coll-condition { font-size: 10px; color: #bbb; text-transform: uppercase; letter-spacing: 0.5px; }
.coll-add-row { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-top: 1px solid var(--border); }
.coll-add-input { flex: 1; border: none; outline: none; font-family: "DM Sans", sans-serif; font-size: 14px; color: var(--text); background: transparent; }
.coll-add-input::placeholder { color: #bbb; }
.coll-add-btn { background: none; border: none; color: var(--gold-light); font-size: 22px; cursor: pointer; line-height: 1; padding: 0 4px; font-weight: 300; }
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; align-items: center; justify-content: center; padding: 20px; }
.modal-overlay.open { display: flex; }
.modal { background: white; border-radius: 16px; padding: 20px; width: 100%; max-width: 340px; }
.modal h3 { font-family: "Bebas Neue", sans-serif; font-size: 22px; letter-spacing: 2px; color: var(--dark); margin-bottom: 4px; }
.modal .game-name { font-size: 13px; color: var(--subtext); margin-bottom: 16px; }
.modal label { display: block; font-size: 11px; font-weight: 600; color: var(--subtext); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; margin-top: 12px; }
.modal input[type=text], .modal input[type=number] { width: 100%; border: 1.5px solid var(--border); border-radius: 10px; padding: 10px 12px; font-family: "DM Sans", sans-serif; font-size: 14px; outline: none; }
.modal input:focus { border-color: var(--gold-light); }
.modal select { width: 100%; border: 1.5px solid var(--border); border-radius: 10px; padding: 10px 12px; font-family: "DM Sans", sans-serif; font-size: 14px; outline: none; background: white; appearance: none; }
.modal select:focus { border-color: var(--gold-light); }
.modal-btns { display: flex; gap: 8px; margin-top: 20px; }
.modal-btns button { flex: 1; padding: 12px; border-radius: 10px; font-family: "DM Sans", sans-serif; font-weight: 600; font-size: 14px; cursor: pointer; border: none; }
.modal-cancel { background: var(--bg); color: var(--subtext); }
.modal-confirm { background: var(--gold); color: white; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🕹 RETRO<span>HUNTER</span></h1>
    <p>Live Market Prices</p>
  </div>

  <div class="action-bar">
    <button class="btn" id="updateBtn" onclick="updatePrices()">Update</button>
    <button class="btn" id="updateAllBtn" onclick="confirmUpdateAll()">Update All</button>
    <button class="btn" onclick="exportList()">Export</button>
  </div>

  <div class="import-toggle">
    <button onclick="toggleImport()">&#43; Import a list</button>
  </div>

  <div class="import-card" id="importCard">
    <label>Paste list to import</label>
    <textarea id="gameInput" placeholder="NES:\nSuper Mario Bros 3\nMetroid\n\nSEGA CD:\nSnatcher"></textarea>
    <div class="import-btn-row">
      <button class="btn-red" id="fetchBtn" onclick="fetchPrices()">Add Games</button>
    </div>
  </div>

  <p class="last-updated" id="lastUpdated">{{ updated if updated else "No data loaded yet" }}</p>
  <div class="spinner" id="spinner">Fetching prices, please wait...</div>

  <div id="results">
    {% if data %}
      {% for system, games in data.items() %}
      <div class="system-card" data-system="{{ system }}">
        <div class="system-header" onclick="toggleSystem(this)">
          {{ system }}<span class="chevron">&#9660;</span>
        </div>
        <div class="system-body">
          {% for game in games %}
          <div class="game-row" data-title="{{ game.title }}" data-url="{{ game.url }}" data-loose="{{ game.loose }}" data-cib="{{ game.cib }}">
            <div class="game-title-wrap">
              <span class="game-title" onclick="openPriceCharting(this)">{{ game.title }}</span>
            </div>
            <div class="price-box">
              {% if game.loose == "N/A" %}
                <a class="na-link" href="{{ game.url }}" target="_blank">N/A — Search</a>
              {% else %}
                <div class="change-col">
                  <span class="change {{ 'up' if game.loose_change and game.loose_change > 0 else 'down' if game.loose_change and game.loose_change < 0 else '' }}">{% if game.loose_change %}{{ '↑' if game.loose_change > 0 else '↓' }}{{ game.loose_change|abs }}%{% endif %}</span>
                  <span class="change {{ 'up' if game.cib_change and game.cib_change > 0 else 'down' if game.cib_change and game.cib_change < 0 else '' }}">{% if game.cib_change %}{{ '↑' if game.cib_change > 0 else '↓' }}{{ game.cib_change|abs }}%{% endif %}</span>
                </div>
                <a class="price-link" href="{{ game.url }}" target="_blank">
                  <div class="price-col">
                    <div class="price-row"><span class="price-label">L</span><span class="loose">{{ game.loose }}</span></div>
                    <div class="price-row"><span class="price-label">CIB</span><span class="cib">{{ game.cib }}</span></div>
                  </div>
                </a>
              {% endif %}
            </div>
            <button class="buy-btn" onclick="openBuyModal(this, '{{ game.title }}', '{{ system }}', '{{ game.loose }}', '{{ game.cib }}')">✓</button>
            <button class="del-btn" onclick="deleteGame(this)">&#10005;</button>
          </div>
          {% endfor %}
          <div class="add-row">
            <input class="add-input" type="text" placeholder="Game name or PriceCharting URL..." />
            <button class="add-btn" onclick="addGame(this)">+</button>
          </div>
        </div>
      </div>
      {% endfor %}
    {% endif %}
  </div>

  <div class="collection-gap"></div>

  <div class="collection-card" id="collectionCard">
    <div class="collection-header" onclick="toggleCollection(this)">
      MY COLLECTION<span class="chevron">&#9660;</span>
    </div>
    <div class="collection-body" id="collectionBody">
      {% for item in collection %}
      <div class="coll-row" data-id="{{ item.id }}" data-paid="{{ item.paid }}" data-condition="{{ item.condition }}">
        <div class="coll-title-wrap">
          <div class="coll-title" onclick="openCollPriceCharting(this)" data-url="{{ item.url }}">{{ item.title }}</div>
          <div class="coll-system">{{ item.system }} &middot; <span class="coll-condition">{{ item.condition }}</span></div>
        </div>
        <div class="coll-prices">
          <div class="coll-paid">Paid: {{ item.paid }}</div>
          {% set market = item.cib if item.condition == 'CIB' else item.loose %}
          <div class="coll-market">{{ market if market else '—' }}</div>
          {% if item.paid and market and market != 'N/A' %}
            {% set diff = (market|replace('$','')|replace(',','')|float) - (item.paid|replace('$','')|replace(',','')|float) %}
            <div class="coll-diff {{ 'profit' if diff >= 0 else 'loss' }}">{{ '+' if diff >= 0 else '' }}${{ "%.2f"|format(diff) }}</div>
          {% endif %}
        </div>
        <button class="del-btn" onclick="deleteCollectionItem(this)">&#10005;</button>
      </div>
      {% endfor %}
      <div class="coll-add-row">
        <input class="coll-add-input" type="text" placeholder="Game name or PriceCharting URL..." id="collAddInput" />
        <button class="coll-add-btn" onclick="openAddCollectionModal()">+</button>
      </div>
    </div>
  </div>
</div>

<!-- Buy modal -->
<div class="modal-overlay" id="buyModal">
  <div class="modal">
    <h3>MARK AS BOUGHT</h3>
    <div class="game-name" id="buyModalName"></div>
    <input type="hidden" id="buyModalTitle" />
    <input type="hidden" id="buyModalSystem" />
    <input type="hidden" id="buyModalLoose" />
    <input type="hidden" id="buyModalCib" />
    <input type="hidden" id="buyModalUrl" />
    <label>What did you pay?</label>
    <input type="number" id="buyModalPaid" placeholder="e.g. 12.50" step="0.01" min="0" />
    <label>Condition</label>
    <select id="buyModalCondition">
      <option value="Loose">Loose</option>
      <option value="CIB">CIB (Complete in Box)</option>
    </select>
    <div class="modal-btns">
      <button class="modal-cancel" onclick="closeBuyModal()">Cancel</button>
      <button class="modal-confirm" onclick="confirmBuy()">Add to Collection</button>
    </div>
  </div>
</div>

<!-- Add to collection modal -->
<div class="modal-overlay" id="addCollModal">
  <div class="modal">
    <h3>ADD TO COLLECTION</h3>
    <label>Game Title</label>
    <input type="text" id="addCollTitle" placeholder="e.g. Snatcher" />
    <label>System</label>
    <input type="text" id="addCollSystem" placeholder="e.g. Sega CD" />
    <label>What did you pay?</label>
    <input type="number" id="addCollPaid" placeholder="e.g. 12.50" step="0.01" min="0" />
    <label>Condition</label>
    <select id="addCollCondition">
      <option value="Loose">Loose</option>
      <option value="CIB">CIB (Complete in Box)</option>
    </select>
    <div class="modal-btns">
      <button class="modal-cancel" onclick="closeAddCollModal()">Cancel</button>
      <button class="modal-confirm" onclick="confirmAddCollection()">Add</button>
    </div>
  </div>
</div>

<script>
function exportList() {
  const lines = [];
  document.querySelectorAll(".system-card").forEach(card => {
    const system = card.dataset.system;
    const titles = [];
    card.querySelectorAll(".game-row .game-title").forEach(el => {
      const t = el.textContent.trim();
      if (t) titles.push(t);
    });
    if (titles.length) {
      lines.push(system + ":");
      titles.forEach(t => lines.push(t));
      lines.push("");
    }
  });
  const text = lines.join("\\n").trimEnd();
  const blob = new Blob([text], {type: "text/plain"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "retro-wishlist.txt";
  a.click();
  URL.revokeObjectURL(url);
}
function isPriceChartingUrl(str) { return str.includes("pricecharting.com/game/"); }
function openPriceCharting(el) {
  const row = el.closest(".game-row");
  const url = row.dataset.url;
  const title = el.textContent.trim();
  if (!url) return;
  if (confirm("Open " + title + " on PriceCharting?")) { window.open(url, "_blank"); }
}
function openCollPriceCharting(el) {
  const url = el.dataset.url;
  const title = el.textContent.trim();
  if (!url) return;
  if (confirm("Open " + title + " on PriceCharting?")) { window.open(url, "_blank"); }
}
function toggleImport() { document.getElementById("importCard").classList.toggle("open"); }
function toggleSystem(header) {
  header.classList.toggle("open");
  header.nextElementSibling.classList.toggle("open");
}
function toggleCollection(header) {
  header.classList.toggle("open");
  document.getElementById("collectionBody").classList.toggle("open");
}

// KEY FIX: collect full game data including prices from data attributes
function getSystemData() {
  const data = {};
  document.querySelectorAll(".system-card").forEach(card => {
    const system = card.dataset.system;
    data[system] = [];
    card.querySelectorAll(".game-row").forEach(row => {
      const title = row.querySelector(".game-title").textContent.trim();
      if (title) {
        data[system].push({
          title: title,
          loose: row.dataset.loose || "-",
          cib: row.dataset.cib || "-",
          url: row.dataset.url || ""
        });
      }
    });
  });
  return data;
}

function deleteGame(btn) { btn.closest(".game-row").remove(); saveList(); }

function addGame(btn) {
  const addRow = btn.closest(".add-row");
  const input = addRow.querySelector(".add-input");
  const value = input.value.trim();
  if (!value) return;
  const systemCard = addRow.closest(".system-card");
  const system = systemCard.dataset.system;
  const systemBody = addRow.closest(".system-body");
  input.value = "";
  if (isPriceChartingUrl(value)) {
    const newRow = document.createElement("div");
    newRow.className = "game-row";
    newRow.dataset.url = value;
    newRow.dataset.loose = "-";
    newRow.dataset.cib = "-";
    newRow.innerHTML = `<div class='game-title-wrap'><span class='game-title'>resolving...</span></div><div class='price-box'><span class='fetching-label'>fetching...</span></div><button class='del-btn' onclick='deleteGame(this)'>&#10005;</button>`;
    systemBody.insertBefore(newRow, addRow);
    fetch("/lookup_url", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({url: value, system}) })
      .then(r => r.json())
      .then(res => {
        newRow.dataset.title = res.title;
        newRow.dataset.url = res.url || value;
        newRow.dataset.loose = res.loose || "-";
        newRow.dataset.cib = res.cib || "-";
        newRow.querySelector(".game-title").textContent = res.title;
        newRow.querySelector(".game-title").setAttribute("onclick", "openPriceCharting(this)");
        let priceHtml = res.loose === "N/A"
          ? `<a class='na-link' href='${res.url}' target='_blank'>N/A — Search</a>`
          : `<div class='change-col'><span class='change'></span><span class='change'></span></div><a class='price-link' href='${res.url}' target='_blank'><div class='price-col'><div class='price-row'><span class='price-label'>L</span><span class='loose'>${res.loose}</span></div><div class='price-row'><span class='price-label'>CIB</span><span class='cib'>${res.cib}</span></div></div></a>`;
        newRow.querySelector(".price-box").innerHTML = priceHtml;
        const t = res.title.replace(/"/g,"&quot;");
        const s = system.replace(/"/g,"&quot;");
        const buyBtn = document.createElement("button");
        buyBtn.className = "buy-btn";
        buyBtn.setAttribute("onclick", `openBuyModal(this,"${t}","${s}","${res.loose}","${res.cib}")`);
        buyBtn.textContent = "✓";
        newRow.insertBefore(buyBtn, newRow.querySelector(".del-btn"));
        saveList();
      })
      .catch(() => { newRow.querySelector(".game-title").textContent = "Error loading"; newRow.querySelector(".price-box").innerHTML = `<span class='fetching-label'>error</span>`; });
  } else {
    const title = value;
    const newRow = document.createElement("div");
    newRow.className = "game-row";
    newRow.dataset.title = title;
    newRow.dataset.url = "";
    newRow.dataset.loose = "-";
    newRow.dataset.cib = "-";
    newRow.innerHTML = `<div class='game-title-wrap'><span class='game-title' onclick='openPriceCharting(this)'>${title}</span></div><div class='price-box'><span class='fetching-label'>fetching...</span></div><button class='buy-btn' onclick='openBuyModal(this,"${title.replace(/"/g,"&quot;")}","${system.replace(/"/g,"&quot;")}","","")'>✓</button><button class='del-btn' onclick='deleteGame(this)'>&#10005;</button>`;
    systemBody.insertBefore(newRow, addRow);
    fetch("/price_lookup", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({title, system}) })
      .then(r => r.json())
      .then(res => {
        newRow.dataset.url = res.url || "";
        newRow.dataset.loose = res.loose || "-";
        newRow.dataset.cib = res.cib || "-";
        let priceHtml = res.loose === "N/A"
          ? `<a class='na-link' href='${res.url}' target='_blank'>N/A — Search</a>`
          : `<div class='change-col'><span class='change'></span><span class='change'></span></div><a class='price-link' href='${res.url}' target='_blank'><div class='price-col'><div class='price-row'><span class='price-label'>L</span><span class='loose'>${res.loose}</span></div><div class='price-row'><span class='price-label'>CIB</span><span class='cib'>${res.cib}</span></div></div></a>`;
        newRow.querySelector(".price-box").innerHTML = priceHtml;
        const t = title.replace(/"/g,"&quot;");
        const s = system.replace(/"/g,"&quot;");
        newRow.querySelector(".buy-btn").setAttribute("onclick", `openBuyModal(this,"${t}","${s}","${res.loose}","${res.cib}")`);
        saveList();
      })
      .catch(() => { newRow.querySelector(".price-box").innerHTML = `<span class='fetching-label'>error</span>`; saveList(); });
  }
}

function saveList() {
  const data = getSystemData();
  const collection = getCollectionData();
  fetch("/save", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({data, collection}) });
}
function setLoading(msg) {
  ["fetchBtn","updateBtn","updateAllBtn"].forEach(id => { const el = document.getElementById(id); if(el) el.disabled = true; });
  const s = document.getElementById("spinner"); s.style.display = "block"; s.textContent = msg;
}
function clearLoading() {
  ["fetchBtn","updateBtn","updateAllBtn"].forEach(id => { const el = document.getElementById(id); if(el) el.disabled = false; });
  document.getElementById("spinner").style.display = "none";
}
function changeHtml(val) {
  if (!val) return "<span class='change'></span>";
  const cls = val > 0 ? "up" : "down";
  const arrow = val > 0 ? "↑" : "↓";
  return `<span class='change ${cls}'>${arrow}${Math.abs(val)}%</span>`;
}
function calcDiffHtml(paid, market) {
  if (!paid || !market || market === "N/A" || market === "—") return "";
  const paidNum = parseFloat(paid.replace("$",""));
  const mktNum = parseFloat(market.replace("$","").replace(",",""));
  if (isNaN(paidNum) || isNaN(mktNum)) return "";
  const diff = mktNum - paidNum;
  return `<div class='coll-diff ${diff>=0?"profit":"loss"}'>${diff>=0?"+":""}$${Math.abs(diff).toFixed(2)}</div>`;
}
function renderResults(data, updated) {
  let html = "";
  for (const [system, games] of Object.entries(data)) {
    html += `<div class='system-card' data-system='${system}'>`;
    html += `<div class='system-header' onclick='toggleSystem(this)'>${system}<span class='chevron'>&#9660;</span></div>`;
    html += `<div class='system-body'>`;
    for (const game of games) {
      let priceHtml = game.loose === "N/A"
        ? `<a class='na-link' href='${game.url}' target='_blank'>N/A — Search</a>`
        : `<div class='change-col'>${changeHtml(game.loose_change)}${changeHtml(game.cib_change)}</div><a class='price-link' href='${game.url}' target='_blank'><div class='price-col'><div class='price-row'><span class='price-label'>L</span><span class='loose'>${game.loose}</span></div><div class='price-row'><span class='price-label'>CIB</span><span class='cib'>${game.cib}</span></div></div></a>`;
      const t = game.title.replace(/'/g,"&#39;").replace(/"/g,"&quot;");
      const s = system.replace(/"/g,"&quot;");
      const u = (game.url||"").replace(/"/g,"&quot;");
      html += `<div class='game-row' data-title='${game.title.replace(/'/g,"&#39;")}' data-url='${u}' data-loose='${game.loose||"-"}' data-cib='${game.cib||"-"}'>`;
      html += `<div class='game-title-wrap'><span class='game-title' onclick='openPriceCharting(this)'>${game.title}</span></div>`;
      html += `<div class='price-box'>${priceHtml}</div>`;
      html += `<button class='buy-btn' onclick='openBuyModal(this,"${t}","${s}","${game.loose}","${game.cib}")'>✓</button>`;
      html += `<button class='del-btn' onclick='deleteGame(this)'>&#10005;</button></div>`;
    }
    html += `<div class='add-row'><input class='add-input' type='text' placeholder='Game name or PriceCharting URL...' /><button class='add-btn' onclick='addGame(this)'>+</button></div></div></div>`;
  }
  document.getElementById("results").innerHTML = html;
  document.getElementById("lastUpdated").textContent = "Last updated: " + updated;
}
function fetchPrices() {
  const input = document.getElementById("gameInput").value.trim();
  if (!input) return;
  setLoading("Adding games, please wait...");
  fetch("/fetch", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({gamelist: input}) })
    .then(r => r.json())
    .then(res => { clearLoading(); renderResults(res.data, res.updated); document.getElementById("gameInput").value = ""; document.getElementById("importCard").classList.remove("open"); })
    .catch(() => clearLoading());
}
function updatePrices() {
  const data = getSystemData();
  setLoading("Fetching new prices only...");
  fetch("/update", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({data}) })
    .then(r => r.json())
    .then(res => { clearLoading(); renderResults(res.data, res.updated); })
    .catch(() => clearLoading());
}
function confirmUpdateAll() {
  if (confirm("Update All re-fetches every game and can take several minutes. Continue?")) {
    setLoading("Refreshing all prices, please wait...");
    fetch("/refresh", { method: "POST" })
      .then(r => r.json())
      .then(res => { clearLoading(); renderResults(res.data, res.updated); renderCollection(res.collection); })
      .catch(() => clearLoading());
  }
}
let _buyRow = null;
function openBuyModal(btn, title, system, loose, cib) {
  _buyRow = btn.closest(".game-row");
  document.getElementById("buyModalName").textContent = title + " (" + system + ")";
  document.getElementById("buyModalTitle").value = title;
  document.getElementById("buyModalSystem").value = system;
  document.getElementById("buyModalLoose").value = loose;
  document.getElementById("buyModalCib").value = cib;
  document.getElementById("buyModalUrl").value = _buyRow ? (_buyRow.dataset.url||"") : "";
  document.getElementById("buyModalPaid").value = "";
  document.getElementById("buyModal").classList.add("open");
}
function closeBuyModal() { document.getElementById("buyModal").classList.remove("open"); _buyRow = null; }
function confirmBuy() {
  const title = document.getElementById("buyModalTitle").value;
  const system = document.getElementById("buyModalSystem").value;
  const paid = document.getElementById("buyModalPaid").value;
  const condition = document.getElementById("buyModalCondition").value;
  const loose = document.getElementById("buyModalLoose").value;
  const cib = document.getElementById("buyModalCib").value;
  const url = document.getElementById("buyModalUrl").value;
  if (!paid) { alert("Please enter what you paid."); return; }
  addCollectionItem({title, system, paid: "$" + parseFloat(paid).toFixed(2), condition, loose, cib, url, id: Date.now().toString()});
  if (_buyRow) { _buyRow.remove(); saveList(); }
  closeBuyModal();
}
function openAddCollectionModal() {
  const titleInput = document.getElementById("collAddInput");
  const val = titleInput.value.trim();
  titleInput.value = "";
  if (isPriceChartingUrl(val)) {
    setLoading("Looking up game...");
    fetch("/lookup_url", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({url: val, system: ""}) })
      .then(r => r.json())
      .then(res => { clearLoading(); document.getElementById("addCollTitle").value = res.title||""; document.getElementById("addCollSystem").value = res.system||""; document.getElementById("addCollPaid").value = ""; document.getElementById("addCollModal").classList.add("open"); })
      .catch(() => { clearLoading(); document.getElementById("addCollModal").classList.add("open"); });
  } else {
    document.getElementById("addCollTitle").value = val;
    document.getElementById("addCollSystem").value = "";
    document.getElementById("addCollPaid").value = "";
    document.getElementById("addCollModal").classList.add("open");
  }
}
function closeAddCollModal() { document.getElementById("addCollModal").classList.remove("open"); }
function confirmAddCollection() {
  const title = document.getElementById("addCollTitle").value.trim();
  const system = document.getElementById("addCollSystem").value.trim();
  const paid = document.getElementById("addCollPaid").value;
  const condition = document.getElementById("addCollCondition").value;
  if (!title || !system || !paid) { alert("Please fill in all fields."); return; }
  setLoading("Looking up price...");
  fetch("/price_lookup", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({title, system}) })
    .then(r => r.json())
    .then(res => { clearLoading(); addCollectionItem({title, system, paid: "$" + parseFloat(paid).toFixed(2), condition, loose: res.loose, cib: res.cib, url: res.url, id: Date.now().toString()}); closeAddCollModal(); saveList(); })
    .catch(() => { clearLoading(); addCollectionItem({title, system, paid: "$" + parseFloat(paid).toFixed(2), condition, loose: null, cib: null, id: Date.now().toString()}); closeAddCollModal(); saveList(); });
}
function addCollectionItem(item) {
  const body = document.getElementById("collectionBody");
  const addRow = body.querySelector(".coll-add-row");
  const market = item.condition === "CIB" ? item.cib : item.loose;
  const diffHtml = calcDiffHtml(item.paid, market);
  const row = document.createElement("div");
  row.className = "coll-row";
  row.dataset.id = item.id;
  row.dataset.paid = item.paid;
  row.dataset.condition = item.condition;
  row.innerHTML = `<div class='coll-title-wrap'><div class='coll-title' onclick='openCollPriceCharting(this)' data-url='${item.url||""}'>${item.title}</div><div class='coll-system'>${item.system} &middot; <span class='coll-condition'>${item.condition}</span></div></div><div class='coll-prices'><div class='coll-paid'>Paid: ${item.paid}</div><div class='coll-market'>${market||"—"}</div>${diffHtml}</div><button class='del-btn' onclick='deleteCollectionItem(this)'>&#10005;</button>`;
  body.insertBefore(row, addRow);
  document.querySelector(".collection-header").classList.add("open");
  document.getElementById("collectionBody").classList.add("open");
}
function deleteCollectionItem(btn) {
  if (!confirm("Remove this game from your collection?")) return;
  btn.closest(".coll-row").remove();
  saveList();
}
function getCollectionData() {
  const items = [];
  document.querySelectorAll(".coll-row").forEach(row => {
    const titleEl = row.querySelector(".coll-title");
    const title = titleEl?.textContent.trim();
    const systemEl = row.querySelector(".coll-system");
    const systemText = systemEl ? systemEl.textContent.split("·")[0].trim() : "";
    const condition = row.querySelector(".coll-condition")?.textContent.trim();
    const paidEl = row.querySelector(".coll-paid");
    const paid = paidEl ? paidEl.textContent.replace("Paid: ","").trim() : "";
    const url = titleEl?.dataset.url || "";
    if (title) items.push({id: row.dataset.id || Date.now().toString(), title, system: systemText, condition, paid, url});
  });
  return items;
}
function renderCollection(collection) {
  if (!collection) return;
  const body = document.getElementById("collectionBody");
  const addRow = body.querySelector(".coll-add-row");
  body.querySelectorAll(".coll-row").forEach(r => r.remove());
  collection.forEach(item => {
    const market = item.condition === "CIB" ? item.cib : item.loose;
    const diffHtml = calcDiffHtml(item.paid, market);
    const row = document.createElement("div");
    row.className = "coll-row";
    row.dataset.id = item.id;
    row.innerHTML = `<div class='coll-title-wrap'><div class='coll-title' onclick='openCollPriceCharting(this)' data-url='${item.url||""}'>${item.title}</div><div class='coll-system'>${item.system} &middot; <span class='coll-condition'>${item.condition}</span></div></div><div class='coll-prices'><div class='coll-paid'>Paid: ${item.paid}</div><div class='coll-market'>${market||"—"}</div>${diffHtml}</div><button class='del-btn' onclick='deleteCollectionItem(this)'>&#10005;</button>`;
    body.insertBefore(row, addRow);
  });
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    saved = load_gist()
    return render_template_string(HTML_TEMPLATE, data=saved.get("data", {}), collection=saved.get("collection", []), updated=saved.get("updated"))

@app.route("/fetch", methods=["POST"])
def fetch():
    body = request.get_json()
    gamelist = body.get("gamelist", "")
    new_data_raw = parse_list_text(gamelist)
    new_data = parse_and_fetch(new_data_raw)
    updated = now_eastern()
    saved = load_gist()
    existing_data = saved.get("data", {})
    for system, new_games in new_data.items():
        if system in existing_data:
            existing_titles = {g["title"]: g for g in existing_data[system]}
            for game in new_games:
                if game["title"] not in existing_titles:
                    existing_data[system].append(game)
            existing_data[system] = sorted(existing_data[system], key=lambda x: x["title"].lower())
        else:
            existing_data[system] = new_games
    save_gist({"data": existing_data, "collection": saved.get("collection", []), "updated": updated})
    return jsonify({"data": existing_data, "updated": updated})

@app.route("/update", methods=["POST"])
def update():
    body = request.get_json()
    current_data = body.get("data", {})
    saved = load_gist()
    saved_data = saved.get("data", {})
    # current_data now contains full game objects with prices
    final_data = {}
    import time
    for system, games in current_data.items():
        final_data[system] = []
        existing = {g["title"]: g for g in saved_data.get(system, [])}
        for game in games:
            title = game if isinstance(game, str) else game.get("title", "")
            ex = existing.get(title, {})
            if ex.get("loose") not in (None, "-", ""):
                final_data[system].append(ex)
            else:
                time.sleep(0.5)
                l, c, url = get_market_price(system, title)
                new_game = {"title": title, "loose": l, "cib": c, "url": url}
                new_game = enrich_with_change(new_game, ex)
                final_data[system].append(new_game)
        final_data[system] = sorted(final_data[system], key=lambda x: x["title"].lower())
    updated = now_eastern()
    save_gist({"data": final_data, "collection": saved.get("collection", []), "updated": updated})
    return jsonify({"data": final_data, "updated": updated})

@app.route("/refresh", methods=["POST"])
def refresh():
    saved = load_gist()
    existing_data = saved.get("data", {})
    collection = saved.get("collection", [])
    final_data = full_fetch(existing_data)
    updated_collection = refresh_collection(collection)
    updated = now_eastern()
    save_gist({"data": final_data, "collection": updated_collection, "updated": updated})
    return jsonify({"data": final_data, "collection": updated_collection, "updated": updated})

@app.route("/save", methods=["POST"])
def save():
    body = request.get_json()
    current_data = body.get("data", {})
    collection = body.get("collection", [])
    saved = load_gist()
    existing_data = saved.get("data", {})

    for system, games in current_data.items():
        existing_titles = {g["title"]: g for g in existing_data.get(system, [])}
        merged = []
        for game in games:
            if isinstance(game, dict):
                title = game.get("title", "")
                # Use prices from frontend if they exist, else fall back to gist
                ex = existing_titles.get(title, {})
                loose = game.get("loose") if game.get("loose") not in (None, "-", "") else ex.get("loose", "-")
                cib = game.get("cib") if game.get("cib") not in (None, "-", "") else ex.get("cib", "-")
                url = game.get("url") or ex.get("url", "")
                merged.append({
                    "title": title,
                    "loose": loose,
                    "cib": cib,
                    "url": url,
                    "loose_change": ex.get("loose_change"),
                    "cib_change": ex.get("cib_change"),
                })
            else:
                # plain string title
                ex = existing_titles.get(game, {})
                merged.append({
                    "title": game,
                    "loose": ex.get("loose", "-"),
                    "cib": ex.get("cib", "-"),
                    "url": ex.get("url", ""),
                    "loose_change": ex.get("loose_change"),
                    "cib_change": ex.get("cib_change"),
                })
        existing_data[system] = merged

    saved_coll = {item["id"]: item for item in saved.get("collection", [])}
    merged_collection = []
    for item in collection:
        if item["id"] in saved_coll:
            saved_item = saved_coll[item["id"]]
            item["loose"] = saved_item.get("loose", item.get("loose"))
            item["cib"] = saved_item.get("cib", item.get("cib"))
            item["url"] = item.get("url") or saved_item.get("url", "")
        merged_collection.append(item)
    save_gist({"data": existing_data, "collection": merged_collection, "updated": saved.get("updated")})
    return jsonify({"ok": True})

@app.route("/price_lookup", methods=["POST"])
def price_lookup():
    body = request.get_json()
    title = body.get("title", "")
    system = body.get("system", "")
    l, c, url = get_market_price(system, title)
    return jsonify({"loose": l, "cib": c, "url": url})

@app.route("/lookup_url", methods=["POST"])
def lookup_url():
    body = request.get_json()
    url = body.get("url", "")
    fallback_system = body.get("system", "")
    system, title = parse_pricecharting_url(url)
    if not system:
        system = fallback_system
    if not title:
        return jsonify({"title": "", "system": system, "loose": "N/A", "cib": "N/A", "url": url})
    l, c = get_price_from_url(url)
    return jsonify({"title": title, "system": system, "loose": l, "cib": c, "url": url})

if __name__ == "__main__":
    app.run()
