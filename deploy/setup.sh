#!/usr/bin/env bash
set -euo pipefail

# This script is for baremetal deployment only.
# For Docker deployment, use deploy/docker-compose.yml instead.

SCRIPT_NAME="$(basename "$0")"
APP_USER="drenzzz"
APP_DIR="/home/drenzzz/foodqcheck"
APP_GROUP="drenzzz"
DB_NAME="umkm_food_quality"
DB_USER="foodqcheck"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

if [[ $EUID -ne 0 ]]; then
  fail "Must run as root. Use: sudo $0"
fi

log "=== 1/5 PostgreSQL setup"
apt-get update -y
apt-get install -y postgresql postgresql-contrib

systemctl enable postgresql
systemctl start postgresql

su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\"" | grep -q 1 \
  || su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD 'CHANGEME_DB_PASSWORD'\""

su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\"" | grep -q 1 \
  || su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}\""

su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER}\""
log "PostgreSQL user '${DB_USER}' and database '${DB_NAME}' ready."
log "IMPORTANT: change the database password with: sudo -u postgres psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '<new_password>';\""

log "=== 2/5 Firewall setup"
apt-get install -y ufw
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow "Nginx Full"
ufw --force enable
ufw status verbose

log "=== 3/5 fail2ban setup"
apt-get install -y fail2ban
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

log "=== 4/5 Logrotate for application logs"
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
}
EOF
mkdir -p /var/log/foodqcheck
chown -R "${APP_USER}:${APP_GROUP}" /var/log/foodqcheck 2>/dev/null || true

log "=== 5/5 Nginx setup"
apt-get install -y nginx
systemctl enable nginx

log "=== Done"
log "Next steps:"
log "  1. Set database password: sudo -u postgres psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '<password>';\""
log "  2. Clone the repo into ${APP_DIR} as the ${APP_USER} user"
log "  3. Copy deploy/env.docker.template to deploy/env.production and fill in secrets"
log "  4. Run: docker compose -f deploy/docker-compose.yml up -d --build"
