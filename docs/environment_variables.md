# Environment Variables

Reference for all backend and ML environment variables.

## Current Variables

| Variable | Required | Example | Purpose |
|---|---|---|---|
| `APP_ENV` | Yes | `development` | Runtime context: development, test, or production. |
| `DATABASE_URL` | Yes | `postgresql://postgres:change_me@localhost:5432/umkm_food_quality` | PostgreSQL connection string. |
| `SECRET_KEY` | Yes | `change-this-secret-key` | JWT signing key and security purposes. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | `60` | Access token TTL in minutes. |
| `MODEL_PATH` | Yes | `ml/model/umkm_food_quality_v1/model.keras` | Active model inference path. |
| `CLASS_INDICES_PATH` | Yes | `ml/model/umkm_food_quality_v1/class_indices.json` | Label index mapping for active model. |
| `MODEL_REGISTRY_PATH` | No | `ml/model` | Root directory for multi-model discovery. |
| `ACTIVE_MODEL_CONFIG_PATH` | No | `ml/model/active_model.json` | Active model selector config. |
| `MODEL_QUALITY_REPORT_PATH` | No | `ml/model/model_quality_report.json` | Quality gate report for model validation. |
| `MODEL_QUALITY_STRICT` | No | `false` | Fail startup if active model fails quality gate. |
| `ENABLE_MULTI_MODEL_COMPARISON` | No | `false` | Enable admin multi-model comparison endpoint. |
| `CORS_ORIGINS` | Yes | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed CORS origins. |
| `ALLOWED_IMAGE_DOMAINS` | No | `res.cloudinary.com` | Comma-separated allowed image hostnames for /detect. Leave empty to allow all public hosts. |
| `IMAGE_DOWNLOAD_MAX_BYTES` | No | `10485760` | Maximum image download size in bytes (10MB). |
| `IMAGE_DOWNLOAD_MAX_REDIRECTS` | No | `3` | Maximum HTTP redirect chain length. |
| `IMAGE_DOWNLOAD_TIMEOUT_SECONDS` | No | `20` | HTTP download timeout in seconds. |
| `WARMUP_PREDICTOR_ON_STARTUP` | No | `true` | Load TF model at startup. Set false for fast dev iteration. |
| `EMAIL_BACKEND` | No | `console` | Email delivery: `console` or `smtp`. |
| `SMTP_HOST` | No | | SMTP server hostname. |
| `SMTP_PORT` | No | `587` | SMTP server port. |
| `SMTP_USER` | No | | SMTP authentication username. |
| `SMTP_PASSWORD` | No | | SMTP authentication password. |
| `EMAIL_FROM` | No | `noreply@foodqcheck.local` | Sender email address. |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | No | `15` | Password reset token TTL. |
| `RESET_PASSWORD_FRONTEND_URL` | No | `foodqcheck://reset-password` | Frontend password reset page URL. Use `https://` for production with App Links. |
| `EMAIL_VERIFICATION_TOKEN_TTL_MINUTES` | No | `30` | Email verification token TTL. |
| `VERIFY_EMAIL_FRONTEND_URL` | No | `foodqcheck://verify-email` | Frontend email verification page URL. Use `https://` for production with App Links. |
| `REQUIRE_VERIFIED_EMAIL` | No | `true` | Enforce email verification before login. Recommended `true` for production. |

## Value Rules

### `APP_ENV`

Values: `development`, `test`, `production`.

### `DATABASE_URL`

- Must use full connection string.
- Never commit production credentials.
- For local development, use project-specific database user.

### `SECRET_KEY`

- Must be changed from placeholder before auth is active.
- Use a long, random string.
- Never print to logs or API responses.

### `REQUIRE_VERIFIED_EMAIL`

- Set to `true` for production to block unverified users from logging in.
- When `false`, users can log in without verifying their email but a verification banner is shown in the app.

### `MODEL_PATH`

- Must point to a valid model artifact.
- Current active model: `umkm_food_quality_v1`.

### `ALLOWED_IMAGE_DOMAINS`

- Comma-separated hostnames.
- Leave empty to allow any public host (private/loopback IPs always rejected).
- Set to `res.cloudinary.com` for production.

### `VERIFY_EMAIL_FRONTEND_URL` / `RESET_PASSWORD_FRONTEND_URL`

- Use `foodqcheck://` custom URL scheme for local development with Android emulator.
- Use `https://` scheme for production with Android App Links.
- Example production: `https://foodqcheck.drenzzz.dev/verify-email`

## Auth Validation Rules

### Password Policy

All auth endpoints that accept a password (`register`, `change-password`, `reset-password`) enforce:

- Minimum 8 characters, maximum 128 characters
- At least one uppercase letter (`A-Z`)
- At least one lowercase letter (`a-z`)
- At least one digit (`0-9`)

### Email Normalization

All auth endpoints that accept an email (`register`, `login`, `forgot-password`, `update-profile`) normalize the email to lowercase before storage and comparison. `Test@Example.com` and `test@example.com` are treated as the same address.

### Name Sanitization

The `name` field in `register` and `update-profile` strips HTML tags before storage. `<b>Bold</b> User` becomes `Bold User`.

## Secret Handling Policy

1. `.env` is for local runtime only and must never enter Git.
2. `.env.example` contains safe placeholders only.
3. Secrets like `SECRET_KEY` and database credentials must never be written in source code.
4. Application logs must never print secrets or full connection strings.
5. At deploy time, secrets must be injected via platform environment settings.

## Local Setup

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- `DATABASE_URL`
- `SECRET_KEY`
- `MODEL_PATH`
- `CLASS_INDICES_PATH`

Python 3.11 is the required runtime for both backend and ML environments.

## Change Policy

When adding a new env var:

1. Add to `.env.example` first
2. Document in this file
3. Then use in backend or ML code
