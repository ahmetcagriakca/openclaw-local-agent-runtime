# Task F1.5 — Reboot Readiness Package: Report

## Tasarim Ozeti

Runtime'in kontrollü reboot dogrulamasina hazir olmasini saglayan ve reboot readiness'i observable yapan bir paket eklendi.

**Temel ayrım:**
- **READY** = tum on-kosullar karsilaniyor, reboot guvenli
- **VERIFIED** = gercek reboot sonrasi tum kontroller gecti (bu raporda henuz claim edilmiyor)

**Eklenen bilesenler:**
1. `oc-reboot-validate.ps1` — 3 fazli dogrulama script'i (pre/post/smoke)
2. Health'e `lastPreflightUtc` ve `lastWatchdogUtc` alanlari eklendi
3. Dokumante edilmis operator proseduru

---

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-reboot-validate.ps1` | **YENi** — 3 fazli reboot validation script (pre/post/smoke) |
| `bin/oc-task-health.ps1` | `lastPreflightUtc` ve `lastWatchdogUtc` alanlari eklendi (control-plane.log'dan parse) |
| `bin/oc-task-common.ps1` | Config'e `RebootValidatePath` eklendi |

---

## Tam Patch

### oc-reboot-validate.ps1 (YENi — 3 faz)

**Phase: pre** (reboot oncesi)
- 3 scheduled task registered ve enabled (preflight, worker, watchdog)
- 5 key script mevcut
- Manifest parseable
- Stuck task yok
- Pending ticket yok
- Active lease yok
- Sonuc: READY veya NOT_READY

**Phase: post** (reboot + login sonrasi)
- Preflight calismi (lastPreflightUtc kontrolu)
- Health status ok
- 3 scheduled task hala registered
- Worker active (login sonrasi)
- Stuck task yok
- Sonuc: VERIFIED veya NOT_READY

**Phase: smoke** (end-to-end task testi)
- create_note task enqueue
- Task tamamlanmasini bekle (max 30s)
- Result dosyasi kontrol
- Sonuc: VERIFIED veya NOT_READY

### oc-task-health.ps1 — yeni alanlar

```diff
+$lastPreflightUtc = $null
+$lastWatchdogUtc = $null
+# Parse from last 200 lines of control-plane.log
+# Look for "[preflight] Startup preflight finished" and "[watchdog] Watchdog finished"
+
+    lastPreflightUtc = $lastPreflightUtc
+    lastWatchdogUtc = $lastWatchdogUtc
```

---

## Reboot Validation Proseduru

### Adim 1: Pre-reboot kontrol

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase pre
```

Beklenen: `"result": "READY"`, tum checkler PASS.
Eger NOT_READY ise reboot yapmayin, fail eden checkleri cozun.

### Adim 2: Reboot

```powershell
Restart-Computer
```

### Adim 3: Login sonrasi post-reboot kontrol

Login yaptiktan sonra 1-2 dk bekleyin (worker ve watchdog baslasin), sonra:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase post
```

Beklenen: `"result": "VERIFIED"`, tum checkler PASS.
Ozellikle: `preflight ran = PASS`, `worker active = PASS`.

### Adim 4: End-to-end smoke test

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase smoke
```

Beklenen: `"result": "VERIFIED"`, task succeeded, result dosyasi mevcut.

### Adim 5: Health dogrulama

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1
```

`lastPreflightUtc` reboot sonrasinin timestamp'ini gostermeli.
`lastWatchdogUtc` 15dk icinde guncel olmali.

---

## Observed Output (reboot oncesi)

### Pre-reboot: READY

```json
{
    "phase": "pre",
    "result": "READY",
    "pass": 8,
    "fail": 0,
    "checks": [
        { "check": "preflight task", "result": "PASS", "detail": "OpenClawStartupPreflight = Ready" },
        { "check": "worker task", "result": "PASS", "detail": "OpenClawTaskWorker = Ready" },
        { "check": "watchdog task", "result": "PASS", "detail": "OpenClawRuntimeWatchdog = Ready" },
        { "check": "key scripts", "result": "PASS", "detail": "5 checked" },
        { "check": "manifest", "result": "PASS", "detail": "...manifest.json" },
        { "check": "no stuck tasks", "result": "PASS", "detail": "stuck=0" },
        { "check": "no pending tickets", "result": "PASS", "detail": "pending=0" },
        { "check": "no active leases", "result": "PASS", "detail": "leases=0" }
    ]
}
```

### Post-reboot (reboot olmadan): NOT_READY

```json
{
    "phase": "post",
    "result": "NOT_READY",
    "pass": 6,
    "fail": 1,
    "checks": [
        { "check": "preflight ran", "result": "PASS", "detail": "lastPreflightUtc=2026-03-22T17:34:15Z" },
        { "check": "health status", "result": "PASS" },
        { "check": "preflight task", "result": "PASS" },
        { "check": "worker task", "result": "PASS" },
        { "check": "watchdog task", "result": "PASS" },
        { "check": "worker active", "result": "FAIL", "detail": "workerActive=False" },
        { "check": "no stuck tasks", "result": "PASS" }
    ]
}
```

Worker active=FAIL beklenen — gercek login trigger olmadan worker baslamaz.

### Smoke test: VERIFIED

```json
{
    "phase": "smoke",
    "result": "VERIFIED",
    "pass": 3,
    "fail": 0,
    "checks": [
        { "check": "enqueue", "result": "PASS", "detail": "taskId=task-20260322-175422630-5427" },
        { "check": "task completed", "result": "PASS", "detail": "status=succeeded elapsed=6s" },
        { "check": "result file", "result": "PASS", "detail": "...reboot-smoke-20260322-175422.txt" }
    ]
}
```

### Health — yeni alanlar

```json
{
    "status": "ok",
    "lastPreflightUtc": "2026-03-22T17:34:15.4605053Z",
    "lastWatchdogUtc": "2026-03-22T17:45:04.9482995Z"
}
```

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Gercek reboot testi yapilmadi** | Pre-reboot READY ve smoke VERIFIED kanitlandi. Post-reboot VERIFIED icin gercek reboot gerekli. Bu rapor overclaim yapmiyor. |
| 2 | **Post-reboot worker active check** | Worker sadece AtLogon trigger ile baslar. Post-reboot kontrolu login sonrasi 1-2 dk bekleme gerektirir. |
| 3 | **lastPreflightUtc log-based** | control-plane.log'un son 200 satirindan parse ediliyor. Log rotate sonrasi kaybolabilir. |
| 4 | **Smoke test worker gerektirir** | Smoke phase calismasi icin worker'in aktif olmasi gerekir (enqueue worker'i kick eder). |
| 5 | **Bootstrap henuz oc-reboot-validate.ps1 deploy etmiyor** | Script live dosyadan calisir, bootstrap heredoc'u yok. |
