# FinTrack – Accounting

A Django accounting app with income/expense tracking, categories, an automatically
maintained running ledger, GST calculations, PDF reports and bills, and optional
Gemini-powered financial analytics.

## Run locally (Windows)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The app is available at <http://127.0.0.1:8000/>. Create categories before adding
transactions if you want to categorize them during entry. Otherwise, transactions
can be categorized later.

Set `GEMINI_API_KEY` in the process environment to enable Financial Insights.
PowerShell example: `$env:GEMINI_API_KEY = "your-key"`. Copy `.env.example` to
`.env` when using Docker Compose; Compose loads that file for its environment
substitutions. Set `DJANGO_SECRET_KEY` before starting Django locally (for
example, `$env:DJANGO_SECRET_KEY = "a-long-unique-secret"`). The fallback key
is only available when explicitly enabling `DJANGO_DEBUG=True`.
When the key is not configured or the API returns invalid data, the analytics
page shows an error and does not fabricate a report. Historical transaction
data is sent to Google's Gemini API when this feature is used.

## Tests and static assets

```powershell
python manage.py test accounting
python manage.py test
python manage.py collectstatic --noinput
```

## Docker deployment

Set `DJANGO_SECRET_KEY` and, optionally, `GEMINI_API_KEY` in the environment.
`DJANGO_ALLOWED_HOSTS` must include the host name used to reach the service.
When TLS is configured at the reverse proxy, also set
`SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`,
`CSRF_COOKIE_SECURE=True`, and `SECURE_HSTS_SECONDS` to an appropriate value.
Enable `SECURE_HSTS_INCLUDE_SUBDOMAINS` and `SECURE_HSTS_PRELOAD` only if all
subdomains are HTTPS-only and you intend to use browser HSTS preload.

```powershell
docker compose up --build
```

The container applies database migrations, collects static files, and serves the
app with Gunicorn on port 8000. SQLite data persists in the `fintrack_data`
Docker volume. For production, provide a unique secret key and configure the
allowed hosts and TLS at the hosting provider or reverse proxy.
