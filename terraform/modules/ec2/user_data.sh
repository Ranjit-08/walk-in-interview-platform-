#!/bin/bash
# user_data.sh — Bootstraps EC2 on first boot
# Installs Python, clones the app, creates .env, starts Gunicorn

set -e
exec > /var/log/user-data.log 2>&1

echo "=== Starting EC2 bootstrap ==="

# ── System updates ─────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y
apt-get install -y \
  python3.12 python3.12-venv python3-pip \
  git curl nginx \
  pkg-config default-libmysqlclient-dev gcc \
  supervisor

# ── Create app user ────────────────────────────────────────────────
useradd -m -s /bin/bash appuser || true

# ── Clone application ──────────────────────────────────────────────
mkdir -p /app
cd /app
git clone https://github.com/YOUR_ORG/walk-in-interview-platform.git . || true
chown -R appuser:appuser /app

# ── Python virtual environment ─────────────────────────────────────
sudo -u appuser python3.12 -m venv /app/venv
sudo -u appuser /app/venv/bin/pip install --upgrade pip
sudo -u appuser /app/venv/bin/pip install -r /app/backend/requirements.txt

# ── Write .env file ────────────────────────────────────────────────
cat > /app/backend/.env <<'ENVFILE'
FLASK_ENV=production
FLASK_SECRET_KEY=$(openssl rand -hex 32)
PORT=5000

DB_HOST=${db_host}
DB_PORT=3306
DB_NAME=${db_name}
DB_USER=${db_username}
DB_PASSWORD=${db_password}

COGNITO_USER_POOL_ID=${cognito_pool_id}
COGNITO_APP_CLIENT_ID=${cognito_client_id}
COGNITO_REGION=${aws_region}

SES_SENDER_EMAIL=${ses_sender_email}
SES_REGION=${aws_region}

BEDROCK_REGION=${aws_region}
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

FRONTEND_URL=${frontend_url}
AWS_REGION=${aws_region}
BOOKING_CODE_PREFIX=WI
ENVFILE

chown appuser:appuser /app/backend/.env
chmod 600 /app/backend/.env

# ── Supervisor config (keeps Gunicorn running) ─────────────────────
cat > /etc/supervisor/conf.d/walkin.conf <<'SUPERVISOR'
[program:walkin]
command=/app/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app
directory=/app/backend
user=appuser
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/walkin.err.log
stdout_logfile=/var/log/walkin.out.log
environment=HOME="/home/appuser",USER="appuser"
SUPERVISOR

# ── Nginx reverse proxy ────────────────────────────────────────────
cat > /etc/nginx/sites-available/walkin <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/walkin /etc/nginx/sites-enabled/walkin
rm -f /etc/nginx/sites-enabled/default

# ── Start services ─────────────────────────────────────────────────
systemctl enable nginx supervisor
systemctl restart nginx
supervisorctl reread
supervisorctl update
supervisorctl start walkin

echo "=== Bootstrap complete ==="