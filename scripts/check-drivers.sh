#!/bin/bash
# Quick NVIDIA driver check script

echo "=== NVIDIA Driver Check ==="
echo ""

# Check if nvidia-smi is available
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi is installed"
    echo ""
    echo "Driver Information:"
    nvidia-smi --query-gpu=driver_version,cuda_version --format=csv,noheader
    echo ""
    echo "GPU Details:"
    nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
else
    echo "✗ nvidia-smi is not available"
    echo ""
    echo "To install NVIDIA drivers:"
    echo "  sudo ubuntu-drivers autoinstall"
    echo "  sudo reboot"
fi

echo ""
echo "=== CUDA Toolkit Check ==="
echo ""

# Check if nvcc is available
if command -v nvcc &> /dev/null; then
    echo "✓ CUDA compiler (nvcc) is installed"
    echo ""
    nvcc --version
else
    echo "✗ CUDA compiler (nvcc) is not available"
    echo ""
    echo "CUDA toolkit is optional. Install if needed for ML/AI development."
    echo "See docs/nvidia-setup.md for installation instructions."
fi

