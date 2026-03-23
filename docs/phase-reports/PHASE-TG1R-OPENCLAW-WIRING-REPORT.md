# Phase TG-1R — Mevcut OpenClaw Telegram Baglantisi ve Gercek Kapatma Hazirligi Raporu

**Durum:** TAMAMLANDI — Gercek Telegram kapatmaya hazir
**Tarih:** 2026-03-23
**Kapsam:** Mevcut OpenClaw Telegram entegrasyonunu kanonik cagiran yol olarak kullanma, Bridge baglantisini tamamlama

---

## 1. Ozet

OpenClaw zaten WSL Ubuntu-E ortaminda Telegram baglantisina sahip. Bu adim, mevcut OpenClaw Telegram yolunu dondurulan Bridge kontratina baglamak icin gereken minimum degisiklikleri uygular.

| Bilesen | Durum |
|---------|-------|
| OpenClaw (npm paketi) | Yuklu ve konfigre (`openclaw@2026.3.13`) |
| Telegram eklentisi | Aktif (bot token konfigre) |
| Gercek kullanici ID | `8654710624` (OpenClaw allowFrom'da mevcut) |
| Bridge baglantisi | **Tamamlandi** (bu adimda) |
| Bridge allowlist | **Guncellendi** (gercek kullanici ID eklendi) |

---

## 2. Mevcut OpenClaw Telegram Yolu

### 2.1 OpenClaw Konumu

| Bilesen | Yol |
|---------|-----|
| npm paketi | `/home/akca/.npm-global/lib/node_modules/openclaw/` |
| Konfigurasyon | `/home/akca/.openclaw/` |
| Ana konfig | `/home/akca/.openclaw/openclaw.json` |
| Ortam degiskenleri | `/home/akca/.openclaw/.env` |
| Telegram kimlik bilgileri | `/home/akca/.openclaw/credentials/` |
| Arac betikleri | `/home/akca/bin/` |

### 2.2 Telegram Eklenti Durumu

```
channels.telegram.enabled: true
channels.telegram.dmPolicy: "pairing"
channels.telegram.streaming: "partial"
channels.telegram.execApprovals.enabled: true
channels.telegram.execApprovals.approvers: [8654710624]
plugins.entries.telegram.enabled: true
```

### 2.3 Onceki Durum

OpenClaw'un mevcut arac betikleri (`oc-enqueue-task`, `oc-get-task`, vb.) runtime betiklerini **dogrudan** cagiriyordu — Bridge'i tamamen atliyordu. Bu betikler operator kullanimi icin kalir ama kanonik dis yol degil.

---

## 3. Token ve Konfigurasyon Kaynagi

| Gizli bilgi | Kaynak | Durum |
|-------------|--------|-------|
| Telegram bot tokeni | `/home/akca/.openclaw/.env` icinde `TELEGRAM_BOT_TOKEN` | Konfigure |
| Gercek kullanici ID | `8654710624` — OpenClaw allowFrom ve execApprovals'da | Konfigure |
| Bridge allowlist | `bridge/allowlist.json` | **Guncellendi** |

---

## 4. Bridge Baglanti Durumu

### 4.1 Olusturulan Bridge Sarmalayicilari

WSL icinde `/home/akca/bin/` altina bes bridge sarmalayicisi yuklendi:

| Betik | Dil | Amac |
|-------|-----|------|
| `oc-bridge-call` | Bash | Ham Bridge JSON cagrisi — `pwsh.exe -File bridge/oc-bridge.ps1` |
| `oc-bridge-submit` | Python | Gorev gonder — JSON olustur, `oc-bridge-call`'a ilet |
| `oc-bridge-status` | Python | Gorev durumu sorgula |
| `oc-bridge-cancel` | Python | Gorev iptal et |
| `oc-bridge-health` | Python | Runtime saglik kontrolu |

### 4.2 Neden Python

Bash ile JSON birlestirme, cok katmanli kabuk gecislerinde (WSL -> Windows -> PowerShell) tirnak isareti sorunlarina neden oluyordu. Python sarmalayicilari `json.dumps()` ile guvenilir JSON olusturur, ardindan `oc-bridge-call` (bash) uzerinden Bridge'i cagiirir.

### 4.3 Cagri Zinciri

```
Telegram kullanicisi
    -> OpenClaw (WSL)
        -> /home/akca/bin/oc-bridge-submit (Python)
            -> /home/akca/bin/oc-bridge-call (Bash)
                -> pwsh.exe -File bridge/oc-bridge.ps1 (Windows)
                    -> oc-task-enqueue.ps1 (runtime)
```

---

## 5. Gercek Kullanici Kimlik Bilgisi Yayilimi

| Katman | Kimlik bilgisi kaynagi |
|--------|----------------------|
| Telegram | Telegram sunucusu tarafindan atanan numerik ID: `8654710624` |
| OpenClaw | `credentials/telegram-default-allowFrom.json` icinde `allowFrom: ["8654710624"]` |
| Bridge sarmalayicilari | Varsayilan `sourceUserId` olarak sabit-kodlandi |
| Bridge allowlist | `bridge/allowlist.json` icinde `allowedUserIds: ["8654710624"]` |
| Bridge dogrulamasi | Adim 3'te allowlist'e karsi dogrulanir |
| Denetim kaydi | `sourceUserId: "8654710624"` olarak kaydedilir |

---

## 6. Allowlist Guncellemesi

`bridge/allowlist.json` guncellendi:

```json
{
  "allowedUserIds": [
    "test-user-001",
    "8654710624"
  ]
}
```

`8654710624`, OpenClaw konfigurasyonundaki gercek Telegram kullanici kimlik bilgisidir.

---

## 7. Uygulanan Minimum Degisiklikler

| Degisiklik | Dosya | Tur |
|------------|-------|-----|
| 5 bridge sarmalayici olusturuldu | `/home/akca/bin/oc-bridge-*` (WSL) | Yeni dosya |
| Gercek kullanici ID eklendi | `bridge/allowlist.json` | Konfigurasyon |
| Sarmalayici yukleyicisi | `telegram/install-wsl-wrappers.py` | Yardimci arac |

**Degistirilmeyen:**
- Bridge implementasyonu (`bridge/oc-bridge.ps1`) — degismedi
- Runtime betikleri — degismedi
- OpenClaw konfigurasyonu — degismedi
- Mevcut operator betikleri (`oc-enqueue-task` vb.) — yerinde kaldi

---

## 8. Dogrulama Kaniti

### 8.1 Saglik Testi (WSL -> Bridge -> Runtime)

```
Komut:  /home/akca/bin/oc-bridge-health
Yanit:  {"health":"ok","status":"ok","requestId":"tg-20260323022656-53046"}
Cikis:  0
```

### 8.2 Gorev Gonderimi (WSL -> Bridge -> Runtime)

```
Komut:  /home/akca/bin/oc-bridge-submit create_note '{"filename":"tg-final.txt","content":"WSL native Bridge path OK"}'
Yanit:  {"taskId":"task-20260322-233101445-7514","status":"accepted","taskName":"create_note","requestId":"tg-1774222260-53191"}
Cikis:  0
```

### 8.3 Yoklama — Devam Eden (3 sn sonra)

```
Komut:  /home/akca/bin/oc-bridge-status task-20260322-233101445-7514
Yanit:  {"taskStatus":"running","taskId":"task-20260322-233101445-7514","status":"in_progress","requestId":"tg-1774222264-53195"}
Cikis:  0
```

### 8.4 Yoklama — Terminal (25 sn sonra)

```
Komut:  /home/akca/bin/oc-bridge-status task-20260322-233101445-7514
Yanit:  {"result":{"summary":"Task completed successfully.","outputPreview":"===== STEP 1 / write_file =====\r\n..."},"taskStatus":"succeeded","taskId":"task-20260322-233101445-7514","status":"completed","requestId":"tg-1774222286-53212"}
Cikis:  0
```

### 8.5 Fiziksel Artifact

`results/tg-final.txt` icerigi: `WSL native Bridge path OK`

### 8.6 Denetim Kayitlari

Uc denetim satiri uretildi, hepsi `sourceUserId: "8654710624"` ile:

```
submit_task  -> outcome: allowed, runtimeTaskId: task-20260322-233101445-7514
get_task_status -> outcome: allowed, detail: in_progress: running
get_task_status -> outcome: allowed, detail: completed: succeeded
```

---

## 9. Kanonik Cagiran Yol Karari

### Kanonik dis cagiran yol

```
OpenClaw Telegram -> oc-bridge-submit/status/cancel/health -> oc-bridge-call -> bridge/oc-bridge.ps1 -> runtime
```

### Kanonik olmayan yollar

| Yol | Siniflandirma |
|-----|---------------|
| Dogrudan runtime betikleri (`oc-enqueue-task` vb.) | Operator-only — Bridge'i atlar |
| Bagimsiz Telegram bot (`telegram/oc-telegram-bot.py`) | Gecersiz kilindi — mevcut OpenClaw yolu tercih edilir |
| Ham eylem betikleri (`oc-run-action`, `oc-run-file`) | Yasak — dis kontrat disi |

---

## 10. OpenClaw Exec-Approval Notu

OpenClaw, arac betiklerini calistirmadan once kullanicidan onay ister (`execApprovals.enabled: true`). `oc-bridge-*` betikleri henuz exec-approval beyaz listesinde degil.

**Beklenen davranis:** OpenClaw bu betikleri ilk kez cagirdiginda, Telegram uzerinden kullanicidan onay isteyecek. Kullanici onayladiktan sonra betik beyaz listeye eklenir ve sonraki cagrilarda onay istenmez.

Bu, OpenClaw'un normal guvenlik modelidir ve Bridge kontratini etkilemez.

---

## 11. Gercek Telegram Kapatma Hazirlik Kontrolu

### EVET — Gercek Telegram Kapatmaya Hazir

Tamamlanan on kosullar:

| On kosul | Durum |
|----------|-------|
| Gercek Telegram kullanici ID allowlist'te | **Tamamlandi** (`8654710624`) |
| Bot token konfigure | **Tamamlandi** (OpenClaw `.env`'de) |
| WSL -> Bridge -> Runtime yolu calisiyor | **Dogrulandi** (saglik + gonderim + yoklama) |
| Bridge baslangic fail-closed calisiyor | **Dogrulandi** |
| Denetim kayitlari gercek kullanici ID ile | **Dogrulandi** |
| Kanonik cagiran yol belirlendi | **Tamamlandi** |

### Gercek Telegram testi icin adimlar

```
1. OpenClaw'un WSL'de calistigini dogrulayin
2. Telegram'dan OpenClaw botuna mesaj gonderin
3. Bot araciligiyla oc-bridge-submit calistirilmasini isteyin
4. Exec-approval onayi verin (ilk seferlik)
5. oc-bridge-status ile yoklama yapin
6. Sonucu Telegram'da gorun
7. Denetim kaydini dogrulayin
```
