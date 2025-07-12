# WireGuard Web Manager

A simple, lightweight web interface for managing WireGuard VPN configurations. Built with minimal dependencies to work across a wide range of Linux distributions.

# Showcase
<img src=https://raw.githubusercontent.com/RetributionByRevenue/WireGuard-Web-Manager/refs/heads/main/web1.png>
<img src=https://raw.githubusercontent.com/RetributionByRevenue/WireGuard-Web-Manager/refs/heads/main/web2.png>
<img src=https://raw.githubusercontent.com/RetributionByRevenue/WireGuard-Web-Manager/refs/heads/main/web3.png>

## Features

- **Server Configuration Management**: Generate and manage WireGuard server configurations
- **Peer Management**: Add, delete, and export peer configurations
- **QR Code Generation**: Instantly generate QR codes for easy mobile device setup
- **Web Interface**: Clean, intuitive web UI for all management tasks
- **Cross-Platform**: Works on Alpine, Debian, Arch, Ubuntu, and other Linux distributions

## Prerequisites

- **WireGuard**: Must be installed on your system
- **Python 3**: Required to run the Flask application
- **Root Access**: Application must run as root to manage system configurations

## Installation

### 1. Install WireGuard

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install wireguard
```

**Alpine:**
```bash
sudo apk add wireguard-tools
```

**Arch:**
```bash
sudo pacman -S wireguard-tools
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install wireguard-tools
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd wireguard-web-manager

# Install Python dependencies
pip install -r requirements.txt

# Run the application as root
sudo python main.py
```

## Usage

1. **Access the Web Interface**
   - Open your browser and navigate to `http://localhost:5080`

2. **Generate Server Configuration**
   - Click "Generate WireGuard Config" to create your initial server setup

3. **Manage Peers**
   - Navigate to the "Peers" tab
   - Add new peers with the "Add Peer" button
   - Export peer configurations with QR codes for easy mobile setup
   - Delete peers as needed

4. **Export Configurations**
   - Each peer can be exported with a QR code
   - Customize DNS and Endpoint settings before export
   - Perfect for mobile WireGuard clients

## Configuration

The application uses the standard WireGuard configuration file located at `/etc/wireguard/wg0.conf`. All peer and server configurations are stored in this file.

**Default Settings:**
- Server Address: `11.0.0.1/24`
- Listen Port: `51820`
- Peer IP Range: `11.0.0.2/32` onwards

## Security Notes

- **Root Required**: This application must run as root to access and modify system WireGuard configurations
- **Local Access**: By default, the web interface is accessible from any IP (`0.0.0.0:5080`)
- **Production Use**: Consider adding authentication and HTTPS for production deployments

## Why This Project?

This project was designed to be:
- **Minimal**: Few dependencies, just Python and WireGuard
- **Portable**: Works across different Linux distributions
- **Simple**: Git clone, install requirements, run

Perfect for quickly setting up WireGuard management on servers, VPS instances, or local networks without complex setup procedures.

## Troubleshooting

**Permission Errors:**
- Ensure you're running as root: `sudo python main.py`

**WireGuard Commands Not Found:**
- Verify WireGuard is installed: `wg --version`

**Configuration Issues:**
- Check `/etc/wireguard/wg0.conf` exists and is readable
- Verify firewall rules allow traffic on port 51820
