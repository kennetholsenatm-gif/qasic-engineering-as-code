# IoC Discovery — Installation

One script handles dependency checks and installation for both **from-source** and **RPM** (AlmaLinux 10 / RHEL 10 / Rocky 10).

## Quick start

From the repository root:

```bash
# Check what's missing (no install)
./scripts/install.sh --check-only

# Install everything from source (system deps + Python deps)
./scripts/install.sh -y

# Run discovery
python3 -m discovery.run_discovery
```

## Options

| Option | Description |
|--------|-------------|
| `--check-only` | Only verify dependencies; do not install. |
| `--from-source` | Install from repo: system packages + pip (default). |
| `--rpm` | Build and install RPM via dnf (AlmaLinux/RHEL/Rocky only). |
| `-y`, `--yes` | Non-interactive (yes to all installs). |
| `-h`, `--help` | Show usage. |

## What gets installed

- **Required:** `python3`, `python3-pyyaml`, Python packages: `PyYAML`, `ldap3`, `scapy`.
- **Recommended:** `nmap`, `ncat` (often `nmap-ncat` on RHEL).
- **Optional:** `lldpd` (for `lldpcli`), `python3-ldap3`, `python3-scapy` (from EPEL on RHEL/Alma).

The installer detects **dnf** (RHEL/Alma/Rocky/Fedora), **yum**, **apt** (Debian/Ubuntu), or **brew** (macOS) and installs system packages when you run it without `--check-only`.

## Install from source (any supported OS)

```bash
./scripts/install.sh -y
cd /path/to/repo && python3 -m discovery.run_discovery
```

Config: `config/discovery_config.yaml`  
Output: `output/`

## Install via RPM (AlmaLinux 10 / RHEL 10 / Rocky 10)

```bash
./scripts/install.sh --rpm -y
ioc-discovery
```

Config: `/etc/ioc-discovery/`  
Output: `/var/lib/ioc-discovery/`

Optional tools after RPM install:

```bash
sudo dnf install -y nmap nmap-ncat lldpd
sudo dnf install -y epel-release && sudo dnf install -y python3-ldap3 python3-scapy
```

## Manual dependency install

- **AlmaLinux / RHEL / Rocky:**  
  `sudo dnf install -y python3 python3-pip python3-pyyaml nmap nmap-ncat lldpd`  
  Then: `pip3 install --user PyYAML ldap3 scapy` (or use system `python3-ldap3` / `python3-scapy` from EPEL).
- **Debian / Ubuntu:**  
  `sudo apt-get install -y python3 python3-pip python3-yaml nmap netcat-openbsd lldpd`  
  Then: `pip3 install --user PyYAML ldap3 scapy`.

## Troubleshooting

- **"No supported package manager"** — Install Python 3 and pip, then:  
  `pip3 install PyYAML ldap3 scapy`.  
  Install `nmap` and `ncat` from your OS docs.
- **Permission denied on install.sh** — Run: `chmod +x scripts/install.sh`.
- **Discovery fails with "No module named discovery"** — Run from repo root, or set:  
  `export PYTHONPATH=/path/to/repo` (or `/usr` when using the RPM).
