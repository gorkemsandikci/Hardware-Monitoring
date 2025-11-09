# Hardware Monitor System

A comprehensive hardware monitoring and environment validation tool for Ubuntu systems with NVIDIA GPU support. This application provides real-time monitoring, hardware inventory, and validates your AI/ML development environment (NVIDIA drivers, CUDA, PyTorch, YOLOv8).

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Ubuntu-orange)](https://ubuntu.com/)

## Features

- **Hardware Inventory**: Complete system component detection (CPU, Memory, Disk, GPU, Network)
- **Real-time Monitoring**: Terminal-based dashboard with live updating metrics
- **Web Server**: Remote monitoring via web browser - accessible from any device on your network
- **Environment Validation**: Checks NVIDIA drivers, CUDA toolkit, PyTorch, and YOLOv8 setup
- **GPU Support**: Full NVIDIA GPU detection and monitoring with VRAM, temperature, and power usage
- **Rich Terminal UI**: Beautiful, color-coded terminal interface using the `rich` library
- **WebSocket Support**: Real-time data streaming to web clients

## Quick Start

### Prerequisites

- Ubuntu 20.04, 22.04, or 24.04
- Python 3.10 or higher
- NVIDIA GPU (optional, for GPU monitoring features)

### Installation

```bash
# Clone repository
git clone <repo-url> && cd hardware-monitoring

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

**Easiest way - Just run the launcher:**

```bash
cd /home/gorkem/dev/personal/hardware-monitoring
./run.sh
```

**Or manually:**

```bash
# Navigate to project root (if not already there)
cd /home/gorkem/dev/personal/hardware-monitoring

# Activate virtual environment
source .venv/bin/activate

# Start web server (starts automatically)
python3 src/main.py
```

The web server will start and display:
- **Local access**: `http://localhost:8000`
- **Network access**: `http://YOUR_IP:8000` (shown when server starts)

**Web Interface Features:**
- **📊 Real-time Monitoring**: Live hardware metrics with WebSocket updates
- **💾 Hardware Inventory**: Complete system component information
- **✅ Environment Checker**: Validate NVIDIA/CUDA/PyTorch setup

Access from any device on your network - just open a web browser!

**Or run individual scripts directly (optional):**

```bash
# Collect hardware inventory
python3 src/inventory.py

# Start real-time monitoring dashboard
python3 src/monitor.py

# Check environment setup
python3 src/setup_checker.py
```

Or use the setup script:

```bash
# Setup virtual environment and install dependencies
./scripts/setup-venv.sh

# Activate and run (from project root)
source .venv/bin/activate
python3 src/main.py
```

**Note**: If you see "ModuleNotFoundError", make sure:
1. You're in the project root directory (not in `src/`)
2. The virtual environment is activated (you should see `(.venv)` in your prompt)
3. Dependencies are installed (`pip install -r requirements.txt`)

## Project Structure

```
hardware-monitoring/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── requirements-gui.txt           # Optional GUI dependencies
├── requirements-ml.txt            # Optional ML validation dependencies
├── setup.py                       # Package installation script
├── src/
│   ├── inventory.py              # Hardware inventory module
│   ├── monitor.py                # Real-time terminal dashboard
│   ├── setup_checker.py          # Environment validation
│   ├── utils/
│   │   ├── gpu_utils.py          # GPU-specific utilities
│   │   ├── format_utils.py       # Formatting helpers
│   │   └── logger.py             # Logging configuration
├── scripts/                       # Installation and setup scripts
└── docs/                          # Detailed documentation
```

## Modules

### Hardware Inventory (`inventory.py`)

Collects and catalogs all system hardware components:

- CPU: Model, cores, threads, frequency
- Memory: Total, available, usage, swap
- Disk: All partitions with capacity and usage
- GPU: NVIDIA GPU detection with driver and CUDA version
- Network: All network interfaces with addresses

**Example:**
```bash
python src/inventory.py -o my_inventory.json
```

### Real-time Monitoring (`monitor.py`)

Terminal-based dashboard with live updating metrics:

- CPU usage per core
- Memory and swap usage
- Disk I/O and usage per partition
- Network interface statistics
- GPU utilization, temperature, VRAM, and power

**Features:**
- Color-coded status indicators (green/yellow/red)
- Update interval: 1-2 seconds (configurable)
- Keyboard controls: 'q' to quit, 'r' to reset stats

**Example:**
```bash
python src/monitor.py --interval 1.5
```

### Environment Setup Checker (`setup_checker.py`)

Validates your AI/ML development environment:

- **NVIDIA Driver**: Checks driver version and CUDA support
- **CUDA Toolkit**: Verifies installed CUDA compiler version
- **PyTorch**: Validates PyTorch installation and CUDA availability
- **YOLOv8**: Checks Ultralytics YOLOv8 installation

**Example:**
```bash
python src/setup_checker.py
```

### Web Server (`web_server.py`)

Remote monitoring via web browser - accessible from any device on your network:

- **Real-time Updates**: WebSocket-based live data streaming (1 second intervals)
- **Web Dashboard**: Beautiful, responsive web interface
- **Network Access**: Accessible from any device on your local network
- **No Client Installation**: Just open a web browser
- **API Endpoints**: RESTful API for programmatic access

**Example:**
```bash
# Start web server
python src/web_server.py

# Custom host/port
python src/web_server.py --host 0.0.0.0 --port 8000
```

**Access:**
- Local: `http://localhost:8000`
- Network: `http://YOUR_IP:8000` (shown when server starts)
- API: `http://YOUR_IP:8000/api/metrics` (JSON endpoint)
- WebSocket: `ws://YOUR_IP:8000/ws` (real-time stream)

## System Dependencies

### NVIDIA Driver

The recommended method for installing NVIDIA drivers on Ubuntu:

```bash
# Check available drivers
ubuntu-drivers devices

# Auto-install recommended driver
sudo ubuntu-drivers autoinstall

# Reboot after installation
sudo reboot
```

### CUDA Toolkit (Optional)

For ML/AI development, install CUDA toolkit:

```bash
# Check driver-supported CUDA version
nvidia-smi

# Install CUDA toolkit (example for CUDA 12.0)
# Follow official NVIDIA CUDA installation guide
```

### Verification

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA toolkit
nvcc --version

# Check PyTorch CUDA support
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
```

## Installation Options

### Basic Installation (Monitoring Only)

```bash
pip install -r requirements.txt
```

### With GUI Support

```bash
pip install -r requirements.txt
pip install -r requirements-gui.txt
```

### With ML Validation

```bash
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

### Full Installation

```bash
pip install -r requirements.txt
pip install -r requirements-gui.txt
pip install -r requirements-ml.txt
```

## Usage Examples

### Collect Hardware Inventory

```bash
# Save to default file (inventory_YYYYMMDD_HHMMSS.json)
python src/inventory.py

# Save to custom file
python src/inventory.py -o my_system.json

# Save without printing summary
python src/inventory.py --no-print -o inventory.json
```

### Monitor System Resources

```bash
# Default 1 second interval
python src/monitor.py

# Custom update interval
python src/monitor.py -i 2.0

# Press 'q' to quit, 'r' to reset statistics
```

### Validate Environment

```bash
# Run full environment check
python src/setup_checker.py

# Output includes:
# - NVIDIA driver status
# - CUDA toolkit version
# - PyTorch CUDA availability
# - YOLOv8 installation status
# - Recommendations for missing components
```

## Troubleshooting

### GPU Not Detected

1. Verify NVIDIA driver is installed:
   ```bash
   nvidia-smi
   ```

2. Check if GPU is recognized:
   ```bash
   lspci | grep -i nvidia
   ```

3. Install/reinstall drivers:
   ```bash
   sudo ubuntu-drivers autoinstall
   ```

### Permission Errors

- The application runs with user privileges (no root required)
- Some disk partitions may require elevated permissions
- GPU monitoring requires NVIDIA driver to be properly installed

### Import Errors

- Ensure virtual environment is activated
- Install all required dependencies: `pip install -r requirements.txt`
- For GPU features, ensure `pynvml` is installed

### CUDA/PyTorch Issues

- Verify CUDA toolkit version matches driver-supported version
- Install PyTorch with CUDA support:
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```
- Check PyTorch CUDA availability:
  ```python
  import torch
  print(torch.cuda.is_available())
  ```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/test_inventory.py
```

### Code Style

The project follows PEP 8 style guidelines:

```bash
# Format code
black src/

# Lint code
pylint src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Documentation

Detailed documentation is available in the `docs/` directory:

- `installation.md`: Detailed installation guide
- `nvidia-setup.md`: NVIDIA driver and CUDA setup guide
- `troubleshooting.md`: Common issues and solutions
- `api-reference.md`: Code documentation

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [psutil](https://github.com/giampaolo/psutil) for system information
- Uses [rich](https://github.com/Textualize/rich) for beautiful terminal output
- GPU monitoring powered by [pynvml](https://github.com/gpuopenanalytics/pynvml)

## Support

For issues, questions, or contributions, please open an issue on the project repository.

## Star History

If you find this project useful, please consider giving it a star ⭐!

---

**Note**: This tool is designed for Ubuntu systems. While it may work on other Linux distributions, it has been tested primarily on Ubuntu 20.04, 22.04, and 24.04.

