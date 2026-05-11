# Dataset Gap Notes

Dokumen ini merangkum audit balance label dan gap domain untuk baseline public datasets.

## Total Label Balance

| Label | Count |
|---|---:|
| `layak_jual` | 3 |
| `tidak_layak_jual` | 3 |

## Balance per Dataset Source

| Dataset Slug | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `industry_biscuit` | 1 | 1 |
| `pepsico_potato_lab` | 1 | 1 |
| `taterdat_chip` | 1 | 1 |

## Balance per Product Domain

| Product Domain | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `biskuit_kukis` | 1 | 1 |
| `keripik` | 2 | 2 |

## Split Coverage

| Split | Layak Jual | Tidak Layak Jual |
|---|---:|---:|
| `train` | 3 | 3 |
| `val` | 0 | 0 |
| `test` | 0 | 0 |

## Missing or Deferred Domains

- `kerupuk` belum punya coverage publik aktif di baseline saat ini.

## Key Observations

- Total label publik saat ini masih seimbang antara layak_jual dan tidak_layak_jual.
- Domain kerupuk masih kosong dan tetap menjadi gap utama yang harus ditutup oleh data primer lokal.
- Domain keripik sudah punya dua sumber publik berbeda, sehingga baseline gabungan keripik layak diuji di fase eksperimen berikutnya.
- Domain biskuit_kukis masih bertumpu pada satu sumber utama, sehingga validasi domain lintas sumber nanti tetap penting.
- Split validation dan test masih kosong pada smoke-test ini, yang normal karena ukuran bucket per sumber-label masih sangat kecil.
