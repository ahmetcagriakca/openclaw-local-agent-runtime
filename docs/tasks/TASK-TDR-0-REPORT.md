# Task TDR-0 — Telegram/OpenClaw/Bridge/oc runtime Inventory and Flow Mapping: Report

## 1. Component Inventory

| Katman | Durum | Nerede |
|--------|-------|--------|
| **Telegram Bot** | PLANNED — kod yok | Tasarim: ARCHITECTURE.md section 11 |
| **OpenClaw** | PLANNED — conversation layer yok | Tasarim: ARCHITECTURE.md section 2.1, 3.1-3.2 |
| **Bridge** | PLANNED — endpoint yok | Tasarim: ARCHITECTURE.md section 2.2, 10.1-10.4 |
| **oc runtime** | IMPLEMENTED + FROZEN | `C:\Users\AKCA\oc\bin\` (24 script) |
| **WMCP HTTP layer** | IMPLEMENTED — local MCP proxy | `bin/wmcp-call.ps1`, `bin/wmcp-api.ps1` |

---

## 2. Exact File/Process Names

### oc runtime (LIVE — Phase 1 complete)

| Rol | Dosya | Tetikleyici |
|-----|-------|-------------|
| Task enqueue | `bin/oc-task-enqueue.ps1` | CLI / bridge call |
| Task runner | `bin/oc-task-runner.ps1` | Worker uzerinden |
| Task worker | `bin/oc-task-worker.ps1` | AtLogon scheduled task |
| Startup preflight | `bin/oc-runtime-startup-preflight.ps1` | AtStartup scheduled task |
| Watchdog | `bin/oc-runtime-watchdog.ps1` | 15dk periodic scheduled task |
| Health | `bin/oc-task-health.ps1` | On-demand |
| Cancel | `bin/oc-task-cancel.ps1` | CLI / bridge call |
| Retry | `bin/oc-task-retry.ps1` | CLI / bridge call |
| Get/List/Output | `bin/oc-task-get.ps1`, `oc-task-list.ps1`, `oc-task-output.ps1` | On-demand |
| Action runner | `bin/oc-run-action.ps1` | Runner uzerinden |
| Reboot validate | `bin/oc-reboot-validate.ps1` | Manual |
| Rejection helpers | `bin/oc-task-common.ps1` (New-OcRejection, Write-OcRejectionAndExit) | Her script |

### WMCP HTTP layer (LIVE — local proxy)

| Dosya | Amac | Endpoint |
|-------|------|----------|
| `bin/wmcp-call.ps1` | PowerShell command execution via HTTP | `POST http://localhost:8001/PowerShell` |
| `bin/wmcp-api.ps1` | Generic JSON API call via HTTP | `POST http://localhost:8001/{path}` |

Varsayilan: `BaseUrl = http://localhost:8001`, `ApiKey = local-mcp-12345` (hardcoded default — uretim icin degistirilmeli).

### Telegram Bot (PLANNED — hicbir dosya yok)

Mevcut dosyalar: **yok**. Ne bot token, ne webhook config, ne allowlist dosyasi mevcut.

### OpenClaw (PLANNED — conversation layer yok)

Mevcut dosyalar: **yok**. Intent-to-task mapping kodu yok.

### Bridge (PLANNED — endpoint yok)

Mevcut dosyalar: **yok**. OpenClaw -> oc runtime ceviri kodu yok.

---

## 3. Exact Command Paths (Currently Known)

### Calisan yol: Manuel CLI -> oc runtime -> result dosyasi

```
Operator (terminal)
  |
  v
powershell.exe -File bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 <b64> -Source "manual"
  |
  v
queue/pending/p05-task-NNNN.json (ticket yazilir)
  |
  v
oc-task-worker.ps1 (ticket'i claim eder, leases/'e tasir)
  |
  v
oc-task-runner.ps1 -TaskId task-NNNN (action'lari calistirir)
  |
  v
oc-run-action.ps1 -ActionName write_file -PayloadB64 <b64> (powershell.exe 5.1)
  |
  v
results/from-telegram-final.txt (dosya yazilir)
  |
  v
task.json.status = "succeeded"
```

### Calisan yol: WMCP HTTP -> oc runtime

```
HTTP Client (veya OpenClaw)
  |
  v
POST http://localhost:8001/PowerShell
  Body: { "command": "& bin\\oc-task-enqueue.ps1 -TaskName create_note ...", "timeout": 30 }
  Header: Authorization: Bearer local-mcp-12345
  |
  v
wmcp-call.ps1 (veya wmcp-api.ps1)
  |
  v
oc-task-enqueue.ps1 (ayni akis)
```

### PLANLI ama MEVCUT OLMAYAN yol: Telegram -> Bridge -> oc runtime

```
Telegram User (mesaj gonderir)
  |
  v
[Telegram Bot Process] — YOK
  |
  v
[OpenClaw Intent Parser] — YOK
  |
  v
[Bridge Endpoint] — YOK
  Beklenen input: { "intent": "create_note", "arguments": {...}, "source": "telegram", "sourceUserId": "123" }
  |
  v
[Allowlist Check] — YOK (SOURCE_NOT_ALLOWED reserved)
  |
  v
[Intent -> Task Mapping] — YOK
  |
  v
oc-task-enqueue.ps1 -TaskName create_note -InputBase64 <b64> -Source "telegram" — HAZIR
  |
  v
(runtime akisi ayni)
  |
  v
[Bridge Response Translator] — YOK
  Beklenen: "Gorev siraya alindi." veya "Bu komut icin yetkin yok."
  |
  v
[Telegram Bot Reply] — YOK
```

---

## 4. End-to-End Sequence Description

```
TELEGRAM        OPENCLAW         BRIDGE           OC RUNTIME           RESULT
   |                |               |                  |                  |
   | mesaj          |               |                  |                  |
   |--------------->|               |                  |                  |
   |                | intent parse  |                  |                  |
   |                |-------------->|                  |                  |
   |                |               | allowlist check  |                  |
   |                |               | intent->task map |                  |
   |                |               |                  |                  |
   |                |               | enqueue_task     |                  |
   |                |               |----------------->|                  |
   |                |               |                  | validate         |
   |                |               |                  | queue            |
   |                |               |                  | worker claim     |
   |                |               |                  | runner execute   |
   |                |               |                  |----------------->|
   |                |               |                  |                  | write_file
   |                |               |                  |<-----------------|
   |                |               |                  | task.status=ok   |
   |                |               |<-----------------|                  |
   |                |               | translate reply  |                  |
   |                |<--------------|                  |                  |
   |                | format reply  |                  |                  |
   |<---------------|               |                  |                  |
   | "Dosya yazildi"|               |                  |                  |

LEGENDA:
  [TELEGRAM]  = Telegram Bot Process        — YOK
  [OPENCLAW]  = Conversation/Intent Layer   — YOK
  [BRIDGE]    = Translation + Trust Layer   — YOK (contract tanimli, kod yok)
  [OC RUNTIME]= Task Execution Engine       — CALISIYOR
  [RESULT]    = File/Artifact Output        — CALISIYOR
```

---

## 5. Gaps / Manual Steps List

| # | Gap | Kategori | Etki |
|---|-----|----------|------|
| 1 | **Telegram bot process yok** | Altyapi | Mesaj alinamaz, yanitlanamaz |
| 2 | **OpenClaw conversation layer yok** | Altyapi | Intent parse edilemez |
| 3 | **Bridge endpoint yok** | Altyapi | Intent -> task cevirisi yapilamaz |
| 4 | **Allowlist dosyasi yok** | Guvenlik | Kaynak dogrulamasi yok |
| 5 | **Bot token yok** | Guvenlik | Telegram API'ye baglanilamaz |
| 6 | **SOURCE_NOT_ALLOWED reserved** | Guvenlik | Runtime'da source filtreleme yok |
| 7 | **RUNTIME_UNAVAILABLE reserved** | Operasyon | Health-gate rejection yok |
| 8 | **Intent -> task mapping kodu yok** | Mantik | Hangi mesaj hangi task olacak belirsiz |
| 9 | **User-facing response templates yok** | UX | Runtime JSON -> kullanici mesaji cevirisi yok |
| 10 | **Result -> Telegram donusu yok** | Altyapi | Task sonucu kullaniciya iletilemez |

### Calisanlar (Runtime tarafinda HAZIR)

| # | Hazir olan | Kanit |
|---|-----------|-------|
| 1 | `-Source` parametresi tum task API'lerde | enqueue, retry, cancel |
| 2 | `source` alani task.json ve event'lerde | F1.3 ile eklendi |
| 3 | Rejection envelope `source` iceriyor | FROZEN (F1.3) |
| 4 | `SOURCE_NOT_ALLOWED` reason code tanimli | ARCHITECTURE.md section 9 |
| 5 | `RUNTIME_UNAVAILABLE` reason code tanimli | ARCHITECTURE.md section 9 |
| 6 | Bridge contract tanimli | ARCHITECTURE.md section 10 |
| 7 | WMCP HTTP layer calisiyor | wmcp-call.ps1, localhost:8001 |
| 8 | Onceki Telegram testlerinden result dosyalari | `results/from-telegram-final.txt`, `results/telegram-v3.txt` |

---

## 6. Remaining Risks

| # | Risk | Onem | Aciklama |
|---|------|------|----------|
| 1 | **WMCP API key hardcoded** | YUKSEK | `local-mcp-12345` wmcp-call.ps1 ve wmcp-api.ps1'de default olarak hardcoded. Uretim icin secret yonetimi gerekli. |
| 2 | **Bot token yoklugu** | YUKSEK | Telegram entegrasyonu baslamadan token storage + rotation proseduru olmali. |
| 3 | **Allowlist yoklugu** | YUKSEK | Bridge olmadan herhangi bir source dogrudan runtime'a erisebilir. |
| 4 | **Bridge tek-nokta-basarisizlik** | ORTA | Bridge olmadan Telegram -> runtime yolu tamamen manual. |
| 5 | **Intent mapping tanimlanmamis** | ORTA | Hangi Telegram komutu hangi task'a eslenecek belirsiz. |
| 6 | **Result delivery yok** | ORTA | Task basarili olsa bile kullanici sonucu goremez (Telegram reply yok). |
| 7 | **localhost:8001 dependency** | DUSUK | WMCP proxy'nin calisir durumda olmasi gerekiyor. Saglik kontrolu yok. |
