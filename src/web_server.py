"""Web server for remote hardware monitoring."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List

# Check if dependencies are installed
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    print("ERROR: Web server dependencies are not installed.")
    print("\nPlease run: pip install fastapi uvicorn websockets")
    sys.exit(1)

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import psutil
from src.utils.gpu_utils import get_gpu_info, get_gpu_metrics
from src.utils.logger import setup_logger
from src.utils.format_utils import (
    format_bytes,
    format_percentage,
    format_temperature,
    format_frequency,
)
from src.inventory import collect_inventory
from src.setup_checker import (
    check_nvidia_driver,
    check_cuda_toolkit,
    check_pytorch,
    check_yolov8,
    check_version_compatibility,
    CheckResult,
)

logger = setup_logger(__name__)

app = FastAPI(title="Hardware Monitor System", version="1.0.0")

# Store active WebSocket connections
active_connections: List[WebSocket] = []


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"Client connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"Client disconnected. Total connections: {len(self.active_connections)}"
        )

    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def get_cpu_data() -> Dict:
    """Get current CPU metrics."""
    try:
        per_cpu = psutil.cpu_percent(percpu=True, interval=0.1)
        overall = psutil.cpu_percent(interval=0.1)

        freq = None
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                freq = cpu_freq.current
        except:
            pass

        return {
            "per_core": per_cpu,
            "overall": overall,
            "frequency_mhz": freq,
            "cores": len(per_cpu),
        }
    except Exception as e:
        logger.error(f"Error getting CPU data: {e}")
        return {"per_core": [], "overall": 0, "frequency_mhz": None, "cores": 0}


def get_memory_data() -> Dict:
    """Get current memory metrics."""
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }
    except Exception as e:
        logger.error(f"Error getting memory data: {e}")
        return {
            "total": 0,
            "available": 0,
            "used": 0,
            "percent": 0,
            "swap_total": 0,
            "swap_used": 0,
            "swap_percent": 0,
        }


def get_disk_data() -> List[Dict]:
    """Get current disk metrics."""
    disks = []
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions[:10]:  # Limit to 10 partitions
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    }
                )
            except PermissionError:
                continue
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Error getting disk data: {e}")

    return disks


def get_network_data() -> List[Dict]:
    """Get current network metrics."""
    interfaces = []
    try:
        net_io = psutil.net_io_counters(pernic=True)
        net_if_stats = psutil.net_if_stats()

        for interface_name, stats in list(net_if_stats.items())[
            :10
        ]:  # Limit to 10 interfaces
            if interface_name == "lo":
                continue

            if_stats = net_io.get(interface_name)
            sent = if_stats.bytes_sent if if_stats else 0
            recv = if_stats.bytes_recv if if_stats else 0

            interfaces.append(
                {
                    "name": interface_name,
                    "is_up": stats.isup,
                    "speed_mbps": stats.speed if stats.speed > 0 else None,
                    "bytes_sent": sent,
                    "bytes_recv": recv,
                }
            )
    except Exception as e:
        logger.error(f"Error getting network data: {e}")

    return interfaces


def get_gpu_data() -> List[Dict]:
    """Get current GPU metrics."""
    gpus = []
    try:
        _, _, gpu_list = get_gpu_info()
        for gpu in gpu_list:
            metrics = get_gpu_metrics(gpu.index)
            if metrics:
                gpus.append(
                    {
                        "index": gpu.index,
                        "name": gpu.name,
                        "utilization": metrics.get("utilization", 0),
                        "temperature": metrics.get("temperature"),
                        "memory_used": metrics.get("memory_used", 0),
                        "memory_total": metrics.get("memory_total", 0),
                        "memory_percent": metrics.get("memory_percent", 0),
                        "power": metrics.get("power"),
                    }
                )
            else:
                gpus.append(
                    {
                        "index": gpu.index,
                        "name": gpu.name,
                        "utilization": None,
                        "temperature": None,
                        "memory_used": None,
                        "memory_total": gpu.total_memory,
                        "memory_percent": None,
                        "power": None,
                    }
                )
    except Exception as e:
        logger.error(f"Error getting GPU data: {e}")

    return gpus


def get_all_metrics() -> Dict:
    """Get all current metrics."""
    return {
        "cpu": get_cpu_data(),
        "memory": get_memory_data(),
        "disks": get_disk_data(),
        "network": get_network_data(),
        "gpu": get_gpu_data(),
    }


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the web dashboard."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hardware Monitor System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2em;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .tabs {
            background: white;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            gap: 0;
            overflow-x: auto;
        }
        
        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: transparent;
            font-size: 1em;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .tab:hover {
            background: #f5f5f5;
            color: #667eea;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
            font-weight: bold;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4caf50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-indicator.disconnected {
            background: #f44336;
            animation: none;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            color: #666;
        }
        
        .metric-value {
            font-weight: bold;
            color: #333;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            transition: width 0.3s ease;
        }
        
        .progress-fill.warning {
            background: linear-gradient(90deg, #ff9800, #ffc107);
        }
        
        .progress-fill.danger {
            background: linear-gradient(90deg, #f44336, #e91e63);
        }
        
        .gpu-card {
            grid-column: span 2;
        }
        
        .core-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        
        .core-item {
            text-align: center;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }
        
        .core-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .core-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #667eea;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .gpu-card {
                grid-column: span 1;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Hardware Monitor System</h1>
            <div class="status">
                <div class="status-indicator" id="statusIndicator"></div>
                <span id="statusText">Connecting...</span>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('monitoring', this)">📊 Real-time Monitoring</button>
            <button class="tab" onclick="switchTab('inventory', this)">💾 Hardware Inventory</button>
            <button class="tab" onclick="switchTab('setup', this)">✅ Environment Checker</button>
        </div>
        
        <div id="monitoring" class="tab-content active">
            <div class="grid" id="metricsGrid">
                <!-- Metrics will be populated by JavaScript -->
            </div>
        </div>
        
        <div id="inventory" class="tab-content">
            <div class="card">
                <h2>Hardware Inventory</h2>
                <div id="inventoryContent" style="padding: 20px;">
                    <p>Loading inventory...</p>
                </div>
            </div>
        </div>
        
        <div id="setup" class="tab-content">
            <div class="card">
                <h2>Environment Setup Checker</h2>
                <button onclick="runSetupCheck()" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 20px 0;">Run Check</button>
                <div id="setupContent" style="padding: 20px;">
                    <p>Click "Run Check" to validate your environment setup.</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let reconnectInterval = null;
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('Connected to server');
                updateStatus(true);
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateMetrics(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateStatus(false);
            };
            
            ws.onclose = () => {
                console.log('Disconnected from server');
                updateStatus(false);
                // Reconnect after 3 seconds
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(connect, 3000);
                }
            };
        }
        
        function updateStatus(connected) {
            const indicator = document.getElementById('statusIndicator');
            const text = document.getElementById('statusText');
            
            if (connected) {
                indicator.classList.remove('disconnected');
                text.textContent = 'Connected';
            } else {
                indicator.classList.add('disconnected');
                text.textContent = 'Disconnected';
            }
        }
        
        function updateMetrics(data) {
            const grid = document.getElementById('metricsGrid');
            grid.innerHTML = '';
            
            // CPU Card
            if (data.cpu) {
                const cpuCard = createCPUCard(data.cpu);
                grid.appendChild(cpuCard);
            }
            
            // Memory Card
            if (data.memory) {
                const memoryCard = createMemoryCard(data.memory);
                grid.appendChild(memoryCard);
            }
            
            // GPU Card
            if (data.gpu && data.gpu.length > 0) {
                const gpuCard = createGPUCard(data.gpu);
                grid.appendChild(gpuCard);
            }
            
            // Disk Card
            if (data.disks && data.disks.length > 0) {
                const diskCard = createDiskCard(data.disks);
                grid.appendChild(diskCard);
            }
            
            // Network Card
            if (data.network && data.network.length > 0) {
                const networkCard = createNetworkCard(data.network);
                grid.appendChild(networkCard);
            }
        }
        
        function createCPUCard(cpu) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h2>CPU</h2>
                <div class="metric">
                    <span class="metric-label">Overall Usage</span>
                    <span class="metric-value">${cpu.overall.toFixed(1)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${getProgressClass(cpu.overall)}" style="width: ${cpu.overall}%"></div>
                </div>
                <div class="core-list">
                    ${cpu.per_core.map((usage, i) => `
                        <div class="core-item">
                            <div class="core-label">Core ${i}</div>
                            <div class="core-value">${usage.toFixed(0)}%</div>
                        </div>
                    `).join('')}
                </div>
                ${cpu.frequency_mhz ? `
                    <div class="metric">
                        <span class="metric-label">Frequency</span>
                        <span class="metric-value">${(cpu.frequency_mhz / 1000).toFixed(2)} GHz</span>
                    </div>
                ` : ''}
            `;
            return card;
        }
        
        function createMemoryCard(memory) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h2>Memory</h2>
                <div class="metric">
                    <span class="metric-label">Used</span>
                    <span class="metric-value">${formatBytes(memory.used)} / ${formatBytes(memory.total)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Usage</span>
                    <span class="metric-value">${memory.percent.toFixed(1)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${getProgressClass(memory.percent)}" style="width: ${memory.percent}%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Available</span>
                    <span class="metric-value">${formatBytes(memory.available)}</span>
                </div>
                ${memory.swap_total > 0 ? `
                    <div class="metric">
                        <span class="metric-label">Swap</span>
                        <span class="metric-value">${formatBytes(memory.swap_used)} / ${formatBytes(memory.swap_total)} (${memory.swap_percent.toFixed(1)}%)</span>
                    </div>
                ` : ''}
            `;
            return card;
        }
        
        function createGPUCard(gpus) {
            const card = document.createElement('div');
            card.className = 'card gpu-card';
            card.innerHTML = `
                <h2>GPU</h2>
                ${gpus.map(gpu => `
                    <div style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee;">
                        <div class="metric">
                            <span class="metric-label">GPU ${gpu.index}: ${gpu.name}</span>
                        </div>
                        ${gpu.utilization !== null ? `
                            <div class="metric">
                                <span class="metric-label">Utilization</span>
                                <span class="metric-value">${gpu.utilization.toFixed(1)}%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill ${getProgressClass(gpu.utilization)}" style="width: ${gpu.utilization}%"></div>
                            </div>
                        ` : ''}
                        ${gpu.temperature !== null ? `
                            <div class="metric">
                                <span class="metric-label">Temperature</span>
                                <span class="metric-value">${gpu.temperature}°C</span>
                            </div>
                        ` : ''}
                        ${gpu.memory_used !== null ? `
                            <div class="metric">
                                <span class="metric-label">VRAM</span>
                                <span class="metric-value">${formatBytes(gpu.memory_used)} / ${formatBytes(gpu.memory_total)}</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill ${getProgressClass(gpu.memory_percent)}" style="width: ${gpu.memory_percent}%"></div>
                            </div>
                        ` : ''}
                        ${gpu.power !== null ? `
                            <div class="metric">
                                <span class="metric-label">Power</span>
                                <span class="metric-value">${gpu.power.toFixed(1)} W</span>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            `;
            return card;
        }
        
        function createDiskCard(disks) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h2>Disks</h2>
                ${disks.map(disk => `
                    <div style="margin-bottom: 15px;">
                        <div class="metric">
                            <span class="metric-label">${disk.device} (${disk.mountpoint})</span>
                            <span class="metric-value">${disk.percent.toFixed(1)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getProgressClass(disk.percent)}" style="width: ${disk.percent}%"></div>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Used / Total</span>
                            <span class="metric-value">${formatBytes(disk.used)} / ${formatBytes(disk.total)}</span>
                        </div>
                    </div>
                `).join('')}
            `;
            return card;
        }
        
        function createNetworkCard(networks) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h2>Network</h2>
                ${networks.map(net => `
                    <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
                        <div class="metric">
                            <span class="metric-label">${net.name}</span>
                            <span class="metric-value" style="color: ${net.is_up ? '#4caf50' : '#f44336'}">${net.is_up ? 'UP' : 'DOWN'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Sent</span>
                            <span class="metric-value">${formatBytes(net.bytes_sent)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Received</span>
                            <span class="metric-value">${formatBytes(net.bytes_recv)}</span>
                        </div>
                        ${net.speed_mbps ? `
                            <div class="metric">
                                <span class="metric-label">Speed</span>
                                <span class="metric-value">${net.speed_mbps} Mbps</span>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            `;
            return card;
        }
        
        function getProgressClass(value) {
            if (value >= 90) return 'danger';
            if (value >= 70) return 'warning';
            return '';
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function switchTab(tabName, element) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            if (element) {
                element.classList.add('active');
            }
            
            // Load data for inventory and setup tabs
            if (tabName === 'inventory') {
                loadInventory();
            }
        }
        
        async function loadInventory() {
            try {
                const response = await fetch('/api/inventory');
                const data = await response.json();
                displayInventory(data);
            } catch (error) {
                document.getElementById('inventoryContent').innerHTML = '<p style="color: red;">Error loading inventory: ' + error + '</p>';
            }
        }
        
        function displayInventory(inventory) {
            const content = document.getElementById('inventoryContent');
            let html = '<div style="display: grid; gap: 20px;">';
            
            // System Info
            if (inventory.system) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">System</h3>';
                html += `<p><strong>Hostname:</strong> ${inventory.system.hostname}</p>`;
                html += `<p><strong>OS:</strong> ${inventory.system.os} ${inventory.system.os_release}</p>`;
                html += '</div>';
            }
            
            // CPU
            if (inventory.cpu) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">CPU</h3>';
                html += `<p><strong>Model:</strong> ${inventory.cpu.model}</p>`;
                html += `<p><strong>Physical Cores:</strong> ${inventory.cpu.physical_cores}</p>`;
                html += `<p><strong>Logical Threads:</strong> ${inventory.cpu.logical_threads}</p>`;
                html += '</div>';
            }
            
            // Memory
            if (inventory.memory) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">Memory</h3>';
                html += `<p><strong>Total:</strong> ${formatBytes(inventory.memory.total_bytes)}</p>`;
                html += `<p><strong>Available:</strong> ${formatBytes(inventory.memory.available_bytes)}</p>`;
                html += `<p><strong>Used:</strong> ${formatBytes(inventory.memory.used_bytes)} (${inventory.memory.usage_percent.toFixed(1)}%)</p>`;
                html += '</div>';
            }
            
            // GPU
            if (inventory.gpu && inventory.gpu.gpus) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">GPU</h3>';
                html += `<p><strong>Driver Version:</strong> ${inventory.gpu.driver_version || 'N/A'}</p>`;
                html += `<p><strong>CUDA Version:</strong> ${inventory.gpu.cuda_version || 'N/A'}</p>`;
                html += `<p><strong>GPU Count:</strong> ${inventory.gpu.gpu_count}</p>`;
                inventory.gpu.gpus.forEach(gpu => {
                    html += `<p><strong>GPU ${gpu.index}:</strong> ${gpu.name} (${formatBytes(gpu.total_memory_bytes)})</p>`;
                });
                html += '</div>';
            }
            
            // Disks
            if (inventory.disks && inventory.disks.length > 0) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">Disks</h3>';
                inventory.disks.forEach(disk => {
                    html += `<p><strong>${disk.device}</strong> (${disk.mountpoint}): ${formatBytes(disk.used_bytes)} / ${formatBytes(disk.total_bytes)} (${disk.usage_percent.toFixed(1)}%)</p>`;
                });
                html += '</div>';
            }
            
            // Network
            if (inventory.network && inventory.network.length > 0) {
                html += '<div><h3 style="color: #667eea; margin-bottom: 10px;">Network Interfaces</h3>';
                inventory.network.forEach(iface => {
                    html += `<p><strong>${iface.name}:</strong> ${iface.is_up ? 'UP' : 'DOWN'}</p>`;
                });
                html += '</div>';
            }
            
            html += '</div>';
            content.innerHTML = html;
        }
        
        async function runSetupCheck() {
            const content = document.getElementById('setupContent');
            content.innerHTML = '<p>Running checks...</p>';
            
            try {
                const response = await fetch('/api/setup-check');
                const data = await response.json();
                displaySetupCheck(data.results);
            } catch (error) {
                content.innerHTML = '<p style="color: red;">Error running setup check: ' + error + '</p>';
            }
        }
        
        function displaySetupCheck(results) {
            const content = document.getElementById('setupContent');
            let html = '<div style="display: grid; gap: 15px;">';
            
            results.forEach(result => {
                const statusColor = result.status === 'pass' ? '#4caf50' : result.status === 'warning' ? '#ff9800' : '#f44336';
                const statusIcon = result.status === 'pass' ? '✓' : result.status === 'warning' ? '⚠' : '✗';
                
                html += `<div style="padding: 15px; background: #f5f5f5; border-radius: 5px; border-left: 4px solid ${statusColor};">`;
                html += `<h3 style="margin: 0 0 10px 0; color: ${statusColor};">${statusIcon} ${result.name}</h3>`;
                html += `<p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: ${statusColor};">${result.status.toUpperCase()}</span></p>`;
                html += `<p style="margin: 5px 0;"><strong>Message:</strong> ${result.message}</p>`;
                if (result.recommendation) {
                    html += `<p style="margin: 5px 0;"><strong>Recommendation:</strong> <span style="color: #666;">${result.recommendation}</span></p>`;
                }
                html += '</div>';
            });
            
            html += '</div>';
            content.innerHTML = html;
        }
        
        // Connect on page load
        connect();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/inventory")
async def get_inventory():
    """Get hardware inventory."""
    try:
        inventory = collect_inventory()
        return JSONResponse(content=inventory)
    except Exception as e:
        logger.error(f"Error getting inventory: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/setup-check")
async def get_setup_check():
    """Get environment setup check results."""
    try:
        results = []

        # Check NVIDIA driver
        results.append(check_nvidia_driver())

        # Check CUDA toolkit
        results.append(check_cuda_toolkit())

        # Check PyTorch
        pytorch_check, pytorch_cuda_check = check_pytorch()
        results.append(pytorch_check)
        if pytorch_cuda_check:
            results.append(pytorch_cuda_check)

        # Check YOLOv8
        results.append(check_yolov8())

        # Check version compatibility
        compatibility_results = check_version_compatibility()
        results.extend(compatibility_results)

        # Convert to dict for JSON
        results_dict = [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "recommendation": r.recommendation or "",
            }
            for r in results
        ]

        return JSONResponse(content={"results": results_dict})
    except Exception as e:
        logger.error(f"Error getting setup check: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics."""
    try:
        metrics = get_all_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics."""
    await manager.connect(websocket)
    try:
        while True:
            # Send metrics every 1 second
            metrics = get_all_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Run the web server.

    Args:
        host: Host to bind to (default: 0.0.0.0 for all interfaces)
        port: Port to bind to (default: 8000)
    """
    import socket

    # Get local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"

    logger.info("=" * 60)
    logger.info("Hardware Monitor Web Server")
    logger.info("=" * 60)
    logger.info(f"Server starting on http://{host}:{port}")
    logger.info(f"Local access: http://localhost:{port}")
    logger.info(f"Network access: http://{local_ip}:{port}")
    logger.info("=" * 60)
    logger.info("Press CTRL+C to stop the server")
    logger.info("=" * 60)

    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Main entry point for web server."""
    import argparse

    parser = argparse.ArgumentParser(description="Hardware Monitor Web Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )

    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
