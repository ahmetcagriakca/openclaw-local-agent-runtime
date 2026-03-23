# Task F1.4-behavior — Prove Stuck Task Policy Behavior: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-task-common.ps1` | `ConvertTo-OcUtcDateTime` ve `Get-OcUtcAgeMinutes` helper fonksiyonlari eklendi (timezone bug fix) |
| `bin/oc-runtime-watchdog.ps1` | `[DateTime]::Parse` -> `Get-OcUtcAgeMinutes` (2 yer), em-dash -> ASCII dash |
| `bin/oc-runtime-startup-preflight.ps1` | `[DateTime]::Parse` -> `Get-OcUtcAgeMinutes` (2 yer), em-dash -> ASCII dash |
| `bin/oc-task-health.ps1` | `[DateTime]::Parse` -> `Get-OcUtcAgeMinutes` (1 yer) |
| `bin/oc-task-repair.ps1` | `[DateTime]::Parse` -> `ConvertTo-OcUtcDateTime` (2 yer) |
| `bin/oc-task-worker.ps1` | `[DateTime]::Parse` -> `Get-OcUtcAgeMinutes` (1 yer) |

## Timezone Bug Fix

Tum script'lerde `[DateTime]::Parse("...Z")` kullanimi UTC timestamp'i local time'a donusturuyordu (UTC+3 ortamda). Bu, yas hesaplamasini 180 dk (3 saat) yanlis yapiyordu. Fix: `Get-OcUtcAgeMinutes` helper fonksiyonu `.ToUniversalTime()` ile dogru hesaplama yapiyor.

---

## Test Senaryolari

6 sentetik task olusturuldu:

| Probe | TaskId | Status | Age | Beklenen Davranis |
|-------|--------|--------|-----|-------------------|
| 1 | task-99990001-...-0001 | running | 20 min | Hicbir threshold'u asmaz |
| 2 | task-99990001-...-0002 | running | 35 min | Health uyari (>30), watchdog yok (<60) |
| 3 | task-99990001-...-0003 | queued | 45 min | Health uyari (>30), watchdog yok (<60) |
| 4 | task-99990001-...-0004 | running | 65 min | Case A: auto-fail (>60, no worker, no lease) |
| 5 | task-99990001-...-0005 | cancel_requested | 90 min | Case A: auto-cancel (>60, no worker, no lease) |
| 6 | task-99990001-...-0006 | running + lease | 70 min | Case B: ambiguous (>60, lease var), mutasyon yok |

---

## Smoke Test Komutlari ve Observed Output

### Step 1: Health (warning threshold 30 min)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1
```

```json
{
    "status": "degraded",
    "statusReasons": ["stuck tasks: 5"],
    "nonTerminalTasks": 6,
    "stuckTasks": 5,
    "stuckCaseA": 4,
    "stuckCaseB": 1
}
```

- Probe 1 (20 min): nonTerminal ama stuck degil (< 30) -> DOGRU
- Probe 2 (35 min): stuck, Case A -> DOGRU
- Probe 3 (45 min): stuck, Case A -> DOGRU
- Probe 4 (65 min): stuck, Case A -> DOGRU
- Probe 5 (90 min): stuck, Case A -> DOGRU
- Probe 6 (70 min + lease): stuck, Case B -> DOGRU

### Step 2: Preflight (recovery threshold 60 min, observe-only)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1
```

```json
{
    "phase": "startup-preflight",
    "status": "degraded",
    "checks": ["stuck tasks: 3 (Case A safe: 2, Case B ambiguous: 1)"],
    "repairs": [],
    "stuckTasks": 3,
    "stuckCaseA": 2,
    "stuckCaseB": 1
}
```

- Probe 2 (35 min): recovery threshold altinda (< 60) -> gorulmedi -> DOGRU
- Probe 3 (45 min): recovery threshold altinda (< 60) -> gorulmedi -> DOGRU
- Probe 4 (65 min): Case A, sadece raporlandi, MUTASYON YOK -> DOGRU
- Probe 5 (90 min): Case A, sadece raporlandi, MUTASYON YOK -> DOGRU
- Probe 6 (70 min): Case B, sadece raporlandi -> DOGRU
- `repairs: []` — preflight hicbir sey degistirmedi -> DOGRU

### Step 3: Watchdog (recovery threshold 60 min, acts on Case A)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1
```

```json
{
    "phase": "watchdog",
    "status": "degraded",
    "checks": ["stuck tasks: 3 (Case A auto-resolved: 2, Case B ambiguous: 1)"],
    "repairs": [
        "Case A: task-99990001-000000004-0004 running -> failed",
        "Case A: task-99990001-000000005-0005 cancel_requested -> cancelled"
    ],
    "stuckSafeRecovered": 2,
    "stuckAmbiguous": 1
}
```

- Probe 4 (65 min, running): Case A -> **auto-failed** -> DOGRU
- Probe 5 (90 min, cancel_requested): Case A -> **auto-cancelled** -> DOGRU
- Probe 6 (70 min, lease): Case B -> **mutasyon yok** -> DOGRU

### Step 4: Task state verification

| Probe | Status before | Status after | lastError | Event |
|-------|--------------|-------------|-----------|-------|
| 1 | running | running | null | (no change) |
| 2 | running | running | null | (no change) |
| 3 | queued | queued | null | (no change) |
| 4 | running | **failed** | "Stuck task auto-failed by watchdog (Case A)..." | `stuck_task_auto_failed` |
| 5 | cancel_requested | **cancelled** | "Stuck task auto-cancelled by watchdog (Case A)..." | `stuck_task_auto_cancelled` |
| 6 | running | running | null | (no recovery event — Case B) |

### Step 5: Log entries

```
[preflight] Stuck task (Case A safe): ...0004 status=running age=65min - deferred to watchdog
[preflight] Stuck task (Case A safe): ...0005 status=cancel_requested age=90min - deferred to watchdog
[preflight] Stuck task (Case B ambiguous): ...0006 status=running age=70min
[preflight] 3 stuck tasks detected. Case A=2 Case B=1
[watchdog] Case A (safe stuck): ...0004 running -> failed (age=66min)
[watchdog] Case A (safe stuck): ...0005 cancel_requested -> cancelled (age=91min)
[watchdog] Case B (ambiguous): ...0006 status=running age=71min workerActive=False hasLease=True
[watchdog] Stuck tasks: total=3 safeRecovered=2 ambiguous=1
```

### Step 6: Post-recovery health

```json
{
    "status": "degraded",
    "stuckTasks": 3,
    "stuckCaseA": 2,
    "stuckCaseB": 1,
    "nonTerminalTasks": 4
}
```

Health hala probes 2, 3, 6'yi uyari olarak gosteriyor (warning threshold 30 min). Probes 4, 5 artik terminal (failed/cancelled) oldugu icin gorunmuyor.

---

## Threshold Boundary Evidence Tablosu

| Age | Health (>30) | Preflight (>60) | Watchdog (>60) | Kanit |
|-----|-------------|----------------|----------------|-------|
| 20 min | gorunmez | gorunmez | gorunmez | Probe 1: nonTerminal=6 ama stuckTasks=5 (20min dahil degil) |
| 35 min | **stuck** | gorunmez | gorunmez | Probe 2: health'te stuck, preflight/watchdog'da yok |
| 45 min | **stuck** | gorunmez | gorunmez | Probe 3: health'te stuck, preflight/watchdog'da yok |
| 65 min | **stuck** | **Case A** (raporla) | **Case A** (auto-fail) | Probe 4: tum seviyeler goruyor, watchdog aksiyon alir |
| 70 min | **stuck (B)** | **Case B** (raporla) | **Case B** (mutasyon yok) | Probe 6: lease var, hic mutasyon yok |
| 90 min | **stuck** | **Case A** (raporla) | **Case A** (auto-cancel) | Probe 5: cancel_requested -> cancelled |

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Bootstrap heredoc'lardaki timezone bug** | Bootstrap'taki embedded health/worker heredoc'lari hala `[DateTime]::Parse` kullaniyor. Sonraki bootstrap sync'te guncellenecek. |
| 2 | **Sentetik testler temizlendi** | Test task'lari calistirma sonrasinda silindi. Tekrar icin ayni komutlar kullanilabilir. |
| 3 | **Gercek reboot testi yok** | Preflight AtStartup davranisi sentetik olarak test edildi, gercek reboot ile degil. |
