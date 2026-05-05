# Public Dataset Experiment Scope

Dokumen ini menetapkan scope eksperimen baseline untuk backend + ML dengan fokus penuh pada dataset publik yang sudah tersedia.

## Objective

Tujuan fase baseline adalah membuktikan bahwa pipeline machine learning dan backend inference bisa berjalan end-to-end tanpa menunggu data Google Form.

Fase ini belum ditujukan untuk menghasilkan model final paling representatif untuk semua produk UMKM lokal.

## Active Product Domains

Scope aktif untuk eksperimen baseline:

- `keripik`
- `biskuit`
- `kukis`

Scope yang belum aktif di baseline publik:

- `kerupuk`

`kerupuk` belum dimasukkan ke eksperimen baseline karena saat ini belum ada dataset publik yang cukup kuat dan konsisten untuk domain tersebut.

## Public Dataset Roles

### 1. IndustryBiscuit

Peran:

- sumber utama domain `biskuit`
- sumber utama domain `kukis`

Alasan:

- ukuran dataset paling besar
- anotasi class paling eksplisit
- paling dekat ke produk kering berbasis biskuit

### 2. taterdat-chip

Peran:

- sumber utama domain `keripik`

Alasan:

- struktur folder sederhana untuk baseline binary classification
- sudah kamu tetapkan sebagai domain keripik

### 3. Pepsico RnD Potato Lab Dataset

Peran:

- sumber pendamping domain `keripik`
- sumber validasi domain chips dari vendor berbeda

Alasan:

- sudah punya train/test bawaan
- masih dekat dengan domain keripik atau chips
- berguna untuk cek apakah model terlalu bias ke satu sumber data

## Baseline Experiment Order

Urutan eksperimen baseline yang akan dipakai:

### Experiment 1 - IndustryBiscuit Only

Fokus:

- membangun baseline untuk `biskuit/kukis`
- memvalidasi pipeline preprocessing, training, dan evaluation pada dataset yang paling stabil

Output yang diharapkan:

- model baseline domain `biskuit/kukis`
- metrik awal untuk `layak_jual` vs `tidak_layak_jual`

### Experiment 2 - taterdat-chip Only

Fokus:

- membangun baseline pertama untuk `keripik`
- memvalidasi pipeline binary classification pada dataset folder-based yang sederhana

Output yang diharapkan:

- model baseline domain `keripik`
- metrik awal domain keripik dari satu sumber publik

### Experiment 3 - Pepsico Only

Fokus:

- membangun baseline kedua untuk `keripik`
- mengecek stabilitas pipeline pada dataset yang punya split bawaan dan penamaan class berbeda

Output yang diharapkan:

- model baseline kedua domain `keripik`
- catatan mismatch atau perbedaan performa terhadap `taterdat-chip`

### Experiment 4 - Combined Keripik Public Datasets

Fokus:

- menggabungkan `taterdat-chip` dan `Pepsico`
- melihat apakah baseline keripik lebih stabil setelah domain chips diperkaya dari dua sumber

Output yang diharapkan:

- model baseline gabungan untuk `keripik`
- indikasi awal apakah gabungan dua dataset publik membantu atau justru menambah noise domain

### Experiment 5 - Combined Public Baseline

Fokus:

- menggabungkan domain `biskuit/kukis` dan `keripik`
- menghasilkan model baseline lintas-domain untuk integrasi backend awal

Output yang diharapkan:

- satu model baseline publik yang cukup untuk integrasi endpoint `/detect`
- catatan risiko saat model digunakan di luar domain publik

## Decision Rules

Aturan keputusan selama fase baseline:

1. `IndustryBiscuit` tidak dicampur ke eksperimen keripik-only.
2. `taterdat-chip` dan `Pepsico` boleh digabung hanya setelah baseline masing-masing selesai.
3. `kerupuk` tidak dipaksa ikut sampai data primer lokal cukup.
4. Data Google Form tidak dibutuhkan untuk memulai eksperimen baseline.
5. Model baseline publik boleh dipakai backend lebih dulu, tetapi tidak dianggap model final capstone.

## Success Criteria for This Phase

Fase eksperimen publik dianggap cukup jika:

1. Pipeline preprocessing dapat membaca semua dataset aktif tanpa konflik label.
2. Pipeline training dapat menghasilkan artefak model dan `class_indices.json`.
3. Pipeline evaluation dapat menghasilkan metrik klasifikasi yang konsisten.
4. Satu model baseline publik dapat dipakai untuk integrasi backend awal.

## Deferred Scope

Hal yang sengaja ditunda ke fase berikutnya:

- integrasi `kerupuk` sebagai domain aktif
- retraining dengan data Google Form
- threshold tuning final berbasis data primer lokal
- validasi final terhadap foto smartphone nyata

## Google Form Integration Timing

Data Google Form masuk setelah jumlahnya cukup untuk menjadi refinement layer.

Saat data form mulai memadai, step berikutnya adalah:

1. ubah response form menjadi image-level records
2. review dan kurasi data primer
3. merge ke metadata utama
4. retrain atau fine-tune model baseline
5. evaluasi ulang threshold dan performa akhir
