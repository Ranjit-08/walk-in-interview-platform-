#!/bin/bash
# deploy.sh — Manual deployment script (run from your local machine)
# Usage: ./scripts/deploy.sh [backend|frontend|all]

set -e

DEPLOY_TARGET=${1:-all}
EC2_IP=${EC2_PUBLIC_IP:-"YOUR_EC2_IP"}
S3_BUCKET=${S3_BUCKET_NAME:-"walkin-platform-frontend-prod"}
API_URL=${API_GATEWAY_URL:-"https://your-api-gateway-url/prod"}

echo "================================================"
echo " Walk-in Interview Platform — Manual Deploy"
echo " Target: $DEPLOY_TARGET"
echo "================================================"

deploy_backend() {
  echo ""
  echo "--- Deploying Backend to EC2 ---"

  ssh -i ~/.ssh/your-keypair.pem ubuntu@$EC2_IP << 'ENDSSH'
    set -e
    echo "Pulling latest code..."
    cd /app
    git fetch origin main
    git reset --hard origin/main

    echo "Installing dependencies..."
    /app/venv/bin/pip install -r /app/backend/requirements.txt --quiet

    echo "Restarting application..."
    sudo supervisorctl restart walkin
    sleep 5

    echo "Health check..."
    curl -sf http://localhost:5000/health && echo " Backend OK!" || echo " Backend FAILED!"
ENDSSH

  echo "Backend deployment complete."
}

deploy_frontend() {
  echo ""
  echo "--- Deploying Frontend to S3 ---"

  # Inject API URL
  sed -i.bak \
    "s|https://your-api-gateway-url.execute-api.ap-south-1.amazonaws.com/prod|$API_URL|g" \
    frontend/js/api.js

  # Sync to S3
  aws s3 sync frontend/ s3://$S3_BUCKET/ \
    --delete \
    --exclude "*.DS_Store" \
    --cache-control "no-cache, no-store, must-revalidate"

  # Restore original api.js
  mv frontend/js/api.js.bak frontend/js/api.js

  echo "Frontend deployed to: http://$S3_BUCKET.s3-website.ap-south-1.amazonaws.com"
}

# Run based on argument
case $DEPLOY_TARGET in
  backend)  deploy_backend ;;
  frontend) deploy_frontend ;;
  all)
    deploy_backend
    deploy_frontend
    ;;
  *)
    echo "Usage: ./scripts/deploy.sh [backend|frontend|all]"
    exit 1
    ;;
esac

echo ""
echo "================================================"
echo " Deployment Complete!"
echo " Frontend : http://$S3_BUCKET.s3-website.ap-south-1.amazonaws.com"
echo " API      : $API_URL"
echo "================================================"