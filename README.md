# UMKM Food Quality

Sistem deteksi kualitas visual produk makanan kering UMKM berbasis MobileNetV2 + FastAPI.

Struktur project ini difokuskan untuk dua domain utama:

- `ml/` untuk pipeline dataset, training, evaluasi, dan artefak model
- `app/` untuk backend API berbasis Python

Struktur ini sengaja dipisah dari mobile agar pengembangan backend dan machine learning bisa stabil lebih dulu.

## Root Layout

```text
umkm-food-quality/
├── app/                 # FastAPI backend (API, auth, ML inference)
├── dataset/             # Dataset (not committed)
├── deploy/              # Docker, Caddy, deployment scripts
├── docs/                # Technical documentation
├── ml/                  # ML pipeline (train, evaluate, artifacts)
├── scripts/             # Utility scripts
└── tests/               # Automated tests
```

## Environment Strategy

Project ini memakai tiga dependency set:

- `requirements-ml.txt` untuk preprocessing, training, evaluasi, dan eksperimen notebook
- `requirements-backend.txt` untuk FastAPI, database, auth, dan model serving (production, pinned versions)
- `requirements-dev.txt` untuk testing dependencies (pytest, respx)

## Local Setup

Disarankan memakai dua virtual environment terpisah.

### Python Compatibility

Baseline runtime yang dipakai project ini adalah Python `3.11`.

### ML Environment

```bash
python3.11 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install -r requirements-ml.txt
```

### ML GPU Runtime Check

```bash
./scripts/run_ml_python.sh -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### Backend Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
pip install -r requirements-dev.txt
```

### Run Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `http://localhost:8000/health`

## Environment Variables

Salin file contoh environment lebih dulu:

```bash
cp .env.example .env
```

Referensi detail arti tiap variable dan aturan secret ada di `.env.example` dan `docs/environment_variables.md`.

Generate secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Repository Boundary

Aturan file yang boleh masuk repo dan yang harus tetap lokal didokumentasikan di `docs/repo_strategy.md`.

## Auth & Security

Backend menggunakan JWT (HS256) untuk autentikasi. Fitur autentikasi meliputi:

- Register, login, update profile, ganti password, hapus akun
- Password policy: minimal 8 karakter, harus ada huruf besar, kecil, dan angka
- Email di-normalize ke lowercase sebelum disimpan
- JWT memiliki `iss` dan `aud` claims
- Token invalidated otomatis saat user ganti password
- Rate limiting di semua endpoint
- SSRF protection di endpoint `/detect`
- Docker container berjalan sebagai non-root user

## API Endpoints

| Group | Endpoints | Auth |
|---|---|---|
| Health | `GET /health` | No |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET/PATCH /auth/me`, `POST /auth/change-password`, `DELETE /auth/me` | Yes |
| Detect | `POST /detect` | Yes |
| History | `GET /history`, `GET /history/latest`, `GET /history/{id}`, `DELETE /history/{id}`, `DELETE /history` | Yes |
| Admin | `GET /admin/dashboard`, `GET /admin/detections`, `GET /admin/models`, `POST /admin/detect/compare` | Admin |

## Deployment

Deployment ke VPS menggunakan Docker Compose. Lihat `deploy/` untuk:

- `Dockerfile` — multi-stage build, non-root user
- `docker-compose.yml` — db, api, caddy
- `deploy.sh` — automated deployment script
- `Caddyfile` — reverse proxy config with automatic HTTPS
