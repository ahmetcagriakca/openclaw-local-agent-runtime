# WSL + OpenClaw Stability Hardening

**Date:** 2026-03-24
**Status:** IMPLEMENTED
**Scope:** WSL lifecycle management, OpenClaw service supervision, memory bounding
**Supersedes:** sleep infinity keepalive (Phase 1.6 WSL Guardian passive approach)

---

## 1. Problem Statement

OpenClaw runs inside WSL Ubuntu-E. Telegram bot connectivity depends on OpenClaw staying alive. Observed failures:

- WSL idle shutdown (default vmIdleTimeout = 60 seconds) kills the VM, Telegram goes silent
- `sleep infinity` keepalive is blind — keeps WSL alive but doesn't detect or recover OpenClaw crashes
- No memory bounds — WSL can consume unlimited host RAM, eventually degrading the host
- No service lifecycle — OpenClaw started manually, no auto-restart on crash

**Diagnostic evidence:** Memory snapshot showed 912 MiB used / 5.8 GiB total — the issue was NOT memory exhaustion. It was WSL lifecycle + process supervision. openclaw-gateway at 119% CPU suggested event loop contention, not OOM.

**Root cause:** Not "needs more RAM" but "needs bounded always-on WSL + supervised OpenClaw."

---

## 2. Solution Architecture

Four coordinated changes:

```
┌─────────────────────────────────────────────┐
│ Windows Host                                │
│                                             │
│  .wslconfig ──► Bounded VM (6GB/4GB swap)   │
│                 vmIdleTimeout = 30 min       │
│                 autoMemoryReclaim = gradual  │
│                                             │
│  WSL Guardian ──► Windows-side monitoring    │
│  (oc-wsl-guardian.ps1, existing Phase 1.6)  │
│                                             │
├─────────────────────────────────────────────┤
│ WSL Ubuntu-E                                │
│                                             │
│  systemd ──► openclaw.service               │
│              (auto-start, auto-restart)      │
│                                             │
│  systemd ──► wsl-openclaw-keepalive.service │
│              (health loop, WSL alive signal) │
│                                             │
│  /etc/wsl.conf ──► systemd=true             │
└─────────────────────────────────────────────┘
```

---

## 3. Changes Applied

### 3.1 .wslconfig — Bounded WSL VM

**Location:** `C:\Users\AKCA\.wslconfig`

```ini
[wsl2]
memory=6GB
processors=4
swap=4GB
vmIdleTimeout=1800000
guiApplications=false
localhostForwarding=true

[experimental]
autoMemoryReclaim=gradual
```

| Setting | Value | Purpose |
|---------|-------|---------|
| memory | 6GB | Hard ceiling — WSL cannot consume more than 6GB host RAM |
| processors | 4 | CPU core limit |
| swap | 4GB | Swap space inside VM |
| vmIdleTimeout | 1800000 (30 min) | Up from default 60s — prevents premature VM shutdown |
| guiApplications | false | No GUI needed, saves resources |
| localhostForwarding | true | Required for WMCP (:8001) and agent communication |
| autoMemoryReclaim | gradual | Periodically returns unused pages to host |

### 3.2 /etc/wsl.conf — systemd Enabled

```ini
[boot]
systemd=true
```

Enables systemd as init system inside WSL. Required for service management.

### 3.3 OpenClaw systemd Service

**Start script:** `/usr/local/bin/openclaw-start.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
export HOME=/home/akca
cd /home/akca/.openclaw
exec /home/akca/.npm-global/bin/openclaw start
```

**Service unit:** `/etc/systemd/system/openclaw.service`

```ini
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=akca
WorkingDirectory=/home/akca/.openclaw
Environment=HOME=/home/akca
Environment=NODE_OPTIONS=--max-old-space-size=1024
ExecStart=/usr/local/bin/openclaw-start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

| Setting | Purpose |
|---------|---------|
| Restart=always | Auto-restart on any exit (crash, OOM kill, etc.) |
| RestartSec=5 | 5 second cooldown between restarts |
| NODE_OPTIONS=--max-old-space-size=1024 | Node.js heap cap at 1GB — prevents memory leak runaway |

### 3.4 Purpose-Built Keepalive (replaces sleep infinity)

**Script:** `/usr/local/bin/wsl-openclaw-keepalive.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

while true; do
  if ! systemctl is-active --quiet openclaw.service; then
    systemctl restart openclaw.service || true
  fi
  sleep 20
done
```

**Service unit:** `/etc/systemd/system/wsl-openclaw-keepalive.service`

```ini
[Unit]
Description=Keep WSL alive for OpenClaw Telegram connectivity
After=openclaw.service
Requires=openclaw.service

[Service]
Type=simple
ExecStart=/usr/local/bin/wsl-openclaw-keepalive.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Why this is better than sleep infinity:**

| Aspect | sleep infinity | Keepalive service |
|--------|---------------|-------------------|
| WSL alive | Yes | Yes |
| Detects OpenClaw crash | No | Yes (20s interval) |
| Restarts OpenClaw | No | Yes (via systemctl) |
| CPU cost | ~0 | ~0 (sleep 20 loop) |
| Memory cost | ~0 | ~0 |
| Observability | None | systemctl status, journalctl |

---

## 4. Activation Sequence

```bash
# Inside WSL Ubuntu-E:
sudo systemctl daemon-reload
sudo systemctl enable openclaw.service
sudo systemctl enable wsl-openclaw-keepalive.service
sudo systemctl start openclaw.service
sudo systemctl start wsl-openclaw-keepalive.service
```

```powershell
# Windows side (apply .wslconfig):
wsl --shutdown
wsl -d Ubuntu-E
```

---

## 5. Verification Commands

```bash
# Service status
systemctl status openclaw.service --no-pager
systemctl status wsl-openclaw-keepalive.service --no-pager

# Process and memory
ps aux --sort=-%mem | head -n 10
free -h

# Logs
journalctl -u openclaw.service -n 100 --no-pager
journalctl -u wsl-openclaw-keepalive.service -n 50 --no-pager
```

---

## 6. Interaction with Existing Components

### WSL Guardian (bin/oc-wsl-guardian.ps1)

The Windows-side WSL Guardian (Phase 1.6) remains operational. It provides a second layer of monitoring:

| Layer | Component | Scope | Recovery |
|-------|-----------|-------|----------|
| L1 (WSL-internal) | keepalive service | OpenClaw process health | systemctl restart openclaw |
| L2 (Windows-side) | WSL Guardian | WSL VM + OpenClaw existence | WSL restart, OpenClaw restart, Telegram alert |

The two layers are complementary:
- **L1** handles fast OpenClaw process recovery (20s detection, 5s restart)
- **L2** handles WSL VM-level failures (30s detection, VM restart, Telegram notification)

### Scheduled Tasks

No changes to Windows scheduled tasks. OpenClawWslGuardian (AtLogOn) continues to run.

---

## 7. Decision Record

| ID | Decision | Rationale |
|----|----------|-----------|
| WSL-1 | Memory bounded at 6GB | Prevents WSL from consuming all host RAM. Diagnostic showed current usage <1GB, 6GB is generous ceiling. |
| WSL-2 | vmIdleTimeout = 30 min | Default 60s too aggressive for always-on bot. 30 min balances power savings with connectivity. |
| WSL-3 | systemd for OpenClaw lifecycle | Official WSL-supported approach. Replaces manual `nohup openclaw start &`. |
| WSL-4 | Node heap cap 1024MB | Guard against Node.js memory leaks. OpenClaw RSS was ~672MB at diagnostic time. |
| WSL-5 | Keepalive replaces sleep infinity | Same WSL-alive function + OpenClaw health check + restart capability. |
| WSL-6 | autoMemoryReclaim=gradual | Returns unused pages to host without aggressive dropping that could cause latency spikes. |

---

## 8. Known Limitations

| Limitation | Severity | Mitigation |
|------------|----------|------------|
| 30-min idle timeout still allows shutdown if both services stopped | Low | Guardian detects and restarts from Windows side |
| Node heap cap may need tuning | Low | Monitor via journalctl for OOM exits, adjust if needed |
| No alerting from WSL-internal keepalive | Low | Guardian (L2) handles Telegram alerts |
| wsl --shutdown required for .wslconfig changes | Operational | One-time; documented in activation sequence |
| systemd in WSL is Microsoft-supported but not all features work | Low | Only using basic service management (Type=simple, Restart=always) |

---

**Documented:** 2026-03-24 | Based on diagnostic analysis + GPT collaboration
**Related:** Phase 1.6 WSL Guardian, D-021 (WSL Guardian replaces WSLKeepAlive)
