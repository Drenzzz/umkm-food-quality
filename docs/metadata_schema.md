# Metadata Schema

Dokumen ini menetapkan skema metadata gabungan untuk public dataset dan primary dataset.

## Canonical Metadata Rule

Semua image metadata yang akan dipakai pipeline final harus berada dalam satu skema yang sama, walau sumbernya berbeda.

Sumber metadata yang didukung:

- `public`
- `form`
- `manual`
- `scrape`

## Canonical Columns

| Column | Purpose |
|---|---|
| `image_id` | Identifier unik per image row. |
| `source_type` | Tipe sumber data, misalnya `public` atau `form`. |
| `source_batch` | Batch sumber untuk tracing. |
| `submitted_at` | Waktu submit jika sumbernya form. |
| `nama_pengirim` | Nama pengirim form atau collector. |
| `nomor_whatsapp` | Kontak form jika tersedia. |
| `nama_usaha` | Nama usaha jika tersedia. |
| `nama_produk` | Nama produk dari sumber primer. |
| `jenis_produk` | Jenis produk granular. |
| `jenis_produk_detail` | Detail produk tambahan jika ada. |
| `product_domain` | Domain utama seperti `keripik`, `kerupuk`, atau `biskuit_kukis`. |
| `is_sold_product` | Penanda apakah produk memang dijual atau tidak. |
| `label_form` | Label awal dari responden atau input sumber. |
| `jenis_cacat_form` | Kategori defect dari sumber primer. |
| `catatan_cacat` | Catatan defect tambahan. |
| `file_url` | URL file jika sumbernya form atau scrape. |
| `file_name` | Nama file asli yang diketahui dari sumber primer. |
| `filename` | Nama file lokal hasil preprocessing atau rename. |
| `relative_path` | Path lokal relatif ke project untuk image yang sudah tersedia. |
| `dataset_name` | Nama dataset sumber. |
| `dataset_slug` | Slug dataset sumber. |
| `source_group` | Grup sumber seperti `public_dataset` atau `form`. |
| `notes` | Catatan bebas tambahan. |
| `consent_status` | Status izin penggunaan data. |
| `label_review` | Label final setelah review. |
| `jenis_cacat_review` | Kategori defect final setelah review. |
| `review_status` | Status review seperti `approved` atau `pending_review`. |
| `split` | Split training jika sudah ditentukan. |

## Merge Rule

### Public Metadata

- `label_form` diisi sama dengan `final_label`
- `label_review` diisi sama dengan `final_label`
- `consent_status` diisi `not_required`
- `source_batch` diisi `public-baseline`

### Primary Metadata

- `label_form` diambil dari sumber primer
- `label_review` bisa kosong sampai review selesai
- `review_status` default `pending_review`
- `relative_path` bisa kosong sampai file lokal final tersedia

## Current Merge Strategy

Tahap merge saat ini hanya menyatukan metadata public dan metadata primary ke skema kanonik. Ini belum otomatis menyatukan image file ke split training akhir. Tujuan step ini adalah memastikan kedua sumber data bisa hidup dalam satu format metadata terlebih dahulu.
