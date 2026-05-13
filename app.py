import os
import re
import json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
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

def load_gist():
    try:
        r = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=GIST_HEADERS, timeout=10)
        content = r.json()["files"][GIST_FILENAME]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"Error loading gist: {e}")
        return {"data": {}, "updated": None}

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

def get_market_price(system, title):
    sys_map = {
        "NES": "nes", "SNES": "super-nintendo", "N64": "nintendo-64",
        "GAMEBOY": "gameboy", "GAMEBOY COLOR": "gameboy-color",
        "SEGA MASTER SYSTEM": "sega-master-system", "SEGA GENESIS": "sega-genesis",
        "SEGA CD": "sega-cd", "SEGA GAME GEAR": "sega-game-gear",
        "PS1": "playstation", "PS2": "playstation-2",
        "NEO GEO AES": "neo-geo-aes", "3DO": "3do",
        "ATARI JAGUAR": "atari-jaguar", "PC ENGINE": "pc-engine"
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
            return "N/A", "N/A"
        loose = used_td.find("span", class_="price").text.strip()
        cib = complete_td.find("span", class_="price").text.strip()
        return loose, cib
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return "N/A", "N/A"

def parse_and_fetch(gamelist):
    import time
    final_data = {}
    current_system = "Unknown"
    for line in gamelist.splitlines():
        clean = line.strip().lstrip("*- ").strip()
        clean = clean.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        if not clean:
            continue
        if clean.endswith(":"):
            current_system = clean[:-1].strip()
            final_data[current_system] = []
        else:
            time.sleep(0.5)
            l, c = get_market_price(current_system, clean)
            if current_system not in final_data:
                final_data[current_system] = []
            final_data[current_system].append({"title": clean, "loose": l, "cib": c})
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
        .input-card { background: var(--card-bg); border-radius: 14px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 10px; }
        .input-card label { display: block; font-size: 11px; font-weight: 600; color: var(--subtext); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
        textarea { width: 100%; height: 100px; border: 1.5px solid var(--border); border-radius: 10px; padding: 10px 12px; font-family: "DM Sans", sans-serif; font-size: 14px; color: var(--text); outline: none; background: #fafafa; resize: none; display: block; margin-bottom: 10px; }
        textarea:focus { border-color: var(--red); background: #fff; }
        textarea::placeholder { color: #bbb; line-height: 1.6; }
        .btn-row { display: flex; gap: 8px; justify-content: flex-end; }
        .btn { background: var(--red); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-family: "DM Sans", sans-serif; font-weight: 600; font-size: 13px; cursor: pointer; white-space: nowrap; }
        .btn-outline { background: transparent; color: var(--dark); border: 1.5px solid var(--border); }
        .btn:active { opacity: 0.7; }
        .btn:disabled { opacity: 0.5; }
        .last-updated { text-align: center; font-size: 11px; color: #aaa; margin-bottom: 22px; letter-spacing: 0.5px; }
        .system-card { background: var(--card-bg); border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 16px; overflow: hidden; }
        .system-header { background: var(--dark); color: white; padding: 10px 16px; font-family: "Bebas Neue", sans-serif; font-size: 18px; letter-spacing: 2px; display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .system-header::before { content: ""; display: inline-block; width: 3px; height: 16px; background: var(--red); border-radius: 2px; flex-shrink: 0; }
        .chevron { margin-left: auto; font-size: 12px; opacity: 0.6; transition: transform 0.2s; }
        .system-header.open .chevron { transform: rotate(180deg); }
        .system-body { display: none; }
        .system-body.open { display: block; }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 13px 16px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: middle; }
        tr:last-child td { border-bottom: none; }
        .game-title { font-weight: 600; color: var(--text); font-size: 14px; }
        .price-box { text-align: right; }
        .loose { color: var(--green); font-weight: 600; font-size: 14px; display: block; }
        .cib { color: var(--red); font-weight: 700; font-size: 14px; display: block; margin-top: 2px; }
        .price-label { font-size: 10px; color: #bbb; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 2px; }
        .spinner { display: none; text-align: center; padding: 20px; font-size: 13px; color: var(--subtext); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕹 RETRO<span>HUNTER</span></h1>
            <p>Live Market Prices</p>
        </div>
        <div class="input-card">
            <label>Paste your list</label>
            <textarea id="gameInput" placeholder="NES:
Super Mario Bros 3
Metroid

SEGA CD:
Snatcher"></textarea>
            <div class="btn-row">
                <button class="btn btn-outline" id="updateBtn" onclick="updatePrices()">Update</button>
                <button class="btn" id="fetchBtn" onclick="fetchPrices()">Fetch Prices</button>
            </div>
        </div>
        <p class="last-updated" id="lastUpdated">{{ updated if updated else "No data loaded yet" }}</p>
        <div class="spinner" id="spinner">Fetching prices, please wait...</div>
        <div id="results">
        {% if data %}
            {% for system, games in data.items() %}
            <div class="system-card">
                <div class="system-header" onclick="toggleSystem(this)">
                    {{ system }}
                    <span class="chevron">&#9660;</span>
                </div>
                <div class="system-body">
                    <table>
                        {% for game in games %}
                        <tr>
                            <td><span class="game-title">{{ game.title }}</span></td>
                            <td class="price-box">
                                <span class="loose"><span class="price-label">L</span>{{ game.loose }}</span>
                                <span class="cib"><span class="price-label">CIB</span>{{ game.cib }}</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
            {% endfor %}
        {% endif %}
        </div>
    </div>
    <script>
        function toggleSystem(header) {
            header.classList.toggle("open");
            header.nextElementSibling.classList.toggle("open");
        }
        function setLoading(msg) {
            document.getElementById("fetchBtn").disabled = true;
            document.getElementById("updateBtn").disabled = true;
            document.getElementById("spinner").style.display = "block";
            document.getElementById("spinner").textContent = msg;
        }
        function clearLoading() {
            document.getElementById("fetchBtn").disabled = false;
            document.getElementById("updateBtn").disabled = false;
            document.getElementById("spinner").style.display = "none";
        }
        function renderResults(data, updated) {
            let html = "";
            for (const [system, games] of Object.entries(data)) {
                html += "<div class='system-card'><div class='system-header' onclick='toggleSystem(this)'>" + system + "<span class='chevron'>&#9660;</span></div><div class='system-body'><table>";
                for (const game of games) {
                    html += "<tr><td><span class='game-title'>" + game.title + "</span></td><td class='price-box'><span class='loose'><span class='price-label'>L</span>" + game.loose + "</span><span class='cib'><span class='price-label'>CIB</span>" + game.cib + "</span></td></tr>";
                }
                html += "</table></div></div>";
            }
            document.getElementById("results").innerHTML = html;
            document.getElementById("lastUpdated").textContent = "Last updated: " + updated;
        }
        function fetchPrices() {
            const input = document.getElementById("gameInput").value.trim();
            if (!input) return;
            setLoading("Fetching prices, please wait...");
            fetch("/fetch", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({gamelist: input})
            })
            .then(r => r.json())
            .then(res => {
                clearLoading();
                renderResults(res.data, res.updated);
                document.getElementById("gameInput").value = "";
            })
            .catch(() => clearLoading());
        }
        function updatePrices() {
            setLoading("Updating prices from PriceCharting...");
            fetch("/update", {method: "POST"})
            .then(r => r.json())
            .then(res => {
                clearLoading();
                renderResults(res.data, res.updated);
            })
            .catch(() => clearLoading());
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    saved = load_gist()
    return render_template_string(HTML_TEMPLATE, data=saved.get("data", {}), updated=saved.get("updated"))

@app.route("/fetch", methods=["POST"])
def fetch():
    body = request.get_json()
    gamelist = body.get("gamelist", "")
    new_data = parse_and_fetch(gamelist)
    updated = datetime.now().strftime("%d %b %Y, %H:%M")
    saved = load_gist()
    existing_data = saved.get("data", {})
    existing_data.update(new_data)
    save_gist({"data": existing_data, "updated": updated})
    return jsonify({"data": existing_data, "updated": updated})

@app.route("/update", methods=["POST"])
def update():
    saved = load_gist()
    old_data = saved.get("data", {})
    lines = []
    for system, games in old_data.items():
        lines.append(f"{system}:")
        for game in games:
            lines.append(game["title"])
    gamelist = "\n".join(lines)
    final_data = parse_and_fetch(gamelist)
    updated = datetime.now().strftime("%d %b %Y, %H:%M")
    save_gist({"data": final_data, "updated": updated})
    return jsonify({"data": final_data, "updated": updated})

if __name__ == "__main__":
    app.run()
