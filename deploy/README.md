# Deployment Guide

This guide walks through deploying the UMKM Food Quality stack to an Ubuntu
22.04 VPS (4 GB RAM, 2 vCPU) using `foodqcheck.drenzzz.dev` as the public
hostname.

Two deployment variants are supported:

- **Baremetal** — Nginx, PostgreSQL and Gunicorn run directly on the VPS.
  Recommended for the 4 GB / 2 vCPU target.
- **Docker Compose** — Same stack inside containers. Heavier on RAM but
  reproducible.

## Architecture

```
Cloudflare DNS (Flexible SSL, terminates HTTPS)
        │
        ▼
  VPS (Ubuntu 22.04, 4 GB, 2 vCPU)
  ┌──────────────────────────────────────┐
  │ Nginx (port 80)                      │
  │   /                  → web SPA       │
  │   /api/              → strip prefix  │
  │   /.well-known/      → assetlinks    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ Gunicorn + Uvicorn (2 workers)       │
  │ FastAPI app on 127.0.0.1:8000       │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ PostgreSQL 14 (baremetal) / 15 (docker)│
  │ Database: umkm_food_quality          │
  └──────────────────────────────────────┘
```

## Cloudflare DNS

1. In Cloudflare dashboard for `drenzzz.dev`, add an **A** record:
   - Type: `A`
   - Name: `foodqcheck`
   - Content: `<VPS IP>`
   - Proxy: **Proxied** (orange cloud)
2. SSL/TLS → Overview → set mode to **Flexible**.
   Cloudflare terminates HTTPS for the public; the VPS only needs to serve
   plain HTTP on port 80. Do **not** enable HSTS on the origin — the
   origin connection is HTTP, not HTTPS.
3. Speed → Optimization: enable Brotli if desired.
4. Caching → Auto Minify HTML/CSS/JS: on (optional, SPA still works).

## Prerequisites

Run on your **local machine** before connecting to the VPS:

```bash
# Build the web SPA so deploy can sync it to the VPS
cd umkm-food-quality-mobile
./scripts/build-web.sh /api
```

The built `dist/` directory will be uploaded later.

## Baremetal Deployment

### 1. Run setup once (on the VPS)

SSH into the VPS as root:

```bash
ssh root@<VPS-IP>
```

Then:

```bash
# 1. Clone the backend repo
git clone <repo-url> /opt/foodqcheck
cd /opt/foodqcheck
chown -R foodqcheck:foodqcheck .

# 2. Run the setup script as root
sudo bash deploy/setup.sh
```

`setup.sh` will:
- Install Python 3.11, PostgreSQL, Nginx, fail2ban
- Create the `foodqcheck` system user
- Create the `umkm_food_quality` database (default password: `CHANGEME_DB_PASSWORD`)
- Configure UFW (allow SSH + Nginx) and fail2ban
- Set up log rotation

### 2. Change the database password (on the VPS)

```bash
sudo -u postgres psql -c "ALTER USER foodqcheck WITH PASSWORD '<strong-password>';"
```

### 3. Configure environment (on the VPS)

```bash
cd /opt/foodqcheck
cp deploy/env.production.template .env
nano .env   # fill in real values
```

Required values to fill in:
- `DATABASE_URL` — set to the new password
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `SMTP_USER` / `SMTP_PASSWORD` — Gmail address + App Password

### 4. Configure Nginx (on the VPS)

```bash
sudo cp /opt/foodqcheck/deploy/nginx.conf /etc/nginx/sites-available/foodqcheck
sudo ln -s /etc/nginx/sites-available/foodqcheck /etc/nginx/sites-enabled/foodqcheck
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Upload the model (from local)

The trained model lives in your local repo but is git-ignored. Copy it
to the VPS:

```bash
# From local machine
cd umkm-food-quality
./deploy/copy-model.sh foodqcheck@<VPS-IP>
```

This SCPs `model.keras` and `class_indices.json` and restarts the service.

### 6. Upload the web SPA (from local)

```bash
# From local machine
cd umkm-food-quality-mobile
rsync -avz --delete dist/ foodqcheck@<VPS-IP>:/opt/foodqcheck/web/
```

### 7. Deploy / update (on the VPS)

```bash
cd /opt/foodqcheck
sudo bash deploy/deploy.sh main
```

This:
- Pulls the latest source
- Updates the Python venv
- Applies Alembic migrations
- Installs the systemd service on first run
- Restarts the service and runs the health check

### 8. Verify

```bash
# Backend health
curl https://foodqcheck.drenzzz.dev/api/health

# Web app
curl -I https://foodqcheck.drenzzz.dev/

# Android App Links file
curl https://foodqcheck.drenzzz.dev/.well-known/assetlinks.json
```

## Docker Compose Deployment

```bash
# 1. Clone the repo on the VPS
git clone <repo-url> /opt/foodqcheck
cd /opt/foodqcheck

# 2. Configure environment
cp deploy/env.production.template .env
nano .env  # fill DB_PASSWORD at minimum
mkdir -p web
rsync -avz --delete ../umkm-food-quality-mobile/dist/ web/

# 3. Build and start
docker compose -f deploy/docker-compose.yml up -d --build

# 4. Check status
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f api

# 5. Upload the model (after the api container is up)
docker compose -f deploy/docker-compose.yml cp \
    ml/model/umkm_food_quality_v1/model.keras \
    api:/app/ml/model/umkm_food_quality_v1/model.keras
docker compose -f deploy/docker-compose.yml cp \
    ml/model/umkm_food_quality_v1/class_indices.json \
    api:/app/ml/model/umkm_food_quality_v1/class_indices.json
docker compose -f deploy/docker-compose.yml restart api
```

## Android App Links Setup (for `foodqcheck://` deep links)

1. Get the SHA-256 fingerprint of your release keystore:
   ```bash
   keytool -list -v -keystore /path/to/release.keystore -alias your_alias
   ```
2. Place the fingerprint in `ml/model/umkm_food_quality_v1/assetlinks.json`:
   ```json
   [
     {
       "relation": ["delegate_permission/common.handle_all_urls"],
       "target": {
         "namespace": "android_app",
         "package_name": "com.drenzzz.foodqcheck",
         "sha256_cert_fingerprints": ["<your-sha256>"]
       }
     }
   ]
   ```
3. Run `copy-model.sh` again (or scp the file directly) so the VPS serves
   it at `/.well-known/assetlinks.json`.
4. Update `umkm-food-quality-mobile/capacitor.config.ts` to add the HTTPS
   intent filter for `foodqcheck.drenzzz.dev` (see the
   `docs/security_notes.md` for the exact config).

## Build the Android APK

The mobile app is the primary target for the capstone demo. Build the
APK from the `umkm-food-quality-mobile` project on your local machine.

### Quick debug build (recommended for demo)

```bash
cd ../umkm-food-quality-mobile
./scripts/build-apk.sh debug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk` (~9 MB)

Install to a connected device or emulator:
```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

The debug APK points to `https://foodqcheck.drenzzz.dev/api` so it works
against the live backend once Cloudflare DNS resolves and the VPS is up.

### Signed release build (for distribution)

Generate a release keystore once:
```bash
keytool -genkey -v -keystore release.keystore -alias foodqcheck \
    -keyalg RSA -keysize 2048 -validity 10000
```

Build a signed APK (you'll be prompted for the keystore + key passwords):
```bash
./scripts/build-apk.sh release release.keystore foodqcheck
```

Output: `android/app/build/outputs/apk/release/app-release.apk`

### Smoke test checklist after install

- App launches → login screen
- Register with a real email → check Gmail → click verification link
- After verification → login → home screen → tap "Mulai Deteksi" → upload image
- Reset password flow → check Gmail → use link → new password works

## Rollback Strategy

| Change | Rollback |
|--------|----------|
| Backend code | `cd /opt/foodqcheck && sudo -u foodqcheck git reset --hard <previous-sha>` then `sudo systemctl restart foodqcheck` |
| Web SPA | `rsync` the previous `dist/` from local backup |
| Model | `scp` the previous `model.keras` from local backup |
| Database schema | `sudo -u foodqcheck .venv/bin/alembic downgrade -1` (one revision) or `-2` etc. |
| Docker stack | `docker compose -f deploy/docker-compose.yml down` then `up -d` from previous image tag |
| Nginx | `sudo cp /etc/nginx/sites-available/foodqcheck{.bak,}` then `sudo systemctl reload nginx` |

Always snapshot the database before destructive changes:
```bash
sudo -u postgres pg_dump umkm_food_quality > /opt/foodqcheck/backups/pre-deploy-$(date +%F).sql
```

## Troubleshooting

- **502 Bad Gateway** — backend not running. `sudo systemctl status foodqcheck`
- **Database connection refused** — wrong `DATABASE_URL` or PostgreSQL down. `sudo systemctl status postgresql`
- **Emails not sending** — most VPS providers (DigitalOcean, Vultr, Linode) block outbound SMTP (25/465/587). Check `EMAIL_BACKEND=resend` and a valid `RESEND_API_KEY`; the API uses port 443 which is always open. For SMTP fallback, verify `SMTP_*` env vars and Gmail App Password. Test with `curl -X POST http://localhost:8000/auth/forgot-password` (logged email will appear in `/var/log/foodqcheck/` for `EMAIL_BACKEND=console`, or check the Resend dashboard at https://resend.com/emails for the API).
- **Resend 403 "domain not verified"** — sender address must be on a verified domain at https://resend.com/domains, or use the test sender `onboarding@resend.dev` (which can only send to the Resend account owner email).
- **Resend 403 "only send testing emails to your own email"** — `onboarding@resend.dev` test sender is limited to the Resend account owner. Verify a custom domain or use a different sender.
- **Web app 404 on refresh** — ensure `try_files $uri $uri/ /index.html` is in the nginx `/` location block
- **`assetlinks.json` not found** — confirm the file is at `/var/www/foodqcheck/.well-known/assetlinks.json` (baremetal) or the Docker volume mount
- **Token expired in Deep Link** — bump `EMAIL_VERIFICATION_TOKEN_TTL_MINUTES` in `.env` for demo/development
