# Security Notes

Dokumen ini menjadi catatan keamanan untuk backend.

## Middleware Order

Urutan middleware konseptual yang dipakai:

1. `CORS`
2. `Auth`
3. `Validation`
4. `RateLimit`
5. `Handler`

## Auth Rules

- Gunakan JWT bearer token untuk endpoint yang membutuhkan identitas user.
- JWT sekarang memiliki `iss` (issuer) dan `aud` (audience) claims untuk mencegah token replay antar service.
- `GET /auth/me` wajib memakai token valid.
- Endpoint admin wajib memakai role check eksplisit.
- Token invalidated otomatis saat user ganti password (via `last_password_change_at` check di `get_current_user`).

## Password Policy

Semua endpoint yang menerima password (`register`, `change-password`) men-validasi:

- Minimal 8 karakter, maksimal 128 karakter
- Harus ada huruf besar (`A-Z`)
- Harus ada huruf kecil (`a-z`)
- Harus ada angka (`0-9`)

## Input Validation Rules

- Request auth harus divalidasi dengan schema Pydantic.
- Request detect wajib memvalidasi `image_url` sebagai URL yang valid.
- Error input harus dikembalikan tanpa menampilkan detail internal backend.
- Field `name` di-sanitize (strip HTML tags) sebelum disimpan.
- Field `email` di-normalize ke lowercase sebelum disimpan dan dibandingkan.

## JWT Security

- Token di-sign dengan HS256 menggunakan `SECRET_KEY`.
- Payload berisi: `sub` (user ID), `iat` (issued at), `exp` (expiry), `iss` (issuer), `aud` (audience).
- `iss` dan `aud` di-validate saat decode — token dari service lain atau issuer berbeda akan ditolak.

## CORS

- CORS origins ditentukan sepenuhnya dari env var `CORS_ORIGINS`.
- Tidak ada hardcoded localhost defaults — semua origin harus di-configure secara eksplisit.
- Production: set `CORS_ORIGINS` ke domain yang diizinkan saja.

## Detect Endpoint Rules

- Backend hanya menerima satu referensi gambar per request.
- Backend wajib menolak URL yang bukan image resource.
- Backend tidak boleh mengembalikan stack trace mentah ke client.

## Secret Rules

- `SECRET_KEY` wajib dibaca dari environment variable.
- `.env` tidak boleh masuk Git.
- Credential database tidak boleh dicetak ke log.

## Role Access Rules

- `user` hanya boleh melihat riwayat miliknya sendiri.
- `admin` boleh mengakses dashboard dan daftar semua deteksi.
- Role check harus dilakukan di dependency layer, bukan hanya di frontend.
- Grad-CAM heatmap (`heatmap_base64`) hanya ditampilkan di admin panel. User-facing pages tidak menampilkan heatmap meskipun data tersedia di response.

## Logging Rules

- Log backend boleh mencatat event umum seperti startup atau error kategori tinggi.
- Log backend tidak boleh mencetak secret, password, atau connection string penuh.
