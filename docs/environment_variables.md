# Environment Variables

Dokumen ini menjadi acuan utama untuk environment variable backend + ML pada fase baseline.

## Current Baseline Variables

| Variable | Required | Example | Purpose |
|---|---|---|---|
| `APP_ENV` | Yes | `development` | Menandai konteks runtime aktif seperti development atau production. |
| `DATABASE_URL` | Yes | `postgresql://app_user:change_me@localhost:5432/umkm_food_quality` | Connection string database backend. |
| `SECRET_KEY` | Yes | `change-this-secret-key` | Kunci untuk signing token dan kebutuhan security backend. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | `60` | Masa berlaku access token dalam menit. |
| `MODEL_PATH` | Yes | `ml/model/mobilenetv2_umkm.keras` | Lokasi model inference yang akan dibaca backend. |
| `CLASS_INDICES_PATH` | Yes | `ml/model/class_indices.json` | Lokasi file mapping label hasil training. |
| `CORS_ORIGINS` | Yes | `http://localhost:3000,http://localhost:5173` | Daftar origin yang diizinkan untuk akses frontend atau client. |

## Value Rules

### `APP_ENV`

Nilai yang dipakai di fase awal:

- `development`
- `production`

### `DATABASE_URL`

Rules:

- wajib memakai connection string penuh
- jangan simpan credential database produksi di repo
- untuk local development, pakai user database khusus project

### `SECRET_KEY`

Rules:

- wajib diganti dari placeholder sebelum auth aktif dipakai
- jangan gunakan string pendek atau gampang ditebak
- jangan dicetak ke log atau response API

### `ACCESS_TOKEN_EXPIRE_MINUTES`

Rules:

- gunakan angka bulat positif
- untuk local baseline, nilai `60` dianggap aman

### `MODEL_PATH`

Rules:

- harus menunjuk ke artefak model final yang valid
- backend tidak boleh menebak nama model secara hardcoded di banyak tempat

### `CLASS_INDICES_PATH`

Rules:

- harus selalu satu paket dengan model yang aktif
- jika model diganti, file ini juga harus ikut diperbarui

### `CORS_ORIGINS`

Rules:

- isi dipisah dengan koma
- untuk development cukup isi origin lokal yang benar-benar dipakai
- jangan membuka origin terlalu lebar di production tanpa alasan jelas

## Secret Handling Policy

Aturan secret untuk project ini:

1. File `.env` hanya untuk local runtime dan tidak boleh masuk Git.
2. File `.env.example` hanya berisi placeholder aman, bukan nilai rahasia nyata.
3. Secret seperti `SECRET_KEY` dan credential database tidak boleh ditulis di source code.
4. Log aplikasi tidak boleh mencetak isi secret atau connection string lengkap.
5. Saat deploy, secret harus diisi lewat environment setting platform deployment, bukan dengan commit file `.env`.

## Baseline Local Workflow

Urutan pakai untuk local setup:

```bash
cp .env.example .env
```

Lalu edit `.env` dan sesuaikan minimal:

- `DATABASE_URL`
- `SECRET_KEY`
- `MODEL_PATH`
- `CLASS_INDICES_PATH`

Untuk environment backend dan ML, runtime baseline yang dipakai project ini adalah Python `3.11`.

## Change Policy

Jika ada env var baru di fase berikutnya:

1. tambahkan dulu ke `.env.example`
2. dokumentasikan di file ini
3. baru dipakai di kode backend atau script ML
