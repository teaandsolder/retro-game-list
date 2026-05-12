from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)

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

        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 20px 16px 40px;
        }

        .container { max-width: 560px; margin: 0 auto; }

        .header {
            text-align: center;
            margin-bottom: 24px;
            padding-top: 8px;
        }

        .header h1 {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 42px;
            letter-spacing: 3px;
            color: var(--dark);
            line-height: 1;
        }

        .header h1 span { color: var(--red); }

        .header p {
            font-size: 12px;
            color: var(--subtext);
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-top: 4px;
        }

        .input-card {
            background: var(--card-bg);
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            margin-bottom: 10px;
        }

        .input-card label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: var(--subtext);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 10px;
        }

        textarea {
            width: 100%;
            height: 160px;
            border: 1.5px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            color: var(--text);
            resize: none;
            outline: none;
            background: #fafafa;
            transition: border-color 0.15s;
            -webkit-appearance: none;
        }

        textarea:focus { border-color: var(--red); background: #fff; }
        textarea::placeholder { color: #bbb; }

        .input-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
        }

        .input-footer span {
            font-size: 11px;
            color: #bbb;
        }

        .btn {
            background: var(--red);
            color: white;
            border: none;
            padding: 10px 22px;
            border-radius: 8px;
            font-family: 'DM Sans', sans-serif;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            -webkit-appearance: none;
            transition: opacity 0.15s;
        }

        .btn:active { opacity: 0.8; }
        .btn:disabled { opacity: 0.6; }

        .last-updated {
            text-align: center;
            font-size: 11px;
            color: #aaa;
            margin-bottom: 22px;
            letter-spacing: 0.5px;
        }

        .system-card {
            background: var(--card-bg);
            border-radius: 14px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            overflow: hidden;
        }

        .system-header {
            background: var(--dark);
            color: white;
            padding: 10px 16px;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 18px;
            letter-spacing: 2px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .system-header::before {
            content: '';
            display: inline-block;
            width: 3px;
            height: 16px;
            background: var(--red);
            border-radius: 2px;
        }

        table { width: 100%; border-collapse: collapse; }
        tr { transition: background 0.1s; }
        tr:active { background: #fafafa; }

        td {
            padding: 13px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
            vertical-align: middle;
        }

        tr:last-child td { border-bottom: none; }

        .game-title {
            font-weight: 600;
            color: var(--text);
            font-size: 14px;
        }

        .price-box { text-align: right; }

        .loose {
            color: var(--green);
            font-weight: 600;
            font-size: 14px;
            display: block;
        }

        .cib {
            color: var(--red);
            font-weight: 700;
            font-size: 14px;
            display: block;
            margin-top: 2px;
        }

        .price-label {
            font-size: 10px;
            color: #bbb;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 2px;
        }
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
            <form method="POST" id="priceForm">
                <textarea name="gamelist" id="gamelist" placeholder="NES:
Super Mario Bros 3
Metroid

SEGA CD:
Snatcher
Sonic CD"></textarea>
                <div class="input-footer">
                    <span>System name followed by colon, then games</span>
                    <button type="submit" class="btn" id="fetchBtn">Fetch Prices</button>
                </div>
            </form>
        </div>

        {% if updated %}
        <p class="last-updated">Last updated: {{ updated }}</p>
        {% else %}
        <p class="last-updated">Paste a list above and hit Fetch Prices</p>
        {% endif %}

        {% if data %}
            {% for system, games in data.items() %}
            <div class="system-card">
                <div class="system-header">{{ system }}</div>
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
            {% endfor %}
        {% endif %}

    </div>

    <script>
        document.getElementById('priceForm').addEventListener('submit', function() {
            const btn = document.getElementById('fetchBtn');
            btn.textContent = 'Fetching...';
            btn.disabled = true;
        });
    </script>

</body>
</html>
"""

def get_market_price(system, title):
    sys_map = {
        'NES': 'nes', 'SNES': 'super-nintendo', 'N64': 'nintendo-64',
        'GAMEBOY': 'gameboy', 'GAMEBOY COLOR': 'gameboy-color',
        'SEGA MASTER SYSTEM': 'sega-master-system', 'SEGA GENESIS': 'sega-genesis',
        'SEGA CD': 'sega-cd', 'SEGA GAME GEAR': 'sega-game-gear',
        'PS1': 'playstation', 'PS2': 'playstation-2',
        'NEO GEO AES': 'neo-geo-aes', '3DO': '3do',
        'ATARI JAGUAR': 'atari-jaguar', 'PC ENGINE': 'pc-engine'
    }
    sys_key = system.upper().strip()
    sys_slug = sys_map.get(sys_key, sys_key.lower().replace(" ", "-"))
    game_slug = re.sub(r'\s+', '-', re.sub(r'[^a-z0-9\s-]', '', title.lower().strip()))
    url = f"https://www.pricecharting.com/game/{sys_slug}/{game_slug}"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        used_td = soup.find('td', id='used_price')
        complete_td = soup.find('td', id='complete_price')
        if not used_td or not complete_td:
            return "N/A", "N/A"
        loose = used_td.find('span', class_='price').text.strip()
        cib = complete_td.find('span', class_='price').text.strip()
        return loose, cib
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return "N/A", "N/A"

@app.route('/', methods=['GET', 'POST'])
def index():
    final_data = {}
    updated = None
    if request.method == 'POST':
        gamelist = request.form.get('gamelist', '')
        current_system = "Unknown"
        for line in gamelist.splitlines():
            clean = line.strip().lstrip('*- ').strip()
            if not clean:
                continue
            if clean.endswith(':'):
                current_system = clean[:-1].strip()
                final_data[current_system] = []
            else:
                import time
                time.sleep(0.5)
                l, c = get_market_price(current_system, clean)
                if current_system not in final_data:
                    final_data[current_system] = []
                final_data[current_system].append({'title': clean, 'loose': l, 'cib': c})
        updated = datetime.now().strftime("%d %b %Y, %H:%M")
    return render_template_string(HTML_TEMPLATE, data=final_data, updated=updated)

if __name__ == '__main__':
    app.run()
