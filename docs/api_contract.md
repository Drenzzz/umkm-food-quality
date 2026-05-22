# API Contract

Dokumen ini menjadi kontrak dasar endpoint backend untuk fase awal integrasi model publik.

## Endpoint Groups

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Detection

- `POST /detect`
- `GET /history`
- `GET /history/{detection_id}`

### Admin

- `GET /admin/dashboard`
- `GET /admin/detections`

### Health

- `GET /health`

## Response Envelope Rule

Fase awal backend akan memakai response JSON langsung per endpoint, tanpa wrapper envelope global tambahan. Alasannya supaya kontrak inferensi dan auth tetap sederhana lebih dulu.

## Auth Contracts

### `POST /auth/register`

Request body:

```json
{
  "name": "string",
  "email": "string",
  "password": "string"
}
```

Success response:

```json
{
  "id": 1,
  "name": "string",
  "email": "string",
  "role": "user",
  "created_at": "2026-05-11T12:00:00Z"
}
```

### `POST /auth/login`

Request body:

```json
{
  "email": "string",
  "password": "string"
}
```

Success response:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in_minutes": 60
}
```

### `GET /auth/me`

Success response:

```json
{
  "id": 1,
  "name": "string",
  "email": "string",
  "role": "user",
  "created_at": "2026-05-11T12:00:00Z"
}
```

## Detection Contracts

### `POST /detect`

Request body:

```json
{
  "image_url": "https://example.com/image.jpg"
}
```

Success response:

```json
{
  "id": 1,
  "label": "Tidak Layak Jual",
  "label_key": "tidak_layak_jual",
  "confidence_score": 91.2,
  "raw_score": 0.912,
  "threshold_used": 0.4,
  "model_version": "exp_001_industry_biscuit_only",
  "explanation": "string",
  "image_url": "https://example.com/image.jpg",
  "created_at": "2026-05-11T12:00:00Z"
}
```

### `GET /history`

Success response:

```json
{
  "items": [
    {
      "id": 1,
      "label": "Layak Jual",
      "label_key": "layak_jual",
      "confidence_score": 73.4,
      "image_url": "https://example.com/image.jpg",
      "created_at": "2026-05-11T12:00:00Z"
    }
  ]
}
```

### `GET /history/{detection_id}`

Success response:

```json
{
  "id": 1,
  "label": "Layak Jual",
  "label_key": "layak_jual",
  "confidence_score": 73.4,
  "raw_score": 0.266,
  "threshold_used": 0.4,
  "model_version": "exp_001_industry_biscuit_only",
  "explanation": "string",
  "image_url": "https://example.com/image.jpg",
  "created_at": "2026-05-11T12:00:00Z"
}
```

## Admin Contracts

### `GET /admin/dashboard`

Success response:

```json
{
  "total_detections": 100,
  "total_layak_jual": 45,
  "total_tidak_layak_jual": 55,
  "active_model_version": "exp_001_industry_biscuit_only"
}
```

### `GET /admin/detections`

Success response:

```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "label": "Layak Jual",
      "label_key": "layak_jual",
      "confidence_score": 73.4,
      "model_version": "exp_001_industry_biscuit_only",
      "created_at": "2026-05-11T12:00:00Z"
    }
  ]
}
```

### `GET /admin/detections/{detection_id}`

Success response:

```json
{
  "id": 1,
  "user_id": 1,
  "label": "Tidak Layak Jual",
  "label_key": "tidak_layak_jual",
  "confidence_score": 60.05,
  "raw_score": 0.6005,
  "threshold_used": 0.5,
  "model_version": "exp_001_industry_biscuit_only",
  "explanation": "string",
  "image_url": "https://example.com/image.jpg",
  "created_at": "2026-05-11T12:00:00Z",
  "active_model_id": "exp_001_industry_biscuit_only",
  "prediction_mode": "single_active_model",
  "class_indices": {
    "layak_jual": 0,
    "tidak_layak_jual": 1
  }
}
```

### `GET /admin/models`

Success response:

```json
{
  "active_model_id": "exp_001_industry_biscuit_only",
  "models": [
    {
      "experiment_id": "exp_001_industry_biscuit_only",
      "model_family": "MobileNetV2",
      "threshold": 0.5,
      "status": "trained",
      "is_active": true,
      "model_file_available": true,
      "class_indices_file_available": true,
      "passed_quality_gate": false,
      "collapse_flags": [
        "constant_raw_score",
        "single_class_prediction_dominance",
        "zero_recall_layak_jual"
      ],
      "quality_sample_count": 500
    }
  ]
}
```

## Health Contract

### `GET /health`

Success response:

```json
{
  "status": "ok",
  "database": "unknown",
  "model_loaded": false,
  "model_version": "unknown"
}
```
