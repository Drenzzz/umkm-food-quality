# Public Baseline Results

Dokumen ini merangkum hasil baseline utama per sumber dataset publik.

## Experiments

| Experiment | Source Scope | Status |
|---|---|---|
| `exp_001_industry_biscuit_only` | `industry_biscuit` | completed |
| `exp_002_taterdat_chip_only` | `taterdat_chip` | completed |
| `exp_003_pepsico_only` | `pepsico_potato_lab` | completed |
| `exp_005_combined_public_baseline` | `industry_biscuit + taterdat_chip + pepsico_potato_lab` | completed |

## Metrics Snapshot

| Experiment | Used Split | Accuracy | Precision Macro | Recall Macro | F1 Macro | Recall Tidak Layak Jual | Recommended Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| `exp_001_industry_biscuit_only` | `test` | 0.6122 | 0.3061 | 0.5000 | 0.3797 | 1.0000 | 0.50 |
| `exp_002_taterdat_chip_only` | `test` | 0.5208 | 0.2604 | 0.5000 | 0.3425 | 0.0000 | 0.40 |
| `exp_003_pepsico_only` | `test` | 0.5208 | 0.2604 | 0.5000 | 0.3425 | 0.0000 | 0.40 |
| `exp_005_combined_public_baseline` | `test` | 0.7898 | 0.8346 | 0.8172 | 0.7891 | 0.6344 | 0.10 |

## Notes

- `exp_005_combined_public_baseline` saat ini menjadi baseline global paling sehat setelah training hardening dan quality gate validation.
- `exp_001_industry_biscuit_only` masih berguna sebagai reference baseline domain `biskuit_kukis`, tetapi bukan lagi kandidat active model terbaik.
- `exp_002_taterdat_chip_only` dan `exp_003_pepsico_only` masih gagal quality gate dan tidak layak dipakai sebagai active model.
- Seluruh eksperimen baseline menghasilkan artefak lengkap: model, class indices, training history, training log, evaluation report, confusion matrix, threshold review, dan artifact manifest.

## Active Public Model

Model aktif untuk backend saat ini adalah:

- `exp_005_combined_public_baseline`

Alasan pemilihan:

- lolos quality gate dengan `raw_score_unique_count` tinggi dan tanpa collapse flags
- memiliki metrik test yang lebih baik secara keseluruhan dibanding baseline source tunggal
- threshold review dan artifact lengkap untuk backend integration
