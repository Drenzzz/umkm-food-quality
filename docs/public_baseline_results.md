# Public Baseline Results

Dokumen ini merangkum hasil baseline utama per sumber dataset publik.

## Experiments

| Experiment | Source Scope | Status |
|---|---|---|
| `exp_001_industry_biscuit_only` | `industry_biscuit` | completed |
| `exp_002_taterdat_chip_only` | `taterdat_chip` | completed |
| `exp_003_pepsico_only` | `pepsico_potato_lab` | completed |

## Metrics Snapshot

| Experiment | Used Split | Accuracy | Precision Macro | Recall Macro | F1 Macro | Recall Tidak Layak Jual | Recommended Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| `exp_001_industry_biscuit_only` | `test` | 0.6122 | 0.3061 | 0.5000 | 0.3797 | 1.0000 | 0.50 |
| `exp_002_taterdat_chip_only` | `test` | 0.5208 | 0.2604 | 0.5000 | 0.3425 | 0.0000 | 0.40 |
| `exp_003_pepsico_only` | `test` | 0.5208 | 0.2604 | 0.5000 | 0.3425 | 0.0000 | 0.40 |

## Notes

- `industry_biscuit` saat ini menjadi baseline paling aman untuk domain `biskuit_kukis`, terutama karena `recall_tidak_layak_jual` mencapai `1.0` pada run baseline ini.
- `taterdat_chip` dan `pepsico_potato_lab` masih memberi baseline keripik yang lemah pada prioritas recall `tidak_layak_jual`, sehingga eksperimen gabungan keripik menjadi penting untuk step berikutnya.
- Ketiga eksperimen utama sudah menghasilkan artefak lengkap: model, class indices, training history, training log, evaluation report, confusion matrix, dan threshold review.
- Hasil ini masih baseline publik dan belum memasukkan data primer lokal dari Google Form, manual collection, atau scraping tambahan.
