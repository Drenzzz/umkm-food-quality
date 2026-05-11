# Threshold Policy

Dokumen ini menetapkan policy review threshold sigmoid untuk baseline model publik.

## Default Starting Point

Threshold default yang dipakai saat evaluasi awal adalah:

- `0.50`

Nilai ini hanya dipakai sebagai titik awal, bukan keputusan final permanen.

## Priority Rule

Metric prioritas utama untuk review threshold adalah:

- `recall_tidak_layak_jual`

Alasannya, kesalahan paling berisiko pada sistem ini adalah produk `tidak_layak_jual` yang lolos menjadi `layak_jual`.

## Threshold Sweep Rule

Threshold review dilakukan dengan sweep rentang nilai sigmoid. Baseline awal memakai rentang:

- start: `0.10`
- stop: `0.90`
- step: `0.10`

## Tie-Break Rule

Jika beberapa threshold punya nilai `recall_tidak_layak_jual` yang sama, pemilihan kandidat terbaik mengikuti urutan:

1. `recall_tidak_layak_jual`
2. `f1_macro`
3. `precision_macro`
4. kedekatan ke `0.50`

## Report Output

Hasil review threshold disimpan di:

- `ml/model/<experiment>/evaluation/threshold_review.json`

File ini harus memuat:

- daftar threshold yang diuji
- metric per threshold
- recommended threshold akhir

## Current Smoke-Test Note

Pada dataset smoke-test kecil, threshold review belum bisa dipakai untuk keputusan model final. Namun step ini tetap penting untuk membuktikan mekanisme review threshold dan format report sudah stabil.
