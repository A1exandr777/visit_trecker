from aiohttp import web
import json
from pathlib import Path
from datetime import datetime
import user_agents
import geoip2.database

DATA_FILE = Path("visits.json")
GEO_DB_FILE = Path("GeoLite2-City.mmdb")



def load_data():
    default_data = {
        "total": 0,
        "by_day": {},  # 2023-10-25
        "by_month": {},  # 2023-10
        "by_year": {},  # 2023

        "unique_total": 0,
        "unique_by_day": {},
        "unique_by_month": {},
        "unique_by_year": {},
        "unique_ips": [],

        "browsers": {},
        "geo": {
            "countries": {},
            "regions": {}
        },

        "time_stats": {
            "by_month_name": {},  
            "by_weekday": {},  
            "by_hour": {} 
        }
    }

    if DATA_FILE.exists():
        try:
            with DATA_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = deep_update(d.get(k, {}), v)
            elif k not in d:
                d[k] = v
        return d

    return deep_update(data, default_data)


def save_data(data):
    with DATA_FILE.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_geo_info(ip):
    """Определяет Страну и Регион по IP."""
    country = "Unknown"
    region = "Unknown"
    if ip in ['127.0.0.1', '::1', 'localhost', 'unknown']:
        return "Localhost", "Localhost"

    if GEO_DB_FILE.exists():
        try:
            with geoip2.database.Reader(str(GEO_DB_FILE)) as reader:
                response = reader.city(ip)
                country = response.country.name or "Unknown"
                if response.subdivisions:
                    region = response.subdivisions.most_specific.name
        except Exception:
            pass

    return country, region


def get_browser_info(user_agent_str):
    """Определяет семейство браузера."""
    if not user_agent_str:
        return "Unknown"
    ua = user_agents.parse(user_agent_str)
    return ua.browser.family 


def increment_counters(data, ip: str, user_agent: str):
    now = datetime.now()

    today = now.strftime('%Y-%m-%d')
    month = now.strftime('%Y-%m')
    year = now.strftime('%Y')

    month_name = now.strftime('%B') 
    weekday = now.strftime('%A') 
    hour = now.strftime('%H') 

    data['total'] = data.get('total', 0) + 1
    data['by_day'][today] = data['by_day'].get(today, 0) + 1
    data['by_month'][month] = data['by_month'].get(month, 0) + 1
    data['by_year'][year] = data['by_year'].get(year, 0) + 1

    if ip not in data.get('unique_ips', []):
        data['unique_ips'].append(ip)
        data['unique_total'] = data.get('unique_total', 0) + 1

    def init_unique_struct(dct, key):
        if key not in dct:
            dct[key] = {"count": 0, "ips": []}

    for container, key in [
        (data['unique_by_day'], today),
        (data['unique_by_month'], month),
        (data['unique_by_year'], year)
    ]:
        init_unique_struct(container, key)
        if ip not in container[key]['ips']:
            container[key]['ips'].append(ip)
            container[key]['count'] += 1

    browser = get_browser_info(user_agent)
    data['browsers'][browser] = data['browsers'].get(browser, 0) + 1

    country, region = get_geo_info(ip)

    data['geo']['countries'][country] = data['geo']['countries'].get(country, 0) + 1

    full_region = f"{country} - {region}"
    data['geo']['regions'][full_region] = data['geo']['regions'].get(full_region, 0) + 1

    data['time_stats']['by_month_name'][month_name] = data['time_stats']['by_month_name'].get(month_name, 0) + 1

    data['time_stats']['by_weekday'][weekday] = data['time_stats']['by_weekday'].get(weekday, 0) + 1
  
    data['time_stats']['by_hour'][hour] = data['time_stats']['by_hour'].get(hour, 0) + 1

    save_data(data)


def reset_counters(data):
    empty_structure = load_data() 
    for key in empty_structure:
        if isinstance(empty_structure[key], int):
            empty_structure[key] = 0
        elif isinstance(empty_structure[key], list):
            empty_structure[key] = []
        elif isinstance(empty_structure[key], dict):
            if key == "geo":
                empty_structure[key] = {"countries": {}, "regions": {}}
            elif key == "time_stats":
                empty_structure[key] = {"by_month_name": {}, "by_weekday": {}, "by_hour": {}}
            else:
                empty_structure[key] = {}

    save_data(empty_structure)


def get_client_ip(request: web.Request) -> str:
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote or 'unknown'

async def index(request: web.Request):
    ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', '')

    data = load_data()
    increment_counters(data, ip, user_agent)

    today = datetime.now().strftime('%Y-%m-%d')

    def get_top(dct, limit=5):
        sorted_items = sorted(dct.items(), key=lambda item: item[1], reverse=True)
        return sorted_items[:limit]

    top_browsers = get_top(data['browsers'])
    top_countries = get_top(data['geo']['countries'])
    top_hours = sorted(data['time_stats']['by_hour'].items())  

    html = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <title>Расширенная статистика</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .card {{ border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; }}
            h3 {{ margin-top: 0; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td, th {{ text-align: left; padding: 5px; border-bottom: 1px solid #eee; }}
        </style>
      </head>
      <body>
        <h1>Аналитика посещений</h1>

        <div class="grid">
            <div class="card">
                <h3>Основное</h3>
                <p>Всего визитов: <strong>{data['total']}</strong></p>
                <p>Уникальных IP: <strong>{data['unique_total']}</strong></p>
                <p>Сегодня ({today}): <strong>{data['by_day'].get(today, 0)}</strong></p>
            </div>

            <div class="card">
                <h3>Топ Браузеров</h3>
                <table>
                    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in top_browsers)}
                </table>
            </div>

            <div class="card">
                <h3>География (Страны)</h3>
                <table>
                    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in top_countries)}
                </table>
            </div>

            <div class="card">
                <h3>Активность по часам (Все время)</h3>
                <table>
                    <tr><th>Час</th><th>Визиты</th></tr>
                    {''.join(f"<tr><td>{k}:00</td><td>{v}</td></tr>" for k, v in top_hours)}
                </table>
            </div>

            <div class="card">
                <h3>Дни недели</h3>
                 <table>
                    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in get_top(data['time_stats']['by_weekday'], 7))}
                </table>
            </div>

             <div class="card">
                <h3>Месяцы (Сезонность)</h3>
                 <table>
                    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in data['time_stats']['by_month_name'].items())}
                </table>
            </div>
        </div>

        <br>
        <form action="/reset" method="post" onsubmit="return confirm('Сбросить ВСЮ статистику?');">
          <button type="submit" style="background:red; color:white; border:none; padding:10px; cursor:pointer;">Сбросить статистику</button>
        </form>

        <p><small>API: GET /count — JSON dump</small></p>
      </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def count_api(request: web.Request):
    data = load_data()
    return web.json_response(data)


async def reset_api(request: web.Request):
    data = load_data()
    reset_counters(data)
    return web.json_response({'status': 'ok', 'message': 'counters reset'})


def create_app():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/count', count_api)
    app.router.add_post('/reset', reset_api)
    app.router.add_get('/reset', reset_api)
    return app


if __name__ == '__main__':
    print("Запуск сервера...")
    web.run_app(create_app(), host='0.0.0.0', port=8080)
