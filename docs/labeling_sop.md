# Labeling SOP

Dokumen ini menjadi SOP review data primer dari Google Form, manual collection, dan scraping.

## Label Final

Label review final yang dipakai:

- `layak_jual`
- `tidak_layak_jual`
- `uncertain`

## Product Scope

Scope utama saat ini:

- `keripik`
- `kerupuk`
- `biskuit`
- `kukis`

## Defect Categories

Kategori defect review yang dipakai:

- `none`
- `gosong`
- `patah_remuk`
- `warna_tidak_normal`
- `bercak_noda`
- `bentuk_tidak_utuh`
- `campuran`
- `uncertain`

## Review Rules

### `layak_jual`

Gunakan jika:

- warna terlihat normal untuk jenis produk
- bentuk produk masih utuh atau hanya ada cacat minor
- permukaan terlihat bersih dan wajar
- tampilan produk masih realistis untuk dipasarkan

### `tidak_layak_jual`

Gunakan jika ada indikasi kuat:

- gosong dominan
- remuk atau patah parah
- warna tidak normal secara jelas
- bercak atau noda yang bukan bagian normal produk
- bentuk produk rusak sehingga kualitas visual turun jelas

### `uncertain`

Gunakan jika:

- foto blur
- objek terlalu jauh
- pencahayaan terlalu buruk
- label antara layak dan tidak layak masih meragukan
- produk keluar dari scope utama

## Review Workflow

1. Data primer masuk ke `dataset/incoming/`
2. Parser mengubah response form menjadi image-level metadata
3. Reviewer memeriksa gambar satu per satu
4. Reviewer mengisi:
   - `label_review`
   - `jenis_cacat_review`
   - `review_status`
5. Hanya data dengan `review_status=approved` yang boleh masuk merge metadata utama

## Metadata Review Status

Status review yang dipakai:

- `pending_review`
- `approved`
- `uncertain`
- `rejected`

## Naming Rule

Nama file hasil rename primer disarankan sederhana dan stabil.

Contoh:

```text
keripik_000001.jpg
biskuit_000001.jpg
```

Detail label, defect, dan source tetap disimpan di metadata CSV, bukan dipaksa masuk semua ke nama file.
