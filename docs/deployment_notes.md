# Deployment Notes

Deployment scripts and full step-by-step instructions live in
[`deploy/README.md`](../deploy/README.md). This file documents the
runtime contract and required environment variables.

## Current Scope

Target deploy saat ini adalah backend API yang memakai satu public baseline model aktif.

Model aktif saat ini:

- `umkm_food_quality_v1` (MobileNetV2, threshold 0.3)

Manifest model aktif:

- `ml/model/active_model.json`

## Recommended Service Layout

### API

- FastAPI app dijalankan dari `app.main:app`
- Production: Gunicorn + Uvicorn workers (2 workers) di belakang Caddy reverse proxy

### Database

- PostgreSQL 14 untuk baremetal
- PostgreSQL 15 untuk Docker compose
- Managed PostgreSQL service direkomendasikan untuk demo online

### Model Artifacts

- Model dibaca dari direktori `ml/model/<experiment>/`
- Backend harus tahu `MODEL_PATH` dan `CLASS_INDICES_PATH`
- Pilihan model aktif sementara harus sinkron dengan `ml/model/active_model.json`
- Model artifacts (.keras) di-gitignore karena ukurannya besar — di-upload manual via `deploy/copy-model.sh` (scp)

## Web SPA

- Frontend di-build dari project `umkm-food-quality-mobile` lewat `scripts/build-web.sh`
- Static bundle di-serve oleh Caddy di `/var/www/foodqcheck`
- `/api/*` di-strip prefix-nya lalu di-proxy ke backend

## Local Run Command

```bash
.venv-backend/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Required Environment Variables

- `APP_ENV`
- `DATABASE_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `MODEL_PATH`
- `CLASS_INDICES_PATH`
- `MODEL_REGISTRY_PATH`
- `ACTIVE_MODEL_CONFIG_PATH`
- `MODEL_QUALITY_REPORT_PATH`
- `MODEL_QUALITY_STRICT`
- `ENABLE_MULTI_MODEL_COMPARISON`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS` — comma-separated hostnames yang diizinkan oleh `TrustedHostMiddleware`
- `ALLOWED_IMAGE_DOMAINS`
- `IMAGE_DOWNLOAD_MAX_BYTES`
- `IMAGE_DOWNLOAD_MAX_REDIRECTS`
- `IMAGE_DOWNLOAD_TIMEOUT_SECONDS`
- `WARMUP_PREDICTOR_ON_STARTUP`
- `SITE_ADDRESS` — public domain Caddy obtains a TLS certificate for (Docker deploy)
- `ACME_EMAIL` — contact email for Let's Encrypt notices (Docker deploy)

## Deployment Checklist

1. Pastikan database bisa diakses dari runtime backend
2. Jalankan `alembic upgrade head` sebelum start server untuk apply schema migration
3. Pastikan `MODEL_PATH` menunjuk model yang benar
4. Pastikan `CLASS_INDICES_PATH` cocok dengan model aktif
5. Pastikan threshold review untuk model aktif sudah ada
6. Pastikan `MODEL_QUALITY_REPORT_PATH` tersedia
7. Set `MODEL_QUALITY_STRICT=true` jika runtime harus gagal saat model aktif tidak lolos quality gate
8. Set `ALLOWED_IMAGE_DOMAINS=res.cloudinary.com` untuk membatasi sumber gambar ke Cloudinary saja
9. Set `APP_ENV=production` agar warmup aktif dan CORS tidak merge dengan localhost defaults
10. Set `SITE_ADDRESS` dan `ACME_EMAIL` agar Caddy bisa menerbitkan sertifikat TLS. Pastikan Cloudflare di mode "Full (Strict)" atau DNS record "DNS only" supaya ACME challenge bisa menjangkau origin.
11. Set `ALLOWED_HOSTS` ke hostname production (mis. `foodqcheck.drenzzz.dev,localhost,127.0.0.1`)
12. Pastikan auth endpoint dan detect endpoint lolos smoke test

## Production Hardening

- OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) otomatis di-disable saat `APP_ENV=production`
- CORS dibatasi ke specific methods (`GET, POST, PATCH, DELETE`) dan headers (`Authorization, Content-Type`)
- `TrustedHostMiddleware` memvalidasi Host header terhadap `ALLOWED_HOSTS`
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS) dipasang di Caddy
- JWT divalidasi dengan `iss` dan `aud` claims
- Password complexity: minimal 8 karakter, harus ada huruf besar, kecil, dan angka
- DB connection pool: `pool_size=5, max_overflow=0` untuk konservatif di 4GB VPS
- fail2ban aktif untuk SSH protection
- UFW aktif: hanya port 22 (SSH), 80, dan 443 (Caddy) yang dibuka

## Fallback Rule

Jika deploy online belum siap, backend tetap bisa dijalankan lokal untuk integrasi tahap awal. Model inference tidak bergantung pada mobile dan bisa diuji via HTTP client atau TestClient.
