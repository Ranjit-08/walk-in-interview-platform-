#!/bin/bash
set -e

echo "--- Step 1: Install packages ---"
sudo apt-get update -y
sudo apt-get install -y \
  python3 python3-pip python3-venv \
  git curl nginx \
  pkg-config default-libmysqlclient-dev \
  gcc supervisor mysql-client openssl

echo "--- Step 2: Create dirs ---"
sudo mkdir -p /app /etc/walkin
sudo chown -R ubuntu:ubuntu /app

echo "--- Step 3: Clone or update repo ---"
cd /app
if [ -d ".git" ]; then
  git fetch origin main
  git reset --hard origin/main
else
  git clone https://github.com/Ranjit-08/walk-in-interview-platform-.git .
fi

echo "--- Step 4: Setup env ---"
sudo mv /tmp/walkin.env /etc/walkin/.env
sudo chmod 600 /etc/walkin/.env
rm -f /app/backend/.env
ln -sf /etc/walkin/.env /app/backend/.env
ls -la /app/backend/.env

echo "--- Step 5: Python venv ---"
cd /app/backend
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo "--- Step 6: Nginx ---"
sudo bash -c 'cat > /etc/nginx/sites-available/walkin' << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 10M;
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
NGINXEOF
sudo ln -sf /etc/nginx/sites-available/walkin /etc/nginx/sites-enabled/walkin
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "--- Step 7: Supervisor ---"
sudo bash -c 'cat > /etc/supervisor/conf.d/walkin.conf' << 'SUPEOF'
[program:walkin]
command=/app/backend/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app
directory=/app/backend
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/walkin.err.log
stdout_logfile=/var/log/walkin.out.log
environment=HOME="/home/ubuntu",USER="ubuntu"
SUPEOF
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart walkin || sudo supervisorctl start walkin
sleep 5
sudo supervisorctl status walkin

echo "--- Step 8: Apply DB schema ---"
DB_HOST=$(grep ^DB_HOST /etc/walkin/.env | cut -d= -f2)
DB_USER=$(grep ^DB_USER /etc/walkin/.env | cut -d= -f2)
DB_PASS=$(grep ^DB_PASSWORD /etc/walkin/.env | cut -d= -f2)
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" interview_platform < /app/backend/migrations/schema.sql || echo "Schema already applied"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" interview_platform -e "SHOW TABLES;"

echo "--- Step 9: Health check ---"
for i in 1 2 3 4 5 6 7 8 9 10; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
  if [ "$STATUS" = "200" ]; then
    echo "Backend is live!"
    exit 0
  fi
  echo "Attempt $i: $STATUS - waiting..."
  sleep 5
done
echo "Health check failed"
tail -30 /var/log/walkin.err.log
exit 1