#!/usr/bin/env bash
# install.sh
# ------------------------
# Installs Python and Node dependencies for backend & frontend

set -euo pipefail

echo "==> 1. Create & activate Python virtualenv"
python3 -m venv venv
source venv/bin/activate

echo "==> 2. Upgrade pip and install backend requirements"
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> 3. Install Node.js dependencies and build frontend"
pushd frontend
npm install
npm run build
popd

echo "==> 4. Install 'serve' for static hosting"
npm install -g serve

echo "✅ Installation complete!"