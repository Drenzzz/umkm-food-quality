# Deployment Notes

Dokumen ini menjadi catatan deploy backend fase awal.

## Current Scope

Target deploy saat ini adalah backend API yang memakai satu public baseline model aktif.

Model aktif sementara:

- `exp_001_industry_biscuit_only`

## Recommended Service Layout

### API

- FastAPI app dijalankan dari `app.main:app`

### Database

- PostgreSQL lokal untuk development
- PostgreSQL managed service untuk demo online

### Model Artifacts

- model dibaca dari direktori `ml/model/<experiment>/`
- backend harus tahu `MODEL_PATH` dan `CLASS_INDICES_PATH`

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
- `CORS_ORIGINS`

## Deployment Checklist

1. pastikan database bisa diakses dari runtime backend
2. pastikan `MODEL_PATH` menunjuk model yang benar
3. pastikan `CLASS_INDICES_PATH` cocok dengan model aktif
4. pastikan threshold review untuk model aktif sudah ada
5. pastikan auth endpoint dan detect endpoint lolos smoke test

## Fallback Rule

Jika deploy online belum siap, backend tetap bisa dijalankan lokal untuk integrasi tahap awal. Model inference tidak bergantung pada mobile dan bisa diuji via HTTP client atau TestClient.
