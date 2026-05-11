# Dataset Gap Notes

Dokumen ini merangkum audit balance label dan gap domain untuk baseline public datasets.

## Total Label Balance

| Label | Count |
|---|---:|
| `layak_jual` | 2896 |
| `tidak_layak_jual` | 3926 |

## Balance per Dataset Source

| Dataset Slug | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `industry_biscuit` | 1896 | 3004 |
| `pepsico_potato_lab` | 500 | 461 |
| `taterdat_chip` | 500 | 461 |

## Balance per Product Domain

| Product Domain | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `biskuit_kukis` | 1896 | 3004 |
| `keripik` | 1000 | 922 |

## Split Coverage

| Split | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `train` | 2027 | 2749 |
| `val` | 434 | 589 |
| `test` | 435 | 588 |

## Missing or Deferred Domains

- `kerupuk` belum punya coverage publik aktif di baseline saat ini.

## Key Observations

- Total label publik saat ini belum seimbang dan perlu dipantau saat dataset diperbesar.
- Domain kerupuk masih kosong dan tetap menjadi gap utama yang harus ditutup oleh data primer lokal.
- Domain keripik sudah punya dua sumber publik berbeda, sehingga baseline gabungan keripik layak diuji di fase eksperimen berikutnya.
- Domain biskuit_kukis masih bertumpu pada satu sumber utama, sehingga validasi domain lintas sumber nanti tetap penting.
