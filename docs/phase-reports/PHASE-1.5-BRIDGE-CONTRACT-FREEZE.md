# Phase 1.5 — Bridge Contract Freeze Raporu

**Durum:** FROZEN
**Tarih:** 2026-03-23
**Kapsam:** Phase 1.5-A (kapatildi), Phase 1.5-B (kapatildi), Phase 1.5-C (contract freeze)

---

## 1. Ozet

Bu belge, OpenClaw + oc runtime entegrasyon programinin Phase 1.5 surecinin tamamini kapsar:

| Alt-faz | Durum | Icerik |
|---------|-------|--------|
| Phase 1.5-A | KAPALI | Mimari kararlar donduruld |
| Phase 1.5-B | KAPALI | Kod/artifact temizligi tamamlandi |
| Phase 1.5-C | DONDURULDU | Bridge kontrati donduruld |

---

## 2. Phase 1.5-A — Dondurulan Mimari Kararlar

### 2.1 Sahiplik Sinirlari

| Sahip | Sorumluluklar |
|-------|---------------|
| **OpenClaw** | Konusma akisi, niyet cikarimi, parametre hazirligi, onay UX, sonuc anlatimi |
| **Bridge** | Ceviri, guven siniri, allowlist uygulamasi. **Asla orkestrator degil.** |
| **oc runtime** | **Gorev yurutme orkestrasyon tek sahibi.** Kuyruk, worker, runner, kurtarma, saglik. |

### 2.2 Entegrasyon Yuzeyi

- Dis entegrasyon yuzeyi **yalnizca gorev-merkezli** (enqueue, get, list, cancel, retry, health)
- **Ham eylem cagrisi** dis entegrasyon yolu olarak **yasak**
- Yerel manuel operator CLI bir yonetim istisnasi, genel entegrasyon yolu degil

### 2.3 Worker Modeli

- Kanonik worker modeli: **tekil gecis (ephemeral single-pass)**
- Eski kalici (persistent) worker ifadeleri **gecersiz kilindi**
- Worker aktvasyon yollari: AtLogOn zamanlanmis gorev, enqueue kick, retry kick, watchdog backstop kick

### 2.4 Diger Dondurulan Kararlar

- Polling-only modeli Phase 1.5 icin donduruldu
- Retry/cancel semantigi runtime'a ait
- Retry, Phase 1.5'te normal son kullanici yolu degil
- Tekrar gorev olusturma (duplicate) kabul edilen davranis
- Onay karari OpenClaw tarafindan olusturulur, Bridge tarafindan tasinir, runtime tarafindan uygulanir
- Bridge onay karari almaz
- requestId, OpenClaw tarafindan uretilir, yalnizca denetim/korelasyon icin kullanilir (dedupe degil)
- sourceUserId, Bridge'de allowlist uygulamasi icin zorunlu

---

## 3. Phase 1.5-B — Temizlik Ozeti

### 3.1 Silinen Artifactlar

| Dosya | Neden |
|-------|-------|
| `bin/oc-runtime-supervisor.ps1` | Olu supervisor yolu, cagiran yok, zamanlanmis gorev yok |
| `bin/oc-runtime-supervisor.ps1.bak-*` | Olu kodun yedegi |
| `bin/wmcp-api.ps1` | Aktif cagiran yok, gorev-merkezli degil, sabit kimlik bilgisi |

### 3.2 Yeniden Yapilandirilan Artifactlar

| Dosya | Degisiklik |
|-------|------------|
| `bin/oc-task-worker.ps1` | Kalici polling dongusu kaldirildi; her zaman tekil gecis |
| `bin/oc-task-common.ps1` | `Invoke-OcWorkerKick` fonksiyonuna `-Source` parametresi ve interaktif oturum tespiti eklendi |
| `bin/oc-runtime-watchdog.ps1` | Kick cagrisi `-Source 'watchdog'` iletiyor |
| `bin/oc-task-enqueue.ps1` | Kick cagrisi `-Source 'enqueue'` iletiyor |
| `bin/oc-task-retry.ps1` | Kick cagrisi `-Source 'retry'` iletiyor |
| `bin/wmcp-call.ps1` | Yalnizca dahili kullanim baslik notu, API anahtari env-var cevirim destegi |
| `oc-task-runtime-bootstrap-v3.4.ps1` | Supervisor kaldirim blogu temizlendi |
| `docs/ARCHITECTURE.md` | Phase 1.5-A dondurulan kararlar bolumu eklendi |
| `docs/SUPERVISOR-RESTART-RECOVERY-CANONICAL.md` | Eski geriye uyumluluk ifadesi duzeltildi |

---

## 4. Phase 1.5-C — Bridge Kontrati

### 4.1 Dis Kontrat: OpenClaw -> Bridge

Phase 1.5'te disa acik dort islem:

| Islem | Amac |
|-------|------|
| `submit_task` | Yeni gorev gonder |
| `get_task_status` | Gorev durumu ve sonuc sorgula (polling) |
| `cancel_task` | Terminal olmayan gorevi iptal et |
| `get_health` | Runtime uygunlugunu kontrol et |

**Retry dis kontratta YOK.** Retry yalnizca operator erisimine acik.

#### submit_task — Istek

```json
{
  "operation": "submit_task",
  "taskName": "create_note",
  "arguments": { "filename": "note.txt", "content": "hello" },
  "source": "telegram",
  "sourceUserId": "123456789",
  "requestId": "req-20260323-001",
  "approvalStatus": "approved"
}
```

| Alan | Zorunlu | Aciklama |
|------|---------|----------|
| `operation` | evet | Her zaman `"submit_task"` |
| `taskName` | evet | Gorev tanimi adi |
| `arguments` | evet | Gorev girdi parametreleri |
| `source` | evet | Kaynak kanal (ornegin `"telegram"`) |
| `sourceUserId` | evet | Kullanici kimlik bilgisi (allowlist icin) |
| `requestId` | evet | OpenClaw tarafindan uretilen benzersiz istek kimlik bilgisi |
| `approvalStatus` | evet | `"approved"`, `"preapproved"` veya `"pending"` |

#### submit_task — Yanit

```json
{
  "status": "accepted",
  "taskId": "task-20260323-143022541-7812",
  "taskName": "create_note",
  "requestId": "req-20260323-001"
}
```

| `status` degeri | Anlam |
|-----------------|-------|
| `"accepted"` | Gorev kuyruga alindi |
| `"rejected"` | Dogrulama/politika tarafindan reddedildi |
| `"error"` | Altyapi hatasi, tekrar denenebilir |

#### get_task_status — Istek/Yanit

Istek: `taskId`, `source`, `sourceUserId`, `requestId` ile gonderilir.

Yanit `status` degerleri:
- `"completed"` — Gorev terminal durumda. `taskStatus`: `"succeeded"`, `"failed"`, veya `"cancelled"`
- `"in_progress"` — Gorev devam ediyor. `taskStatus`: `"queued"`, `"running"`, veya `"cancel_requested"`
- `"not_found"` — Gorev bulunamadi
- `"error"` — Altyapi hatasi

#### cancel_task — Istek/Yanit

Istek: `taskId`, `source`, `sourceUserId`, `requestId` ile gonderilir.

Yanit `status` degerleri:
- `"acknowledged"` — Iptal istegi kabul edildi, polling ile takip edin
- `"rejected"` — Iptal reddedildi (gorev zaten terminal, vb.)

#### get_health — Yanit

```json
{
  "status": "ok",
  "health": "ok",
  "requestId": "req-20260323-004"
}
```

`health`: `"ok"`, `"degraded"`, veya `"error"`

### 4.2 Ic Kontrat: Bridge -> oc runtime

Bridge, oc runtime ile PowerShell betik cagrilari araciligiyla etkilesir.

#### Izin Verilen Islemler

| Islem | Betik | Katman |
|-------|-------|--------|
| Gorev gonder | `oc-task-enqueue.ps1` | Tier 1 |
| Gorev goruntusu al | `oc-task-get.ps1` | Tier 1 |
| Gorev ciktisi al | `oc-task-output.ps1` | Tier 1 |
| Gorev iptal | `oc-task-cancel.ps1` | Tier 1 |
| Gorev listele | `oc-task-list.ps1` | Tier 2 |
| Saglik kontrolu | `oc-task-health.ps1` | Tier 2 |

#### Yasakli Betikler (Bridge asla cagirmamali)

- `oc-run-action.ps1` — ham eylem yuzeyi
- `oc-run-file.ps1` — ham dosya yurutme
- `oc-task-repair.ps1` — yalnizca operator
- `oc-task-retry.ps1` — dis kontratta yok
- `oc-task-worker.ps1` — runtime-dahili
- `oc-runtime-watchdog.ps1` — runtime-dahili

#### policyContext Tasima

Bridge, dis istekteki alanlari runtime parametrelerine donusturur:

| Dis alan | Runtime parametresi |
|----------|-------------------|
| `taskName` | `-TaskName` |
| `arguments` | `-InputBase64` (base64-kodlanmis JSON) |
| `source` | `-Source` |
| `approvalStatus` = `"approved"` / `"preapproved"` | `-Approved` anahtari mevcut |
| `approvalStatus` = `"pending"` | `-Approved` anahtari yok |

### 4.3 Gorev Durum Yasam Dongusu

| Durum | Terminal | Disa Gorunur | Anlam |
|-------|----------|-------------|-------|
| `queued` | hayir | evet | Gorev kuyrukta bekliyor |
| `running` | hayir | evet | Worker gorevi aldi, yurutme devam ediyor |
| `succeeded` | evet | evet | Tum adimlar basariyla tamamlandi |
| `failed` | evet | evet | Yurutme basarisiz |
| `cancelled` | evet | evet | Gorev iptal edildi |
| `cancel_requested` | hayir | haritalandi | Iptal sinyali gonderildi, henuz uygulanmadi |

### 4.4 Polling Dizisi

```
1. OpenClaw -> Bridge: submit_task
2. Bridge -> Runtime: oc-task-enqueue.ps1
3. Runtime -> Bridge: taskId
4. Bridge -> OpenClaw: accepted + taskId

-- Polling dongusu baslar --

5. OpenClaw -> Bridge: get_task_status(taskId)
6. Bridge -> Runtime: oc-task-get.ps1(taskId)
7. Runtime -> Bridge: task.json snapshot
8a. Non-terminal -> Bridge -> OpenClaw: in_progress (tekrar 5'e don)
8b. Terminal -> Bridge -> Runtime: oc-task-output.ps1(taskId) [basari durumunda]
    Bridge -> OpenClaw: completed + result

-- Polling biter --
```

Polling durdurma kosullari:
- `status` = `"completed"` (gorev terminal)
- `status` = `"not_found"` (gorev yok)
- OpenClaw kendi konusma zamanasimiini asarsa (kontrat disi)

### 4.5 Ret ve Hata Haritasi

| Kosul | Dis errorCode | Tekrar denenebilir? |
|-------|---------------|---------------------|
| Bilinmeyen gorev adi | `UNKNOWN_TASK` | Hayir |
| Gecersiz arguman | `INVALID_INPUT` | Hayir — girdiyi duzelt |
| Gorev tanimi devre disi | `TASK_DISABLED` | Hayir |
| Kaynak allowlist'te yok | `SOURCE_NOT_ALLOWED` | Hayir |
| Onay gerekli ama verilmemis | `APPROVAL_REQUIRED` | Hayir — onayla ve tekrar gonder |
| Gorev bulunamadi | `TASK_NOT_FOUND` | Hayir |
| Terminal gorevde iptal | `CANCEL_REJECTED` | Hayir |
| Runtime erisim disi | `RUNTIME_UNAVAILABLE` | Evet |
| Bridge dahili hata | `BRIDGE_ERROR` | Evet |

Runtime `reasonCode` -> Dis `errorCode` cevirisi:

| Runtime | Dis |
|---------|-----|
| `UNKNOWN_TASK` | `UNKNOWN_TASK` |
| `INVALID_TASK_INPUT` | `INVALID_INPUT` |
| `TASK_POLICY_DENIED` | `TASK_DISABLED` |
| `SOURCE_NOT_ALLOWED` | `SOURCE_NOT_ALLOWED` |
| `APPROVAL_REQUIRED` | `APPROVAL_REQUIRED` |
| `TASK_STATE_INVALID` | `CANCEL_REJECTED` |

### 4.6 Retry / Cancel Gorunurluk Kurallari

| Islem | Dis Kontratta Gorunur mu? | Aciklama |
|-------|---------------------------|----------|
| Cancel | **EVET** | Herhangi bir yetkili cagiran iptal isteyebilir |
| Retry | **HAYIR** | Yalnizca operator erisimi (`oc-task-retry.ps1` yerel CLI) |

Kullanici tekrar denemek isterse: OpenClaw yeni bir `submit_task` gonderiir (yeni `requestId` ile). Bu bagimsiz yeni bir gorev olusturur. Kontrat seviyesinde retry baglantisi yoktur.

### 4.7 Onay Temsil Modeli

Onay akisi:
1. **OpenClaw karar verir** — gorev onay gerektiriyor mu?
2. **OpenClaw toplar** — gerekirse kullanicidan onay alir
3. **OpenClaw ayarlar** — `approvalStatus` disariya gonderir
4. **Bridge tasir** — `-Approved` anahtarina donusturur
5. **Runtime uygular** — `approvalPolicy: "manual"` ise ve `-Approved` yoksa reddeder

Bridge onay karari **ALMAZ**. Bridge yalnizca tasir.

---

## 5. Ertelenen Sorular

| Soru | Erteleme Nedeni |
|------|-----------------|
| Daha guclu dedupe (requestId-tabanli) | Phase 1.5'te tekrarlayan gorev olusturma kabul edilen davranis |
| Daha zengin policyContext tasima | Daha fazla runtime parametre genislemesi gerektirir |
| timeoutSeconds dis kontratta | Runtime dahili stuck-task politikasi (60 dk) yeterli |
| Push/callback/webhook bildirimleri | Polling-only Phase 1.5 icin donduruldu |
| Kaynak-gorev yetkilendirme matrisi | Phase 2 konusu |
| Bridge fiziksel formu | Kontrati dondurmak icin gerekli degil |
| Gorev sonuc artifact erisimi | Phase 1.5 yalnizca `outputPreview` saglar |
| Coklu-adim durum gorunurlugu | Phase 1.5 yalnizca gorev seviyesi durum gosterir |

---

## 6. Phase 1.5-C Cikis Kontrolu

| Kriter | Donduruldu mu? |
|--------|----------------|
| Tek kanonik dis istek zarfi | EVET |
| Tek kanonik dis yanit zarfi | EVET |
| Tek kanonik ic gonderim/sorgulama/kontrol yuzeyi | EVET |
| Tek polling-only dizisi | EVET |
| Tek durum yasam dongusu | EVET |
| Tek ret haritasi modeli | EVET |
| Tek retry/cancel gorunurluk kural seti | EVET |
| Tek onay temsil modeli | EVET |

**Tum kriterler donduruldu. Phase 1.5-C kapatilabilir.**

---

## 7. Sonraki Adimlar

Phase 1.5-C kapatildiktan sonra:
- **Phase 1.5-D:** Bridge implementasyonu (bu kontratin kod haline getirilmesi)
- **Phase 2:** Guvenlik / Politika Sertlestirme
- **Phase 3:** Konusma-Yurutme Urunlestirme
- **Phase 4:** Yeniden Uretebilirlik / Felaket Kurtarma
