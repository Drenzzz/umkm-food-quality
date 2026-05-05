# Dataset Flow

Dokumen ini menetapkan alur baku dari dataset publik mentah ke dataset kerja yang siap diproses pipeline ML.

## Flow Overview

```text
source dataset outside project
    -> dataset/external/
    -> dataset/working/raw_public/
    -> dataset/working/normalized/
    -> dataset/working/merged_public/
    -> dataset/final/
```

## Directory Roles

### `dataset/external/`

Tempat representasi sumber dataset publik mentah.

Subfolder aktif:

- `industry_biscuit/`
- `pepsico_potato_lab/`
- `taterdat_chip/`

Direktori ini dipakai untuk menandai asal dataset per sumber, bukan untuk langsung dibaca training script final.

### `dataset/working/raw_public/`

Tempat data publik yang sudah disalin atau disinkronkan ke struktur kerja internal project, tetapi belum dinormalisasi label dan belum dibersihkan penuh.

Subfolder aktif:

- `industry_biscuit/`
- `pepsico_potato_lab/`
- `taterdat_chip/`

### `dataset/working/normalized/`

Tempat data publik yang sudah diubah ke label final biner per sumber.

Struktur yang dipakai:

- `industry_biscuit/layak_jual/`
- `industry_biscuit/tidak_layak_jual/`
- `pepsico_potato_lab/layak_jual/`
- `pepsico_potato_lab/tidak_layak_jual/`
- `taterdat_chip/layak_jual/`
- `taterdat_chip/tidak_layak_jual/`

Tujuan tahap ini adalah mempertahankan asal sumber dataset sambil menyamakan label final.

### `dataset/working/merged_public/`

Tempat gabungan seluruh dataset publik yang sudah memakai label final biner.

Struktur yang dipakai:

- `layak_jual/`
- `tidak_layak_jual/`

Direktori ini akan menjadi kandidat input untuk baseline gabungan publik.

### `dataset/final/`

Tempat split akhir yang nanti dipakai training dan evaluation script.

Direktori ini sengaja belum diisi di step ini karena split train/val/test baru dibuat setelah preprocessing dan metadata siap.

### `dataset/archive/`

Tempat file yang tidak layak dipakai selama proses standardisasi.

Subfolder aktif:

- `rejected/`
- `duplicate/`
- `invalid/`

## Current Baseline Rule

Urutan kerja yang dipakai untuk dataset publik:

1. Dataset mentah tetap ditandai per sumber di `external/`.
2. Data yang disalin ke project masuk ke `working/raw_public/`.
3. Hasil normalisasi label masuk ke `working/normalized/`.
4. Hasil gabungan publik masuk ke `working/merged_public/`.
5. Split training final baru dibuat di `dataset/final/`.

## Why This Layout Exists

Layout ini dipakai supaya preprocessing berikutnya tidak langsung menembak dataset mentah dan supaya setiap perubahan label atau pembersihan data tetap bisa ditelusuri per sumber.
