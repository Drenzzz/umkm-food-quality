# API Contract

Backend API contract for UMKM Food Quality detection service.

## Endpoint Groups

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/me`
- `POST /auth/change-password`
- `DELETE /auth/me`

### Detection

- `POST /detect`

### History

- `GET /history`
- `GET /history/latest`
- `GET /history/{detection_id}`
- `DELETE /history/{detection_id}`
- `DELETE /history` (bulk)

### Admin

- `GET /admin/dashboard`
- `GET /admin/models`
- `GET /admin/detections`
- `GET /admin/detections/{detection_id}`
- `POST /admin/detect/compare`

### Health

- `GET /health`

## Response Envelope Rule

Backend returns plain JSON per endpoint, no global wrapper envelope. Keeps inference and auth contracts simple.

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

Validation rules:
- `name`: 2-100 characters. HTML tags are stripped automatically.
- `email`: valid email format. Normalized to lowercase before storage.
- `password`: 8-128 characters. Must contain at least one uppercase letter, one lowercase letter, and one digit.

Success response (201):

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

Requires Bearer token.

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

### `PATCH /auth/me`

Requires Bearer token. Request body:

```json
{
  "name": "string",
  "email": "string",
  "current_password": "string"
}
```

### `POST /auth/change-password`

Requires Bearer token. Request body:

```json
{
  "current_password": "string",
  "new_password": "string"
}
```

`new_password` follows the same complexity rules as `register`: 8-128 characters, must contain uppercase, lowercase, and digit. All existing tokens are invalidated after password change.

### `DELETE /auth/me`

Requires Bearer token. Request body:

```json
{
  "current_password": "string"
}
```

## Detection Contracts

### `POST /detect`

Requires Bearer token. Request body:

```json
{
  "image_url": "https://example.com/image.jpg"
}
```

Success response (201):

```json
{
  "id": 1,
  "label": "Tidak Layak Jual",
  "label_key": "tidak_layak_jual",
  "confidence_score": 91.2,
  "raw_score": 0.912,
  "threshold_used": 0.3,
  "model_version": "umkm_food_quality_v1",
  "explanation": "string",
  "image_url": "https://example.com/image.jpg",
  "created_at": "2026-05-11T12:00:00Z"
}
```

## History Contracts

### `GET /history`

Requires Bearer token. Supports pagination query params: `offset` (default 0), `limit` (default 20, max 100).

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
  ],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

### `GET /history/latest`

Requires Bearer token. Returns single `HistoryDetailResponse` or 404.

### `GET /history/{detection_id}`

Requires Bearer token. Returns single `HistoryDetailResponse` or 404.

### `DELETE /history/{detection_id}`

Requires Bearer token.

```json
{ "deleted_count": 1 }
```

### `DELETE /history` (bulk)

Requires Bearer token. Request body:

```json
{ "ids": [1, 2, 3] }
```

```json
{ "deleted_count": 2 }
```

## Admin Contracts

### `GET /admin/dashboard`

Requires admin role.

```json
{
  "total_detections": 100,
  "total_layak_jual": 45,
  "total_tidak_layak_jual": 55,
  "active_model_version": "umkm_food_quality_v1"
}
```

### `GET /admin/models`

Requires admin role.

```json
{
  "active_model_id": "umkm_food_quality_v1",
  "models": [
    {
      "experiment_id": "umkm_food_quality_v1",
      "model_family": "MobileNetV2",
      "threshold": 0.1,
      "status": "trained",
      "is_active": true,
      "model_file_available": true,
      "class_indices_file_available": true,
      "passed_quality_gate": true,
      "collapse_flags": [],
      "quality_sample_count": 72
    }
  ]
}
```

### `GET /admin/detections`

Requires admin role. Supports pagination query params: `offset` (default 0), `limit` (default 20, max 100).

```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "label": "Layak Jual",
      "label_key": "layak_jual",
      "confidence_score": 73.4,
      "model_version": "umkm_food_quality_v1",
      "created_at": "2026-05-11T12:00:00Z"
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

### `GET /admin/detections/{detection_id}`

Requires admin role.

```json
{
  "id": 1,
  "user_id": 1,
  "label": "Tidak Layak Jual",
  "label_key": "tidak_layak_jual",
  "confidence_score": 78.98,
  "raw_score": 0.634354,
  "threshold_used": 0.3,
  "model_version": "umkm_food_quality_v1",
  "explanation": "string",
  "image_url": "https://example.com/image.jpg",
  "created_at": "2026-05-11T12:00:00Z",
  "active_model_id": "umkm_food_quality_v1",
  "prediction_mode": "single_active_model",
  "class_indices": {
    "layak_jual": 0,
    "tidak_layak_jual": 1
  }
}
```

### `POST /admin/detect/compare`

Requires admin role. Gated by `ENABLE_MULTI_MODEL_COMPARISON=true`.

```json
{
  "active_model_id": "umkm_food_quality_v1",
  "image_url": "https://example.com/image.jpg",
  "predictions": [
    {
      "model_version": "umkm_food_quality_v1",
      "label": "Tidak Layak Jual",
      "label_key": "tidak_layak_jual",
      "confidence_score": 78.98,
      "raw_score": 0.634354,
      "threshold_used": 0.3,
      "explanation": "string",
      "is_active": true,
      "passed_quality_gate": true,
      "collapse_flags": []
    }
  ]
}
```

## Health Contract

### `GET /health`

```json
{
  "status": "ok",
  "database": "connected",
  "model_loaded": true,
  "model_version": "umkm_food_quality_v1"
}
```

## Rate Limits

| Endpoint | Limit |
|---|---|
| `POST /auth/register` | 5/min |
| `POST /auth/login` | 5/min |
| `PATCH /auth/me` | 5/min |
| `POST /auth/change-password` | 5/min |
| `DELETE /auth/me` | 5/min |
| `POST /detect` | 30/min |
| `GET /history` | 60/min |
| `GET /history/latest` | 60/min |
| `GET /history/{id}` | 60/min |
| `DELETE /history/{id}` | 30/min |
| `DELETE /history` (bulk) | 10/min |
| `GET /admin/dashboard` | 30/min |
| `GET /admin/detections` | 60/min |
| `GET /admin/models` | 30/min |
| `POST /admin/detect/compare` | 10/min |
| Default | 100/min |
