#!/bin/bash
# Setup virtual environment for hardware monitoring

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up virtual environment for hardware monitoring..."
echo "Project directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To install optional dependencies:"
echo "  pip install -r requirements-gui.txt    # For GUI support"
echo "  pip install -r requirements-ml.txt     # For ML validation"

