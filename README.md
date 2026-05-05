# UMKM Food Quality

Struktur awal project ini difokuskan untuk dua domain utama:

- `ml/` untuk pipeline dataset, training, evaluasi, dan artefak model
- `app/` untuk backend API berbasis Python

Struktur ini sengaja dipisah dari mobile agar pengembangan backend dan machine learning bisa stabil lebih dulu.

## Root Layout

```text
umkm-food-quality/
├── app/
├── dataset/
├── docs/
├── ml/
├── scripts/
└── tests/
```

## Environment Strategy

Project ini memakai dua dependency set yang dipisah dari awal:

- `requirements-ml.txt` untuk preprocessing, training, evaluasi, dan eksperimen notebook
- `requirements-backend.txt` untuk FastAPI, database, auth, dan model serving

Pemisahan ini dipakai supaya dependency training tidak mengganggu dependency backend, dan sebaliknya.

## Local Setup

Disarankan memakai dua virtual environment terpisah.

### Python Compatibility

- Backend environment saat ini sudah aman di Python `3.14`.
- ML environment untuk TensorFlow harus memakai Python yang didukung wheel resmi.
- Baseline yang dipakai project ini adalah Python `3.11` untuk ML.

Jika interpreter aktif masih Python `3.14`, jangan pakai interpreter itu untuk environment ML karena `tensorflow==2.16.1` tidak menyediakan wheel untuk versi tersebut.

### ML Environment

```bash
python3.11 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install -r requirements-ml.txt
```

### Backend Environment

```bash
python -m venv .venv-backend
source .venv-backend/bin/activate
python -m pip install -r requirements-backend.txt
```

## Environment Variables

Salin file contoh environment lebih dulu:

```bash
cp .env.example .env
```

Variable yang sudah disiapkan untuk fase awal:

- `APP_ENV`
- `DATABASE_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `MODEL_PATH`
- `CLASS_INDICES_PATH`
- `CORS_ORIGINS`

Referensi detail arti tiap variable dan aturan secret ada di `docs/environment_variables.md`.
