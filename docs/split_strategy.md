# Public Baseline Split Strategy

Dokumen ini menetapkan strategi split khusus untuk baseline public datasets.

## Input

Input split di fase ini berasal dari:

- `dataset/metadata/public_metadata.csv`

Metadata tersebut dibentuk dari hasil preprocessing publik yang sudah berada di:

- `dataset/working/normalized/`

## Grouping Rule

Split tidak dilakukan secara acak global. Split dilakukan per bucket:

- `dataset_slug`
- `final_label`

Contoh bucket:

- `industry_biscuit + layak_jual`
- `industry_biscuit + tidak_layak_jual`
- `taterdat_chip + layak_jual`

Pendekatan ini dipakai supaya setiap sumber dataset tetap punya representasi label sendiri di baseline publik.

## Baseline Distribution Rule

Target normal saat jumlah data cukup:

- `70% train`
- `15% val`
- `15% test`

Namun untuk bucket kecil, aturan fallback berikut dipakai:

| Bucket Size | Split Result |
|---|---|
| `1` | `train` |
| `2` | `train`, `test` |
| `3` | `train`, `val`, `test` |
| `>=4` | rasio `70/15/15` dengan penyesuaian minimum agar semua split tetap valid |

## Why This Fallback Exists

Smoke-test awal sekarang memang masih sangat kecil. Jika split dipaksa selalu `70/15/15`, beberapa bucket akan menghasilkan split kosong atau tidak stabil. Karena itu fallback dipakai agar pipeline tetap bisa diuji dari awal tanpa menunggu dataset penuh.

## Output

Split menghasilkan dua output utama:

1. File metadata hasil split:
   - `dataset/metadata/split_metadata.csv`
2. Struktur folder final:
   - `dataset/final/train/layak_jual/`
   - `dataset/final/train/tidak_layak_jual/`
   - `dataset/final/val/layak_jual/`
   - `dataset/final/val/tidak_layak_jual/`
   - `dataset/final/test/layak_jual/`
   - `dataset/final/test/tidak_layak_jual/`

## Current Baseline Note

Dengan data smoke-test saat ini, kemungkinan besar distribusi final akan kecil dan tidak mewakili training sesungguhnya. Itu normal. Tujuan fase ini adalah membuktikan mekanisme split dan materialisasi folder final sudah jalan.
