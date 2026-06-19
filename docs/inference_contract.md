# Inference Contract

Dokumen ini mengunci kontrak inferensi model baseline publik yang akan dipakai backend.

## Input

Backend menerima satu referensi gambar per request.

Request body:

```json
{
  "image_url": "https://example.com/image.jpg"
}
```

## Output Fields

Response inferensi wajib memuat field berikut:

| Field | Type | Description |
|---|---|---|
| `id` | integer | Identifier hasil deteksi yang tersimpan di database. |
| `label` | string | Label ramah user, misalnya `Layak Jual`. |
| `label_key` | string | Label internal, misalnya `layak_jual`. |
| `confidence_score` | number | Confidence dalam skala persen. |
| `raw_score` | number | Skor sigmoid mentah dari model. |
| `threshold_used` | number | Threshold aktif yang dipakai backend. |
| `model_version` | string | Nama eksperimen atau versi model aktif. |
| `explanation` | string | Penjelasan singkat hasil inferensi. |
| `image_url` | string | Referensi gambar yang dikirim ke backend. |
| `created_at` | string | Waktu hasil deteksi dicatat. |

## Label Mapping Rule

Mapping internal yang dipakai di fase awal:

- `0 -> layak_jual`
- `1 -> tidak_layak_jual`

Backend harus selalu membaca `class_indices.json` dari model aktif untuk menghindari label terbalik.

## Threshold Rule

The active threshold is configured per model in `active_model.json`. The current active model uses threshold `0.3`.

```text
raw_score < 0.3  -> layak_jual    (confidence = 1 - raw_score)
raw_score >= 0.3 -> tidak_layak_jual (confidence = raw_score)
```

Threshold aktif harus mengikuti artefak model yang dipilih untuk backend. Jangan hardcode threshold — baca dari `active_model.json` atau manifest model.

## Active Model Rule

Backend hanya boleh memakai **satu model aktif** pada satu waktu. Model aktif harus dipilih dari hasil baseline publik yang sudah dievaluasi lengkap.

Model aktif saat ini:

- `umkm_food_quality_v1` (MobileNetV2, threshold 0.3)

Sumber kebenaran pemilihan model aktif:

- `ml/model/active_model.json`

Backend membaca registry model dari `MODEL_REGISTRY_PATH` dan memilih model aktif dari `ACTIVE_MODEL_CONFIG_PATH`. Jika konfigurasi aktif belum tersedia, backend memakai `MODEL_PATH` dan `CLASS_INDICES_PATH` sebagai fallback compatibility.

## Error Rule

Jika inferensi gagal, backend harus mengembalikan error yang tidak membocorkan detail internal seperti path file lokal, credential, atau stack trace mentah.
