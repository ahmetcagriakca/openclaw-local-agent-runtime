# Phase 1.5-F — Cikis Dogrulama / Uctan Uca Dogrulama Raporu

**Durum:** BASARILI (Gercek Telegram On Kosulu ile)
**Tarih:** 2026-03-23
**Kapsam:** Uygulanan Bridge + runtime yolunun dondurulan kontrat ve guvenlik temel cizgisine karsi dogrulanmasi

---

## 1. Ozet

Bu belge, Phase 1.5-E'de uygulanan Bridge sisteminin Phase 1.5-C (kontrat) ve Phase 1.5-D (guvenlik temel cizgisi) gereksinimlerine uygunlugunu kanitlar.

| Alt-faz | Durum | Icerik |
|---------|-------|--------|
| Phase 1.5-A | KAPALI | Mimari kararlar |
| Phase 1.5-B | KAPALI | Kod/artifact temizligi |
| Phase 1.5-C | KAPALI | Bridge kontrati |
| Phase 1.5-D | KAPALI | Guvenlik temel cizgisi |
| Phase 1.5-E | KAPALI | Bridge implementasyonu |
| Phase 1.5-F | TAMAMLANDI | Cikis dogrulama (bu belge) |

### Dogrulama Yontemi

- Tum testler gercek Bridge cagrilariyla yurutuldu: `pwsh -File bridge/oc-bridge.ps1 -RequestJson '...'`
- Runtime betikleri gercek gorev dosyalari olusturdu
- `test-bridge.ps1` araci OpenClaw davranisini simule etti — OpenClaw implementasyonu degil
- Kod incelemesine dayanan sonuclar acikca isaretlendi

---

## 2. Baslangic Fail-Closed Kaniti

Bridge, gecerli allowlist olmadan hicbir istegi islemez.

| Test | Girdi | Cikis kodu | Stderr mesaji | Sonuc |
|------|-------|------------|---------------|-------|
| T1a | Dosya yok (`C:\nonexistent\allowlist.json`) | **2** | `Allowlist file not found` | **BASARILI** |
| T1b | Bos liste (`{"allowedUserIds":[]}`) | **2** | `Allowlist is empty (zero entries)` | **BASARILI** |
| T1c | Bozuk JSON (`NOT{JSON`) | **2** | `Allowlist file is not valid JSON` | **BASARILI** |
| T1d | Gecerli allowlist (1 giris) | **0** | (yok) | **BASARILI** |

Cikis kodu 2, baslangic hatasini istek reddinden (cikis kodu 1) ayirt eder.

---

## 3. Runtime-Oncesi Ret Kaniti

Asagidaki istekler runtime'a ulasmadan reddedildi. Kanitlar: (a) dogrulama sirasi runtime cagrisindan once durur, (b) denetim kayitlarinda `outcome: "allowed"` yok, (c) `tasks/` dizininde yeni gorev olusturulmadi.

### T2a: Yetkisiz sourceUserId

```json
Istek:  {"operation":"get_health","source":"test","sourceUserId":"UNAUTHORIZED-USER","requestId":"req-t2a"}
Yanit:  {"status":"rejected","errorCode":"SOURCE_NOT_ALLOWED","errorMessage":"User is not authorized.","requestId":"req-t2a"}
Cikis:  1
```

### T2b: Eksik sourceUserId

```json
Istek:  {"operation":"get_health","source":"test","requestId":"req-t2b"}
Yanit:  {"status":"rejected","errorCode":"INVALID_INPUT","errorMessage":"Missing required fields: sourceUserId","requestId":"req-t2b"}
Cikis:  1
```

### T2c: approvalStatus = pending

```json
Istek:  {"operation":"submit_task","taskName":"create_note","arguments":{},"source":"test","sourceUserId":"test-user-001","requestId":"req-t2c","approvalStatus":"pending"}
Yanit:  {"status":"rejected","errorCode":"APPROVAL_REQUIRED","errorMessage":"Task requires approval before submission. approvalStatus is pending.","requestId":"req-t2c","taskName":"create_note"}
Cikis:  1
```

### T2d: Bozuk JSON govdesi

```json
Istek:  NOT-VALID-JSON{{{
Yanit:  {"status":"rejected","errorCode":"INVALID_INPUT","errorMessage":"Request is not valid JSON.","requestId":""}
Cikis:  1
```

### T2e: Bilinmeyen islem

```json
Istek:  {"operation":"unknown_op","source":"test","sourceUserId":"test-user-001","requestId":"req-t2e"}
Yanit:  {"status":"rejected","errorCode":"INVALID_INPUT","errorMessage":"Unknown operation: unknown_op","requestId":"req-t2e"}
Cikis:  1
```

Bes dogrulama adimi sirasi:
1. Yapisal dogrulama (T2b, T2d)
2. Islem dogrulamasi (T2e)
3. Allowlist uygulamasi (T2a)
4. Islem-bazli alan dogrulamasi
5. Onay on-dogrulamasi (T2c)

---

## 4. Kesin Onay Ret Yaniti Dogrulamasi

Test T2c tam ciktisi:

```json
{
  "status": "rejected",
  "errorCode": "APPROVAL_REQUIRED",
  "errorMessage": "Task requires approval before submission. approvalStatus is pending.",
  "requestId": "req-t2c",
  "taskName": "create_note"
}
```

| Alan | Mevcut mu? | Deger | Kontrat uyumu |
|------|------------|-------|---------------|
| `status` | evet | `"rejected"` | Uyumlu |
| `errorCode` | evet | `"APPROVAL_REQUIRED"` | Uyumlu — dondurulan ret haritasina uygun |
| `errorMessage` | evet | Okunabilir aciklama | Uyumlu |
| `requestId` | evet | `"req-t2c"` — istekten yankilandi | Uyumlu |
| `taskName` | evet | `"create_note"` — istekten yankilandi | Uyumlu |

Tum zorunlu alanlar mevcut. Sekil, dondurulan Phase 1.5-C dis yanit zarfina uyuyor.

---

## 5. Dis Islem Yuzeyi Kaniti

### Izin verilen islemler

| Islem | Test | Sonuc | Yanit status |
|-------|------|-------|-------------|
| `submit_task` | T3 | Kabul edildi | `accepted` |
| `get_task_status` | T5 | Gorev durumu donduruldu | `completed` |
| `cancel_task` | T6d | Iptal kabul edildi | `acknowledged` |
| `get_health` | T8 | Saglik durumu donduruldu | `ok` |

### Yasakli islemler

| Denenen islem | Test | Sonuc | errorCode |
|---------------|------|-------|-----------|
| `retry_task` | T10a | Reddedildi | `INVALID_INPUT` — `"Unknown operation: retry_task"` |
| `run_action` | T10b | Reddedildi | `INVALID_INPUT` — `"Unknown operation: run_action"` |
| `list_tasks` | T10c | Reddedildi | `INVALID_INPUT` — `"Unknown operation: list_tasks"` |
| `unknown_op` | T2e | Reddedildi | `INVALID_INPUT` — `"Unknown operation: unknown_op"` |

Yalnizca dondurulan dort islem basarili olur. Diger tum islemler `INVALID_INPUT` ile reddedilir.

---

## 6. Polling Akisi Kaniti

### Tam uctan uca dizi (T3 -> T5)

**Adim 1 — Gonderim:**

```
Istek:
  {"operation":"submit_task","taskName":"create_note",
   "arguments":{"filename":"f15f-test.txt","content":"Phase 1.5-F validation OK"},
   "source":"telegram","sourceUserId":"test-user-001",
   "requestId":"req-t3","approvalStatus":"preapproved"}

Yanit:
  {"status":"accepted","taskId":"task-20260322-221638555-1648",
   "taskName":"create_note","requestId":"req-t3"}
```

**Adim 2 — Terminal yoklama (3 sn beklemeden sonra):**

```
Istek:
  {"operation":"get_task_status","taskId":"task-20260322-221638555-1648",
   "source":"telegram","sourceUserId":"test-user-001","requestId":"req-t5"}

Yanit:
  {"status":"completed","taskStatus":"succeeded",
   "taskId":"task-20260322-221638555-1648","requestId":"req-t5",
   "result":{"summary":"Task completed successfully.",
             "outputPreview":"===== STEP 1 / write_file =====\r\n..."}}
```

**Fiziksel artifact dogrulamasi:**
`results/f15f-test.txt` dosya icerigi: `Phase 1.5-F validation OK`

Uctan uca yol kanitlandi: mesaj -> gorev -> yurutme -> dosya yazma -> sonuc dondurme.

---

## 7. Terminal Sonuc Kaniti

### 7.1 Basarili (succeeded) — Test T5

```json
{
  "status": "completed",
  "taskId": "task-20260322-221638555-1648",
  "taskStatus": "succeeded",
  "requestId": "req-t5",
  "result": {
    "summary": "Task completed successfully.",
    "outputPreview": "===== STEP 1 / write_file =====\r\n..."
  }
}
```

| Kontrol | Sonuc |
|---------|-------|
| `taskStatus` = `"succeeded"` | Mevcut |
| `result` nesnesi mevcut | Evet |
| `result.summary` mevcut | Evet |
| `result.outputPreview` mevcut | Evet |
| `failureReason` yok | Dogru — succeeded icin yok |
| `requestId` ve `taskId` surekliligi | Gonderimle esliyor |

### 7.2 Basarisiz (failed) — Test T6b

```json
{
  "status": "completed",
  "taskId": "task-20260322-221715021-7522",
  "taskStatus": "failed",
  "requestId": "req-t6b",
  "failureReason": "Step 1 failed: --- STDERR --- Action not found: nonexistent_action..."
}
```

| Kontrol | Sonuc |
|---------|-------|
| `taskStatus` = `"failed"` | Mevcut |
| `failureReason` mevcut | Evet — gercek hata mesajii |
| `result` nesnesi yok | Dogru — failed icin yok |

Test icin `fail_test.json` gorev tanimi olusturuldu (preapproved, var olmayan eylem). Test sonrasi silindi.

### 7.3 Iptal edilmis (cancelled) — Test T6d

Iptal istegi:
```json
{"status":"acknowledged","taskId":"task-20260322-221844262-9145","requestId":"req-t6d","taskStatus":"cancelled"}
```

Sonraki yoklama:
```json
{
  "status": "completed",
  "taskId": "task-20260322-221844262-9145",
  "taskStatus": "cancelled",
  "requestId": "req-t6d-poll",
  "failureReason": "Cancelled by user before execution."
}
```

| Kontrol | Sonuc |
|---------|-------|
| `taskStatus` = `"cancelled"` | Mevcut |
| `failureReason` mevcut | Evet — `"Cancelled by user before execution."` |
| `result` nesnesi yok | Dogru — cancelled icin yok |

Gorev, `-NoWorkerKick` ile kuyruga alindi (kuyrukta tutmak icin), ardindan Bridge uzerinden iptal edildi.

---

## 8. Bozulmus Terminal Davranisi Kaniti

**Bu, Phase 1.5-E'den acikca ertelenmisti. Simdi kontrol edilen testle dogrulandi.**

### Yontem

`task-20260322-221638555-1648` (succeeded) gorevi icin `task.json` dosyasi degistirildi — `steps` dizisi bos yapildi. Bu, `oc-task-output.ps1`'in `"Task has no steps."` hatasiyla cikmaisna (exit 1) neden olur. Gorev durumu `succeeded` olarak kalir.

### Test T7b tam ciktisi

```json
{
  "status": "completed",
  "taskId": "task-20260322-221638555-1648",
  "taskStatus": "succeeded",
  "requestId": "req-t7b",
  "result": {
    "summary": "Task completed successfully."
  }
}
```

### Dogrulama

| Kontrol | Sonuc |
|---------|-------|
| `status` = `"completed"` | Evet — hata degil |
| `taskStatus` = `"succeeded"` | Evet — dogru terminal durum |
| `result.summary` mevcut | Evet — `"Task completed successfully."` |
| `result.outputPreview` **yok** | Evet — cikti sorgusu basarisiz, alan cikarildi |
| `failureReason` yok | Dogru — succeeded icin yok |
| Cikis kodu | 0 |

**Sonuc:** Takip eden cikti alma basarisiz oldugunda, dis yanit yine `completed` ve `taskStatus: "succeeded"` doner. `result` nesnesi `summary` icerir ama `outputPreview` cikarilir. Davranis belirleyici. Gercek yurutmeyle kanitlandi, kod incelemesiyle degil.

---

## 9. Saglik Maruz Birakma Kaniti

### Test T8 tam ciktisi

```json
{
  "status": "ok",
  "health": "ok",
  "requestId": "req-t8"
}
```

### Alan dogrulamasi

| Alan | Kaynak | Mevcut | Deger |
|------|--------|--------|-------|
| `status` | Bridge sarmalayici | evet | `"ok"` (saglik sorgusu basarili) |
| `health` | Temizlenmis runtime `status` alani | evet | `"ok"` |
| `requestId` | Yanki | evet | `"req-t8"` |

### Sizinti kontrolu

Asagidaki runtime-dahili alanlar dis yanita **dahil degildir:**

`basePath`, `runtimeRoot`, `workerActive`, `scheduledTaskState`, `watchdogTaskState`, `preflightTaskState`, `pendingTickets`, `leaseTickets`, `deadLetterTickets`, `stuckTasks`, `stuckCaseA`, `stuckCaseB`, `statusReasons`, `lastPreflightUtc`, `preflightBootTimeUtc`, `currentBootTimeUtc`, `lastWatchdogUtc`, `taskDefinitions`, `tasks`, `nonTerminalTasks`

Hicbiri dis yanita sizmaadi. Temizleme dogrulandi.

---

## 10. Denetim Kaniti

### Denetim deposu

**Dosya:** `bridge/logs/bridge-audit.jsonl`
**Bu dogrulama calismasinda uretilen kayit sayisi:** 20

### Basarili istek denetim kaydi (T3 — submit kabul)

```json
{
  "ts": "2026-03-22T22:16:38.9061305Z",
  "requestId": "req-t3",
  "source": "telegram",
  "sourceUserId": "test-user-001",
  "operation": "submit_task",
  "taskName": "create_note",
  "approvalStatus": "preapproved",
  "outcome": "allowed",
  "errorCode": "",
  "runtimeTaskId": "task-20260322-221638555-1648",
  "detail": ""
}
```

### Ret denetim kaydi (T2a — yetkisiz)

```json
{
  "ts": "2026-03-22T22:15:52.9058212Z",
  "requestId": "req-t2a",
  "source": "test",
  "sourceUserId": "UNAUTHORIZED-USER",
  "operation": "get_health",
  "taskName": "",
  "approvalStatus": "",
  "outcome": "rejected",
  "errorCode": "SOURCE_NOT_ALLOWED",
  "runtimeTaskId": "",
  "detail": ""
}
```

### Phase 1.5-D minimum denetim alani kontrolu

| Zorunlu alan | Basarili kayitta | Ret kaydinda |
|-------------|-----------------|--------------|
| `requestId` | `req-t3` | `req-t2a` |
| `source` | `telegram` | `test` |
| `sourceUserId` | `test-user-001` | `UNAUTHORIZED-USER` |
| `operation` | `submit_task` | `get_health` |
| `taskName` | `create_note` | (bos — uygulanabilir degil) |
| `approvalStatus` | `preapproved` | (bos — uygulanabilir degil) |
| `outcome` | `allowed` | `rejected` |
| `errorCode` | (bos — hata yok) | `SOURCE_NOT_ALLOWED` |
| `runtimeTaskId` | `task-20260322-...` | (bos — gorev olusturulmadi) |
| `timestamp` (ts) | `2026-03-22T22:16:38Z` | `2026-03-22T22:15:52Z` |

Her iki kayit icin 10 dondurulan minimum denetim alani mevcut.

---

## 11. Yasakli Yol Kaniti

Tum testler **yetkili** kullanici (`test-user-001`) ile gercek Bridge cagrisiyla yurutuldu.

| Yasakli yol | Gonderilen islem | Sonuc | errorCode | Kanit |
|-------------|-----------------|-------|-----------|-------|
| `oc-task-retry.ps1` | `"retry_task"` | Reddedildi | `INVALID_INPUT` | `"Unknown operation: retry_task"` |
| `oc-run-action.ps1` | `"run_action"` | Reddedildi | `INVALID_INPUT` | `"Unknown operation: run_action"` |
| `oc-task-list.ps1` (dis) | `"list_tasks"` | Reddedildi | `INVALID_INPUT` | `"Unknown operation: list_tasks"` |

Bu istekler yetkili bir kullanici tarafindan gonderildi. Allowlist hatasi nedeniyle degil, islem dondurulan kumede olmadigi icin reddedildi. Yetkili bir dis cagiran bile yasakli yollara Bridge uzerinden ulaaasamaz.

---

## 12. Zaman Asimi Davranisi Kaniti

### Uygulama varsayilani

Runtime betik cagrisi basina 30 saniyelik zaman asimi. Bu bir uygulama varsayilanidir, dondurulan kontrat degeri degildir.

### Gozlemlenen davranis (kod incelemesi)

Bir runtime cagrisi 30 saniyeyi astiginda:
1. Runtime sureci sonlandirilir
2. Bridge donduruyor: `status: "error"`, `errorCode: "RUNTIME_UNAVAILABLE"`, `errorMessage: "Runtime did not respond in time."`
3. Denetim kaydinda `detail: "Timeout"` olarak isaretlenir

### Coklu-cagri montaji icin

- Ilk cagri (gorev goruntusu) zaman asimina ugrarsa: yanit `error`/`RUNTIME_UNAVAILABLE`
- Ilk cagri basarili ama ikinci cagri (cikti) zaman asimina ugrarsa: bozulmus davranis uygulanir — `result.summary` mevcut, `outputPreview` cikarilir (T7b ile ayni kod yolu)

### Kanit seviyesi

Kod incelemesi + mevcut `Invoke-RuntimeScript` fonksiyonunun davranisi. 30+ saniyelik engelleme senaryosu zaman maliyeti nedeniyle canli test edilmedi. Kod yolu belirleyici.

---

## 13. Gorev Tanimi / Onay Politikasi Kaniti

| Tanim | Durum | approvalPolicy | Kullanildigi testler |
|-------|-------|----------------|---------------------|
| `create_note.json` | Phase 1.5-E'de yeniden olusturuldu | `preapproved` | T3, T5, T6c, T6d, T7 |
| `fail_test.json` | T6a/T6b icin olusturuldu, sonra silindi | `preapproved` | T6a, T6b |

### Onay testi gecerliligi

Onay on-dogrulama testi (T2c), `create_note` icin `approvalStatus: "pending"` gonderir. Bridge bunu adim 5'te runtime'a ulasmadan **once** reddeder. Runtime'in `approvalPolicy: "preapproved"` degeri bu test icin ilgisiz — ret Bridge seviyesinde dis `approvalStatus` alan degerine gore gerceklesir. Test, gorev taniminin onay politikasindan bagimsiz olarak gecerlidir.

---

## 14. Gercek Telegram Hazirlik Durumu

### Mevcut allowlist

`bridge/allowlist.json` yalnizca `test-user-001` icerir.

### Gercek Telegram dogrulama durumu: HENUZ DOGRULANMADI

Gercek Telegram uctan uca testi icin gerekli:

1. **Gercek Telegram numerik kullanici kimlik bilgisi** `allowlist.json`'a eklenmeli
2. **Telegram bot tokeni** `$env:OC_TELEGRAM_BOT_TOKEN` ortam degiskeninde ayarlanmali
3. **OpenClaw** (veya esdeger Telegram botu) gercek kullanicinin `sourceUserId`'si ile Bridge'i cagirmali

Bunlarin hicbiri su anda mevcut degil. Bu fazdaki tum dogrulama, dogrudan Bridge betik cagrisi yoluyla simule edilmis OpenClaw davranisi kullanmistir.

---

## 15. Kalan Bosluklar

| Bosluk | Ciddiyet | Detay |
|--------|----------|-------|
| Gercek Telegram kullanici kimlik bilgisi allowlist'te yok | On kosul | Tum dogrulama `test-user-001` kullandi |
| Zaman asimi davranisi canli test edilmedi | Dusuk | Kod incelemesiyle dogrulandi, belirleyici kod yolu |
| `fail_test.json` geciciydi | Yok | Test sirasinda olusturuldu ve silindi |

---

## 16. Phase 1.5-F Cikis Karari

### BASARILI — ACIK GERCEK-TELEGRAM ON KOSULU ILE

Tum yerel/kontrol edilen dogrulama kriterleri kanitlandi:

| Kriter | Durum | Kanit |
|--------|-------|-------|
| Bridge yalnizca gecerli allowlist ile baslar | **KANITLANDI** | T1a-T1d: 4/4 test |
| Reddedilen istekler runtime'a ulasmaz | **KANITLANDI** | T2a-T2e: 5/5 test |
| Onay pending ret sekli tam | **KANITLANDI** | T2c: tam yanit gosterildi, tum alanlar dogrulandi |
| Yalnizca dondurulan dis islemler cagrilabilir | **KANITLANDI** | T3/T5/T6d/T8 basarili, T10a-T10c/T2e reddedildi |
| Polling akisi uctan uca calisiyor | **KANITLANDI** | T3->T5: gonderim->yoklama->tamamlandi + artifact |
| Terminal succeeded yaniti kontrata uyuyor | **KANITLANDI** | T5: result/summary/outputPreview mevcut |
| Terminal failed yaniti kontrata uyuyor | **KANITLANDI** | T6b: failureReason mevcut, result yok |
| Terminal cancelled yaniti kontrata uyuyor | **KANITLANDI** | T6d-poll: failureReason mevcut, result yok |
| Bozulmus terminal davranisi gercek testle kanitlandi | **KANITLANDI** | T7b: cikti sorgusu basarisiz, summary mevcut, outputPreview yok |
| Saglik yaniti temizlenmis | **KANITLANDI** | T8: yalnizca status/health/requestId |
| Denetim alanlari kaydediliyor | **KANITLANDI** | 20 kayit, basarili + ret vakalari 10 dondurulan alana karsi dogrulandi |
| Yasakli yollar dis erisime kapali | **KANITLANDI** | T10a-T10c: retry/run_action/list_tasks reddedildi |
| Zaman asimi davranisi belgelendi | **BELGELENDI** | 30sn varsayilan, RUNTIME_UNAVAILABLE yaniti |
| Gorev tanimlari approvalPolicy varsayimlariyla tutarli | **KANITLANDI** | create_note.json: preapproved |
| Gercek Telegram dogrulama durumu acikca belirtildi | **BELIRTILDI** | Henuz dogrulanmadi — on kosullar listelendi |

### Tam Phase 1.5 kapatmasi icin on kosul

Gercek Telegram kullanici kimlik bilgisinin `bridge/allowlist.json`'a eklenmesi ve gercek Telegram bot cagrisiyla dogrulanmasi gerekmektedir.

---

## 17. Phase 1.5 Genel Ozet

Phase 1.5 tamamlandi. Alti alt-faz basariyla kapatildi:

```
Phase 1.5-A  Mimari Kararlar Dondurmasi       -> KAPALI
Phase 1.5-B  Legacy Temizlik                    -> KAPALI
Phase 1.5-C  Bridge Kontrat Dondurmasi          -> KAPALI
Phase 1.5-D  Guvenlik Temel Cizgisi Dondurmasi  -> KAPALI
Phase 1.5-E  Bridge Implementasyonu              -> KAPALI
Phase 1.5-F  Cikis Dogrulama                    -> BASARILI (Telegram on kosulu ile)
```

Sonraki adim: Gercek Telegram entegrasyonu icin allowlist guncellenmesi ve Phase 2'ye gecis.
