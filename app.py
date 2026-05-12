from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Retro Hunter v2</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; margin: 0; padding: 15px; color: #1c1e21; }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { font-size: 24px; text-align: center; color: #c00000; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .update-section { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 25px; text-align: center; }
        .system-card { background: white; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }
        .system-header { background: #2c3e50; color: white; padding: 12px 18px; font-weight: bold; font-size: 16px; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 14px 18px; border-bottom: 1px solid #f0f2f5; font-size: 15px; }
        tr:last-child td { border-bottom: none; }
        .price-box { text-align: right; }
        .loose { color: #555; font-size: 12px; font-weight: 500; display: block; }
        .cib { color: #c00000; font-weight: bold; font-size: 15px; display: block; margin-top: 2px; }
        .btn { background: #c00000; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 16px; width: 100%; cursor: pointer; -webkit-appearance: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 RETRO HUNTER</h1>
        <div class="update-section">
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" id="fileInput" style="display:none;" onchange="this.form.submit()">
                <button type="button" class="btn" onclick="document.getElementById('fileInput').click()">Upload Collection List</button>
            </form>
        </div>
        {% if data %}
            {% for system, games in data.items() %}
            <div class="system-card">
                <div class="system-header">{{ system }}</div>
                <table>
                    {% for game in games %}
                    <tr>
                        <td><strong>{{ game.title }}</strong></td>
                        <td class="price-box">
                            <span class="loose">Loose: {{ game.loose }}</span>
                            <span class="cib">CIB: {{ game.cib }}</span>
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
        'TURBOGRAFX-16': 'turbografx-16', 'ATARI JAGUAR': 'atari-jaguar'
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
    return render_template_string(HTML_TEMPLATE, data=final_data)

if __name__ == '__main__':
    app.run()
