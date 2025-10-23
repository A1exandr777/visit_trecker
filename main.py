from aiohttp import web
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("visits.json")


def load_data():
    default_data = {
        "total": 0,
        "by_day": {},
        "by_month": {},
        "by_year": {},
        "unique_total": 0,
        "unique_by_day": {},
        "unique_by_month": {},
        "unique_by_year": {},
        "unique_ips": []
    }

    if DATA_FILE.exists():
        try:
            with DATA_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    for key, value in default_data.items():
        if key not in data:
            data[key] = value

    return data


def save_data(data):
    with DATA_FILE.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def increment_counters(data, ip: str):
    today = datetime.now().strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')
    year = datetime.now().strftime('%Y')

    data['total'] = data.get('total', 0) + 1
    data['by_day'][today] = data['by_day'].get(today, 0) + 1
    data['by_month'][month] = data['by_month'].get(month, 0) + 1
    data['by_year'][year] = data['by_year'].get(year, 0) + 1
    if ip not in data.get('unique_ips', []):
        data['unique_ips'].append(ip)
        data['unique_total'] = data.get('unique_total', 0) + 1

    if today not in data['unique_by_day']:
        data['unique_by_day'][today] = {"count": 0, "ips": []}
    if ip not in data['unique_by_day'][today]['ips']:
        data['unique_by_day'][today]['ips'].append(ip)
        data['unique_by_day'][today]['count'] += 1

    if month not in data['unique_by_month']:
        data['unique_by_month'][month] = {"count": 0, "ips": []}
    if ip not in data['unique_by_month'][month]['ips']:
        data['unique_by_month'][month]['ips'].append(ip)
        data['unique_by_month'][month]['count'] += 1

    if year not in data['unique_by_year']:
        data['unique_by_year'][year] = {"count": 0, "ips": []}
    if ip not in data['unique_by_year'][year]['ips']:
        data['unique_by_year'][year]['ips'].append(ip)
        data['unique_by_year'][year]['count'] += 1

    save_data(data)


def reset_counters(data):
    data['total'] = 0
    data['by_day'] = {}
    data['by_month'] = {}
    data['by_year'] = {}
    data['unique_total'] = 0
    data['unique_by_day'] = {}
    data['unique_by_month'] = {}
    data['unique_by_year'] = {}
    data['unique_ips'] = []
    save_data(data)


def get_client_ip(request: web.Request) -> str:
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote or 'unknown'


async def index(request: web.Request):
    ip = get_client_ip(request)
    data = load_data()
    increment_counters(data, ip)

    today = datetime.now().strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')
    year = datetime.now().strftime('%Y')

    html = f"""
    <html>
      <head><meta charset="utf-8"><title>Счётчик посещений</title></head>
      <body>
        <h1>Спасибо за визит!</h1>
        <p>Всего посещений: <strong>{data['total']}</strong></p>
        <p>Сегодня ({today}): <strong>{data['by_day'].get(today, 0)}</strong></p>
        <p>В этом месяце ({month}): <strong>{data['by_month'].get(month, 0)}</strong></p>
        <p>В этом году ({year}): <strong>{data['by_year'].get(year, 0)}</strong></p>

        <h2>Уникальные пользователи</h2>
        <p>Всего уникальных: <strong>{data['unique_total']}</strong></p>
        <p>Уникальных сегодня: <strong>{data['unique_by_day'].get(today, {}).get('count', 0)}</strong></p>
        <p>Уникальных в этом месяце: <strong>{data['unique_by_month'].get(month, {}).get('count', 0)}</strong></p>
        <p>Уникальных в этом году: <strong>{data['unique_by_year'].get(year, {}).get('count', 0)}</strong></p>

        <form action="/reset" method="post" onsubmit="return confirm('Сбросить статистику?');">
          <button type="submit">Сбросить статистику</button>
        </form>

        <p>API: GET /count — JSON, POST /reset — сброс</p>
      </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def count_api(request: web.Request):
    data = load_data()
    today = datetime.now().strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')
    year = datetime.now().strftime('%Y')
    return web.json_response({
        'total': data['total'],
        'today': data['by_day'].get(today, 0),
        'this_month': data['by_month'].get(month, 0),
        'this_year': data['by_year'].get(year, 0),
        'unique_total': data.get('unique_total', 0),
        'unique_today': data.get('unique_by_day', {}).get(today, {}).get('count', 0),
        'unique_this_month': data.get('unique_by_month', {}).get(month, {}).get('count', 0),
        'unique_this_year': data.get('unique_by_year', {}).get(year, {}).get('count', 0),
        'by_day': data['by_day'],
        'by_month': data['by_month'],
        'by_year': data['by_year'],
        'unique_by_day': data.get('unique_by_day', {}),
        'unique_by_month': data.get('unique_by_month', {}),
        'unique_by_year': data.get('unique_by_year', {})
    })


async def reset_api(request: web.Request):
    data = load_data()
    reset_counters(data)
    return web.json_response({'status': 'ok', 'message': 'counters reset'})


def create_app():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/count', count_api)
    app.router.add_post('/reset', reset_api)
    return app


if __name__ == '__main__':
    web.run_app(create_app(), host='0.0.0.0', port=8080)
