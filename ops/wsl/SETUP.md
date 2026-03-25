# WSL Ubuntu-E Environment Setup — OpenClaw

## Prerequisites

- Windows 11 with WSL2 enabled
- Ubuntu-E distribution installed (`wsl --install -d Ubuntu-E`)

## Steps

### 1. System Packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git
```

### 2. Python 3.14

```bash
# Install from deadsnakes PPA or build from source
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.14 python3.14-venv python3.14-dev
```

### 3. Virtual Environment

```bash
cd ${OC_ROOT}
${PYTHON} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Clone Repository

```bash
git clone ${OC_REPO_URL} ${OC_ROOT}
cd ${OC_ROOT}
```

### 5. Environment Variables

```bash
cp ops/wsl/env.template ~/.openclaw/.env
# Edit ~/.openclaw/.env with your values
```

### 6. Verify

```bash
${PYTHON} -c "import sys; print(sys.version)"
cd ${OC_ROOT}/agent && ${PYTHON} -m pytest tests/ -v --tb=short
```

## Placeholders

| Variable | Description |
|----------|-------------|
| `${OC_ROOT}` | OpenClaw project root (e.g., `/home/akca/oc`) |
| `${PYTHON}` | Python binary (e.g., `python3.14`) |
| `${OC_REPO_URL}` | Git repository URL |
