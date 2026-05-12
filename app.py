from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = '''
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

        /* HEADER */
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

        /* UPLOAD CARD */
        .upload-card {
            background: var(--card-bg);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .upload-card .upload-icon {
            width: 42px;
            height: 42px;
            background: #fff0f0;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 20px;
        }

        .upload-card .upload-info {
            flex: 1;
        }

        .upload-card .upload-info strong {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: var(--text);
        }

        .upload-card .upload-info span {
            font-size: 12px;
            color: var(--subtext);
        }

        .btn {
            background: var(--red);
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-family: 'DM Sans', sans-serif;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
            -webkit-appearance: none;
            transition: opacity 0.15s;
        }

        .btn:active { opacity: 0.8; }

        .last-updated {
            text-align: center;
            font-size: 11px;
            color: #aaa;
            margin-bottom: 22px;
            letter-spacing: 0.5px;
        }

        /* SYSTEM CARDS */
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

        <div class="upload-card">
            <div class="upload-icon">📋</div>
            <div class="upload-info">
                <strong>Upload Collection List</strong>
                <span>Plain .txt file, one game per line</span>
            </div>
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" id="fileInput" style="display:none;" onchange="this.form.submit()">
                <button type="button" class="btn" onclick="document.getElementById('fileInput').click()">Upload</button>
            </form>
        </div>

        {% if updated %}
        <p class="last-updated">Last updated: {{ updated }}</p>
        {% else %}
        <p class="last-updated">No data loaded yet</p>
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
</body>
</html>
'''

def get_market_price(system, title):
    sys_map = {
        'NES': 'nes', 'SNES': 'super-nintendo', 'N64': 'nintendo-64',
        'GAMEBOY': 'gameboy', 'GAMEBOY COLOR': 'gameboy-color',
        'SEGA MASTER SYSTEM': 'sega-master-system', 'SEGA GENESIS': 'sega-genesis',
        'SEGA CD': 'sega-cd', 'SEGA GAME GEAR': 'sega-game-gear',
        'PS1': 'playstation', 'PS2': 'playstation-2',
        'NEO GEO AES': 'neo-geo-aes', '3DO': '3do',
        'ATARI JAGUAR': 'atari-jaguar',
        'PC ENGINE': 'pc-engine'
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
        file = request.files.get('file')
        if file and file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            current_system = "Unknown"
            for line in content.splitlines():
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
