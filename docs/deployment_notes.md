# Deployment Notes

Deployment scripts and full step-by-step instructions live in
[`deploy/README.md`](../deploy/README.md). This file documents the
runtime contract and required environment variables.

## Current Scope

Target deploy saat ini adalah backend API yang memakai satu public baseline model aktif.

Model aktif saat ini:

- `umkm_food_quality_v1` (MobileNetV2, threshold 0.1)

Manifest model aktif:

- `ml/model/active_model.json`

## Recommended Service Layout

### API

- FastAPI app dijalankan dari `app.main:app`
- Production: Gunicorn + Uvicorn workers (2 workers) di belakang Nginx reverse proxy

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
- Static bundle di-serve oleh Nginx di `/opt/foodqcheck/web/`
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
- `EMAIL_BACKEND`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `VERIFY_EMAIL_FRONTEND_URL`
- `RESET_PASSWORD_FRONTEND_URL`
- `REQUIRE_VERIFIED_EMAIL`

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
10. Set `REQUIRE_VERIFIED_EMAIL=true` agar user harus verifikasi email sebelum login
11. Set `EMAIL_BACKEND=resend` (recommended) atau `smtp` (kalau VPS allow SMTP):
    - **Resend**: Daftar di https://resend.com, buat API key, set `RESEND_API_KEY`. Sender harus domain yang sudah diverifikasi di Resend, atau pakai `onboarding@resend.dev` untuk testing (hanya bisa kirim ke email owner akun Resend). Port HTTPS 443, jadi work di semua VPS provider yang block SMTP.
    - **SMTP/Gmail**: Set `SMTP_*` variables. Perlu Gmail App Password. **TIDAK akan work di VPS yang block port 25/465/587** (e.g. DigitalOcean).
12. Set `VERIFY_EMAIL_FRONTEND_URL` dan `RESET_PASSWORD_FRONTEND_URL` ke URL yang benar:
    - Development (Android emulator): `foodqcheck://verify-email` / `foodqcheck://reset-password`
    - Production: `https://foodqcheck.drenzzz.dev/verify-email` / `https://foodqcheck.drenzzz.dev/reset-password`
13. Set `ALLOWED_HOSTS` ke hostname production (mis. `foodqcheck.drenzzz.dev,localhost,127.0.0.1`)
14. Pastikan auth endpoint dan detect endpoint lolos smoke test
15. Verifikasi `/.well-known/assetlinks.json` bisa diakses via HTTPS untuk Android App Links

## Production Hardening

- OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) otomatis di-disable saat `APP_ENV=production`
- CORS dibatasi ke specific methods (`GET, POST, PATCH, DELETE`) dan headers (`Authorization, Content-Type`)
- `TrustedHostMiddleware` memvalidasi Host header terhadap `ALLOWED_HOSTS`
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy) dipasang di Nginx
- JWT divalidasi dengan `iss` dan `aud` claims
- Password complexity: minimal 8 karakter, harus ada huruf besar, kecil, dan angka
- DB connection pool: `pool_size=5, max_overflow=0` untuk konservatif di 4GB VPS
- fail2ban aktif untuk SSH protection
- UFW aktif: hanya port 22 (SSH) dan 80 (Nginx) yang dibuka

## Fallback Rule

Jika deploy online belum siap, backend tetap bisa dijalankan lokal untuk integrasi tahap awal. Model inference tidak bergantung pada mobile dan bisa diuji via HTTP client atau TestClient.
