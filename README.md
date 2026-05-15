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

- Backend environment dan ML environment sama-sama diselaraskan ke Python `3.11`.
- ML environment untuk TensorFlow harus memakai Python yang didukung wheel resmi.
- Baseline runtime yang dipakai project ini adalah Python `3.11`.

Jika interpreter aktif masih Python `3.14`, jangan pakai interpreter itu untuk environment backend atau ML karena stack TensorFlow backend inference di project ini mengikuti runtime `3.11`.

### ML Environment

```bash
python3.11 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install -r requirements-ml.txt
```

### ML GPU Runtime Check

Jika environment ML ingin memakai GPU NVIDIA, jalankan interpreter lewat wrapper project ini supaya `LD_LIBRARY_PATH` otomatis memuat runtime libraries dari package TensorFlow GPU.

```bash
./scripts/run_ml_python.sh -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Target output minimal:

```text
[PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
```

### Backend Environment

```bash
python3.11 -m venv .venv-backend
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
