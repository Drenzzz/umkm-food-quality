#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
APP_USER="foodqcheck"
APP_DIR="/opt/foodqcheck"
APP_GROUP="foodqcheck"
PYTHON_VERSION="3.11"
DB_NAME="umkm_food_quality"
DB_USER="foodqcheck"
SSH_DIR="/home/${APP_USER}/.ssh"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

if [[ $EUID -ne 0 ]]; then
  fail "Must run as root. Use: sudo $0"
fi

log "=== 1/8 System update"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

log "=== 2/8 Install OS packages"
apt-get install -y \
  software-properties-common \
  ca-certificates \
  curl \
  git \
  nginx \
  postgresql \
  postgresql-contrib \
  ufw \
  fail2ban \
  logrotate \
  rsync \
  unzip

log "=== 3/8 Install Python ${PYTHON_VERSION}"
if ! command -v python${PYTHON_VERSION} >/dev/null 2>&1; then
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update -y
  apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev
fi
python${PYTHON_VERSION} --version

log "=== 4/8 Create application user"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  adduser --system --group --home "/home/${APP_USER}" --shell /bin/bash "$APP_USER"
fi
mkdir -p "$APP_DIR"
chown -R "${APP_USER}:${APP_GROUP}" "$APP_DIR"
chown -R "${APP_USER}:${APP_GROUP}" "/home/${APP_USER}"

log "=== 5/8 PostgreSQL setup"
systemctl enable postgresql
systemctl start postgresql

su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\"" | grep -q 1 \
  || su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD 'CHANGEME_DB_PASSWORD'\""

su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\"" | grep -q 1 \
  || su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}\""

su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER}\""
log "PostgreSQL user '${DB_USER}' and database '${DB_NAME}' ready."
log "IMPORTANT: change the database password with: sudo -u postgres psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '<new_password>';\""

log "=== 6/8 Firewall setup"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow "Nginx Full"
ufw --force enable
ufw status verbose

log "=== 7/8 fail2ban setup"
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
EOF
systemctl enable fail2ban
systemctl restart fail2ban

log "=== 8/8 Logrotate for application logs"
cat > /etc/logrotate.d/foodqcheck <<EOF
/var/log/foodqcheck/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ${APP_USER} ${APP_GROUP}
    sharedscripts
    postrotate
        systemctl reload foodqcheck.service > /dev/null 2>&1 || true
    endscript
}
EOF
mkdir -p /var/log/foodqcheck
chown -R "${APP_USER}:${APP_GROUP}" /var/log/foodqcheck

log "=== Done"
log "Next steps:"
log "  1. Set database password: sudo -u postgres psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '<password>';\""
log "  2. Clone the repo into ${APP_DIR} as the ${APP_USER} user"
log "  3. Copy deploy/.env.production to ${APP_DIR}/.env and fill in secrets"
log "  4. Run deploy/deploy.sh to install deps, migrate, and start the service"
log "  5. Run deploy/copy-model.sh to upload the trained model"
log "  6. Configure Nginx site: sudo cp ${APP_DIR}/deploy/nginx.conf /etc/nginx/sites-available/foodqcheck && sudo ln -s /etc/nginx/sites-available/foodqcheck /etc/nginx/sites-enabled/foodqcheck && sudo nginx -t && sudo systemctl reload nginx"
