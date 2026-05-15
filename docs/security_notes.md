# Security Notes

Dokumen ini menjadi catatan keamanan dasar untuk backend fase awal.

## Middleware Order

Urutan middleware konseptual yang dipakai untuk fase backend ini:

1. `CORS`
2. `Auth`
3. `Validation`
4. `RateLimit`
5. `Handler`

Implementasi middleware penuh akan menyusul di step backend berikutnya, tetapi urutan ini menjadi sumber kebenaran desain.

## Auth Rules

- Gunakan JWT bearer token untuk endpoint yang membutuhkan identitas user.
- `GET /auth/me` wajib memakai token valid.
- Endpoint admin wajib memakai role check eksplisit.

## Input Validation Rules

- Request auth harus divalidasi dengan schema Pydantic.
- Request detect wajib memvalidasi `image_url` sebagai URL yang valid.
- Error input harus dikembalikan tanpa menampilkan detail internal backend.

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

## Logging Rules

- Log backend boleh mencatat event umum seperti startup atau error kategori tinggi.
- Log backend tidak boleh mencetak secret, password, atau connection string penuh.
