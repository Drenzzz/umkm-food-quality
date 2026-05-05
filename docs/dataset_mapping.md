# Public Dataset Mapping

Dokumen ini menetapkan mapping label final untuk dataset publik yang saat ini dipakai sebagai pondasi baseline backend + ML.

## Scope Saat Ini

Dataset publik dipakai untuk membangun baseline awal tanpa menunggu data Google Form.

- `IndustryBiscuit` diposisikan untuk domain `biskuit` dan `kukis`
- `taterdat-chip` diposisikan untuk domain `keripik`
- `Pepsico RnD Potato Lab Dataset` diposisikan untuk domain `keripik`

`kerupuk` belum punya dataset publik yang kuat di fase ini. Domain tersebut akan ditutup nanti lewat data primer dari Google Form atau koleksi manual.

## Binary Labels

Label final yang dipakai untuk seluruh pipeline baseline:

- `layak_jual`
- `tidak_layak_jual`

## Dataset Rules

### 1. IndustryBiscuit

Sumber struktur label:

- file anotasi: `dataset/IndustryBiscuit/Annotations.csv`

Mapping final:

| Source Label | Final Label |
|---|---|
| `Defect_No` | `layak_jual` |
| `Defect_Shape` | `tidak_layak_jual` |
| `Defect_Object` | `tidak_layak_jual` |
| `Defect_Color` | `tidak_layak_jual` |

Catatan:

- Dataset ini menjadi referensi utama untuk produk kering berbasis biskuit.
- Label cacat tetap disimpan di metadata agar nanti analisis error per defect tetap bisa dilakukan.

### 2. taterdat-chip

Sumber struktur label:

- folder: `dataset/taterdat-chip/`

Mapping final:

| Source Label | Final Label |
|---|---|
| `Non-Defective` | `layak_jual` |
| `Defective` | `tidak_layak_jual` |

Catatan:

- Dataset ini diperlakukan sebagai domain `keripik`.
- Nama folder aktual sekarang adalah `taterdat-chip`, jadi semua script berikutnya harus mengikuti nama ini, bukan `taterdat` lama.

### 3. Pepsico RnD Potato Lab Dataset

Sumber struktur label:

- folder: `dataset/Pepsico RnD Potato Lab Dataset/Train`
- folder: `dataset/Pepsico RnD Potato Lab Dataset/Test`

Mapping final:

| Source Label | Final Label |
|---|---|
| `Non-Defective` | `layak_jual` |
| `Not Defective` | `layak_jual` |
| `Defective` | `tidak_layak_jual` |

Catatan:

- Perbedaan nama `Non-Defective` dan `Not Defective` harus dinormalisasi saat preprocessing.
- Dataset ini juga diperlakukan sebagai domain `keripik` atau `chips`.

## Current Dataset Snapshot

Snapshot ini dipakai sebagai baseline audit saat roadmap disetujui:

| Dataset | Source Class | Count |
|---|---|---:|
| IndustryBiscuit | `Defect_No` | 1896 |
| IndustryBiscuit | `Defect_Shape` | 1860 |
| IndustryBiscuit | `Defect_Object` | 632 |
| IndustryBiscuit | `Defect_Color` | 512 |
| taterdat-chip | `Non-Defective` | 500 |
| taterdat-chip | `Defective` | 461 |
| Pepsico Train | `Non-Defective` | 400 |
| Pepsico Train | `Defective` | 369 |
| Pepsico Test | `Not Defective` | 100 |
| Pepsico Test | `Defective` | 92 |

## Operational Decision

Untuk fase baseline, keputusan kerja yang dipakai adalah:

1. Baseline `biskuit/kukis` bertumpu pada `IndustryBiscuit`.
2. Baseline `keripik` bertumpu pada `taterdat-chip` dan `Pepsico`.
3. `kerupuk` ditandai sebagai gap domain dan tidak dipaksa dipenuhi dari dataset publik saat ini.
4. Data Google Form nanti masuk sebagai refinement layer, bukan syarat untuk memulai pipeline baseline.
