# Deployment Notes

Dokumen ini menjadi catatan deploy backend fase awal.

## Current Scope

Target deploy saat ini adalah backend API yang memakai satu public baseline model aktif.

Model aktif saat ini:

- `umkm_food_quality_v1` (MobileNetV2, threshold 0.1)

Manifest model aktif:

- `ml/model/active_model.json`

## Recommended Service Layout

### API

- FastAPI app dijalankan dari `app.main:app`

### Database

- PostgreSQL lokal untuk development
- PostgreSQL managed service untuk demo online

### Model Artifacts

- model dibaca dari direktori `ml/model/<experiment>/`
- backend harus tahu `MODEL_PATH` dan `CLASS_INDICES_PATH`
- pilihan model aktif sementara harus sinkron dengan `ml/model/active_model.json`

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
11. Set `EMAIL_BACKEND=smtp` dan konfigurasi `SMTP_*` variables untuk pengiriman email verifikasi dan reset password
12. Set `VERIFY_EMAIL_FRONTEND_URL` dan `RESET_PASSWORD_FRONTEND_URL` ke URL yang benar:
    - Development (Android emulator): `foodqcheck://verify-email` / `foodqcheck://reset-password`
    - Production: `https://foodqcheck.drenzzz.dev/verify-email` / `https://foodqcheck.drenzzz.dev/reset-password`
13. Pastikan auth endpoint dan detect endpoint lolos smoke test

## Fallback Rule

Jika deploy online belum siap, backend tetap bisa dijalankan lokal untuk integrasi tahap awal. Model inference tidak bergantung pada mobile dan bisa diuji via HTTP client atau TestClient.
