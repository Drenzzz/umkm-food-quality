# Deployment Guide

## Architecture

```
Cloudflare DNS (Flexible SSL, terminates HTTPS)
        |
        v
  VPS (Ubuntu 22.04)
  +--------------------------------------+
  | Nginx container (port 80)            |
  |   /                  -> web SPA      |
  |   /api/              -> strip prefix |
  +------------------+-------------------+
                     |
                     v
  +--------------------------------------+
  | API container (Gunicorn + Uvicorn)   |
  | FastAPI app on 127.0.0.1:8000       |
  +------------------+-------------------+
                     |
                     v
  +--------------------------------------+
  | PostgreSQL 15 container              |
  | Database: umkm_food_quality          |
  +--------------------------------------+
```

## Prerequisites

- VPS with Docker Engine + Docker Compose v2 installed
- SSH key access to VPS as `drenzzz` user
- Domain `foodqcheck.drenzzz.dev` pointed to VPS IP (Cloudflare A record, Proxied)
- Cloudflare SSL/TLS mode set to **Flexible**
- Trained model files available locally (`ml/model/umkm_food_quality_v1/`)

## Quick Deploy (Fresh VPS)

### 1. Install Docker Engine + Compose v2 (on VPS)

SSH into VPS as root:

```bash
ssh root@<VPS-IP>
```

Then:

```bash
# Install Docker from official repo
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add drenzzz to docker group
usermod -aG docker drenzzz

# Verify
su - drenzzz -c "docker compose version"
```

### 2. Clone repo (on VPS)

```bash
su - drenzzz
git clone <repo-url> ~/foodqcheck
cd ~/foodqcheck
```

### 3. Configure environment (on VPS)

```bash
cd ~/foodqcheck/deploy
cp env.docker.template env.production
nano env.production
```

Fill in:
- `DB_PASSWORD` — generate with: `openssl rand -base64 32`
- `SECRET_KEY` — generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `CORS_ORIGINS` — `https://foodqcheck.drenzzz.dev`
- `ALLOWED_HOSTS` — `foodqcheck.drenzzz.dev,localhost,127.0.0.1`

### 4. Build web SPA (on local machine)

```bash
cd umkm-food-quality-mobile
bun install --frozen-lockfile
VITE_API_BASE_URL=/api bun run build
```

### 5. Upload web SPA to VPS (from local machine)

```bash
rsync -avz --delete dist/ drenzzz@<VPS-IP>:~/foodqcheck/web/
```

### 6. Upload model files to VPS (from local machine)

```bash
cd umkm-food-quality
./deploy/copy-model.sh drenzzz@<VPS-IP>
```

### 7. Deploy (on VPS)

```bash
cd ~/foodqcheck
docker compose -f deploy/docker-compose.yml up -d --build
```

### 8. Verify

```bash
# Backend health
curl http://localhost/api/health

# Via Cloudflare
curl https://foodqcheck.drenzzz.dev/api/health

# Web app
curl -I https://foodqcheck.drenzzz.dev/
```

## Update Model (without rebuilding)

```bash
# From local machine
scp ml/model/umkm_food_quality_v1/model.keras drenzzz@<VPS-IP>:~/foodqcheck/ml/model/umkm_food_quality_v1/
scp ml/model/umkm_food_quality_v1/class_indices.json drenzzz@<VPS-IP>:~/foodqcheck/ml/model/umkm_food_quality_v1/

# On VPS, restart api container
docker compose -f deploy/docker-compose.yml restart api
```

## Update Web SPA (without rebuilding)

```bash
# From local machine
cd umkm-food-quality-mobile
VITE_API_BASE_URL=/api bun run build
rsync -avz --delete dist/ drenzzz@<VPS-IP>:~/foodqcheck/web/

# On VPS, restart nginx container
docker compose -f deploy/docker-compose.yml restart nginx
```

## Build Android APK

### Debug build (recommended for demo)

```bash
cd umkm-food-quality-mobile
./scripts/build-apk.sh debug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`

Install to device:
```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

### Signed release build

```bash
# Generate keystore (once)
keytool -genkey -v -keystore release.keystore -alias foodqcheck \
    -keyalg RSA -keysize 2048 -validity 10000

# Build signed APK
./scripts/build-apk.sh release release.keystore foodqcheck
```

## Troubleshooting

- **502 Bad Gateway** — API container not running. Check: `docker compose -f deploy/docker-compose.yml logs api`
- **Database connection refused** — Wrong `DB_PASSWORD` or PostgreSQL not ready. Check: `docker compose -f deploy/docker-compose.yml logs db`
- **Model not loaded** — Model files missing from bind mount. Check: `ls ~/foodqcheck/ml/model/umkm_food_quality_v1/`
- **Web app 404 on refresh** — `try_files` in nginx config not working. Verify nginx config is mounted correctly.
- **Rate limiting in dev** — Default rate limits apply. For testing, use `EMAIL_BACKEND=console` and test from localhost.

## Rollback

| Change | Rollback |
|--------|----------|
| Backend code | `cd ~/foodqcheck && git reset --hard <previous-sha> && docker compose -f deploy/docker-compose.yml up -d --build` |
| Web SPA | Rebuild previous version locally and rsync to VPS |
| Model | Copy previous model.keras/class_indices.json to VPS and restart api |
| Database | `docker compose exec db psql -U foodqcheck umkm_food_quality` then manual restore |
