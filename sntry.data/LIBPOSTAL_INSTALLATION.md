# Libpostal Installation Guide

This document provides instructions for installing Libpostal, which is required for advanced address parsing functionality in the Jamaica Business Directory system.

## Overview

Libpostal is a C library for parsing/normalizing street addresses around the world using statistical NLP and open data. The Python bindings (`postal`) provide access to this functionality.

## System Requirements

- macOS, Linux, or Windows (with WSL)
- C compiler (gcc or clang)
- autotools (autoconf, automake, libtool)
- pkg-config
- Python development headers

## Installation Steps

### macOS (using Homebrew)

1. **Install system dependencies:**
   ```bash
   brew install autoconf automake libtool pkg-config
   ```

2. **Install libpostal C library:**
   ```bash
   # Clone the repository
   git clone https://github.com/openvenues/libpostal
   cd libpostal
   
   # Build and install
   ./bootstrap.sh
   ./configure --datadir=[path where you want the data files]
   make -j4
   sudo make install
   
   # On Linux, you may need to run:
   sudo ldconfig
   ```

3. **Install Python bindings:**
   ```bash
   pip install postal
   ```

### Ubuntu/Debian Linux

1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y curl autoconf automake libtool pkg-config
   ```

2. **Install libpostal C library:**
   ```bash
   git clone https://github.com/openvenues/libpostal
   cd libpostal
   ./bootstrap.sh
   ./configure --datadir=/usr/local/share/libpostal
   make -j4
   sudo make install
   sudo ldconfig
   ```

3. **Install Python bindings:**
   ```bash
   pip install postal
   ```

### CentOS/RHEL/Fedora

1. **Install system dependencies:**
   ```bash
   # CentOS/RHEL
   sudo yum install -y autoconf automake libtool pkgconfig
   
   # Fedora
   sudo dnf install -y autoconf automake libtool pkgconfig
   ```

2. **Follow the same steps as Ubuntu for libpostal installation**

### Windows (WSL recommended)

For Windows users, we recommend using Windows Subsystem for Linux (WSL) and following the Ubuntu installation instructions.

## Data Files

Libpostal requires language/country-specific data files. These are automatically downloaded during the first run, but you can pre-download them:

```bash
# This will download ~2GB of data files
libpostal_data download all
```

## Verification

After installation, verify that everything works:

```python
from postal.parser import parse_address
from postal.expand import expand_address

# Test parsing
address = "123 Main Street, Kingston 10, Jamaica"
parsed = parse_address(address)
print("Parsed:", parsed)

# Test expansion
expanded = expand_address(address)
print("Expanded:", expanded[:3])  # Show first 3 variations
```

## Troubleshooting

### Common Issues

1. **"libpostal/libpostal.h not found"**
   - Ensure libpostal C library is properly installed
   - Check that pkg-config can find libpostal: `pkg-config --cflags libpostal`

2. **"No module named 'postal'"**
   - Install the Python bindings: `pip install postal`
   - Ensure you're using the correct Python environment

3. **Segmentation fault on import**
   - This usually indicates a version mismatch between libpostal and the Python bindings
   - Reinstall both components

4. **Data download fails**
   - Check internet connection
   - Ensure sufficient disk space (~2GB)
   - Try manual download: `libpostal_data download all`

### Performance Notes

- First run will be slow due to data file downloads
- Subsequent runs are much faster
- Consider pre-downloading data files in production environments

## Fallback Behavior

If Libpostal is not available, the system will automatically fall back to a custom address parsing implementation that handles Jamaican address formats. While less sophisticated, this fallback provides basic functionality for:

- Extracting house numbers and street names
- Identifying Jamaican postal zones (e.g., "KINGSTON 10")
- Recognizing parishes and major cities
- Standardizing address formats

## Production Deployment

For production deployments:

1. **Docker**: Include libpostal installation in your Dockerfile
2. **Pre-download data**: Include data files in your container image
3. **Health checks**: Verify libpostal functionality in your health check endpoints
4. **Monitoring**: Monitor parsing success rates and fallback usage

## Support

For issues specific to libpostal installation, refer to:
- [Libpostal GitHub repository](https://github.com/openvenues/libpostal)
- [Python postal bindings](https://github.com/openvenues/pypostal)

For issues specific to this project's address parsing implementation, check the project documentation or create an issue in the project repository.