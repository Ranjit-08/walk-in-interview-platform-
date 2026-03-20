#!/bin/bash
# setup.sh — One-time local development setup
# Run this after cloning the repo

set -e

echo "================================================"
echo " Walk-in Interview Platform — Local Setup"
echo "================================================"

# ── Check prerequisites ────────────────────────────────────────────
echo ""
echo "Checking prerequisites..."

command -v python3  >/dev/null || { echo "Python3 required"; exit 1; }
command -v pip3     >/dev/null || { echo "pip3 required";    exit 1; }
command -v terraform >/dev/null || { echo "Terraform required"; exit 1; }
command -v aws      >/dev/null || { echo "AWS CLI required"; exit 1; }
command -v git      >/dev/null || { echo "git required";     exit 1; }

echo "All prerequisites found."

# ── Backend setup ──────────────────────────────────────────────────
echo ""
echo "Setting up backend..."

cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env if not exists
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || cp ../.env.example .env
  echo ".env created from template. Fill in your values!"
fi

cd ..

# ── Terraform setup ────────────────────────────────────────────────
echo ""
echo "Setting up Terraform..."

cd terraform

# Copy tfvars if not exists
if [ ! -f terraform.tfvars ]; then
  cp terraform.tfvars.example terraform.tfvars
  echo "terraform.tfvars created. Fill in your values!"
fi

terraform init

cd ..

# ── Git hooks ──────────────────────────────────────────────────────
echo ""
echo "Installing git hooks..."

cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/bash
# Pre-commit: check for secrets accidentally staged
if git diff --cached --name-only | grep -E "\.(env|tfvars)$"; then
  echo "ERROR: Attempting to commit .env or .tfvars file!"
  echo "These files contain secrets and must not be committed."
  exit 1
fi
HOOK

chmod +x .git/hooks/pre-commit
echo "Pre-commit hook installed (blocks .env and .tfvars commits)."

echo ""
echo "================================================"
echo " Setup Complete!"
echo ""
echo " Next steps:"
echo " 1. Fill in backend/.env with your AWS values"
echo " 2. Fill in terraform/terraform.tfvars"
echo " 3. cd terraform && terraform apply"
echo " 4. Copy outputs into GitHub Secrets"
echo " 5. git push → auto deploys!"
echo "================================================"