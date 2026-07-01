# Repository Strategy

Dokumen ini menetapkan boundary antara source code yang boleh masuk Git dan artefak lokal yang harus tetap di luar repo.

## What Goes Into Git

File yang boleh masuk repository:

- source code backend di `app/`
- source code ML dan script pipeline di `ml/` dan `scripts/`
- dokumen perencanaan, kontrak API, dan catatan operasional di `docs/`
- metadata contoh kecil yang memang dipakai untuk demonstrasi struktur file
- file konfigurasi seperti `.env.example`, `requirements-ml.txt`, `requirements-backend.txt`, dan `README.md`

## What Must Stay Local

File berikut harus tetap lokal dan tidak boleh dijadikan bagian normal dari repository:

- `.env`
- seluruh virtual environment lokal
- output preprocessing penuh di `dataset/final/`
- file archive hasil pembersihan dataset
- metadata hasil merge yang mengandung data primer real seperti `master_metadata.csv`
- metadata hasil parser form real seperti `form_image_metadata.csv`

## What Is Tracked for Reproducibility

File berikut **di-track ke Git** agar setelah clone backend bisa langsung jalan tanpa retrain:

- `ml/model/umkm_food_quality_v1/model.keras` — model trained
- `ml/model/umkm_food_quality_v1/class_indices.json` — label mapping
- `ml/model/umkm_food_quality_v1/model.tflite` + `model.onnx` — exported models
- `ml/model/umkm_food_quality_v1/evaluation/` — evaluation reports
- `ml/model/active_model.json` — active model selector
- `dataset/working/manual_normalized/` — trained dataset images (739 files)

## Why This Boundary Exists

Boundary ini dipakai supaya:

1. repository tetap ringan
2. history Git fokus ke code dan dokumen, bukan file generated besar
3. data primer dari form/manual tidak tersebar ke repo secara tidak sengaja
4. artefak eksperimen bisa diulang lokal tanpa memenuhi commit history

## Artifact Policy

### ML Artifacts

Artefak model (`.keras`, `.tflite`, `.onnx`, `class_indices.json`, evaluation reports) **di-track ke Git** agar reproducible. Clone → langsung jalan tanpa retrain.

Artefak yang tetap di-ignore:
- `ml/model/*.h5`, `ml/model/*.ckpt` (format lama)
- `ml/model/**/artifact_manifest.json` (metadata internal training)

### Primary Data Artifacts

Artefak data primer diperlakukan lebih ketat karena bisa mengandung sumber form, informasi pengirim, atau file yang masih menunggu review.

## Git Ignore Rule

`.gitignore` harus memblokir minimal:

- `.env` dan turunannya
- `.venv-*`
- `dataset/final/`
- `dataset/archive/**/*.txt`
- `dataset/metadata/master_metadata.csv`
- `dataset/metadata/form_image_metadata.csv`
- `ml/model/*.h5`, `ml/model/*.ckpt`
- `ml/model/**/artifact_manifest.json`

## Commit Rule

Jika ada file baru yang muncul setelah training, preprocessing, atau evaluation run:

1. cek dulu apakah file itu source code, dokumen, atau generated artifact
2. jika generated artifact, tambahkan ke `.gitignore` bila perlu
3. jangan commit artifact hanya karena muncul di `git status`

## Recommended Storage Outside Git

Untuk file besar atau sensitif, gunakan:

- local disk
- external drive
- private cloud storage
- Google Drive

## Current Rule of Thumb

Jika file tersebut tidak dibutuhkan untuk me-*rebuild* logic aplikasi dari nol, besar kemungkinan file itu tidak perlu masuk Git.
