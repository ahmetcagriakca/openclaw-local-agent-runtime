# Phase 1.5-E — Bridge Implementasyon Raporu

**Durum:** TAMAMLANDI
**Tarih:** 2026-03-23
**Kapsam:** Dondurulan kontrat ve guvenlik temel cizgisine gore Bridge implementasyonu

---

## 1. Ozet

Bu belge, Phase 1.5-E kapsaminda gerceklestirilen Bridge implementasyonunu raporlar. Bridge, dondurulan Phase 1.5-C kontratini ve Phase 1.5-D guvenlik temel cizgisini uygular.

| Alt-faz | Durum | Icerik |
|---------|-------|--------|
| Phase 1.5-A | KAPALI | Mimari kararlar |
| Phase 1.5-B | KAPALI | Kod/artifact temizligi |
| Phase 1.5-C | KAPALI | Bridge kontrati |
| Phase 1.5-D | KAPALI | Guvenlik temel cizgisi |
| Phase 1.5-E | TAMAMLANDI | Bridge implementasyonu (bu belge) |

---

## 2. Bridge Fiziksel Formu

**Secilen form:** Tekil-cagri durumsuz PowerShell betigi.

| Ozellik | Deger |
|---------|-------|
| Giris noktasi | `bridge/oc-bridge.ps1` |
| Cagri modeli | Her istek icin bir kez cagrilir, yanit uretir, cikar |
| Durum tutma | Yok — cagrilar arasi durum saklanmaz |
| Kalici sunucu | Yok — HTTP dinleyicisi yok |
| Parametre | `-RequestJson` (zorunlu JSON string) |
| Cikis kodu | 0 = basarili, 1 = ret/hata, 2 = baslangic hatasi |

**Neden bu form:** Phase 1.5 modeli yalnizca polling. OpenClaw her etkilesimi yonetir. Kalici sunucu gereksiz karmasiklik ekler. Betik formu, herhangi bir cagirandan (OpenClaw, Telegram bot, test araclarri) dogrudan calistiirilabilir.

---

## 3. Olusturulan / Degistirilen Dosyalar

| Dosya | Islem | Amac |
|-------|-------|------|
| `bridge/oc-bridge.ps1` | OLUSTURULDU | Bridge giris noktasi — dogrulama, haritalama, runtime cagrisi, denetim |
| `bridge/allowlist.json` | OLUSTURULDU | Yetkili kullanici listesi (`allowedUserIds` dizisi) |
| `bridge/test-bridge.ps1` | OLUSTURULDU | OpenClaw davranisini simule eden dogrulama araci |
| `bridge/logs/` | OLUSTURULDU | Denetim gunluk dizini (`bridge-audit.jsonl`) |
| `defs/tasks/create_note.json` | YENIDEN OLUSTURULDU | Uctan uca dogrulama icin gorev tanimi |

---

## 4. Uygulanan Dis Islemler

Phase 1.5-C'de dondurulan dort dis islem uygulanmistir:

### 4.1 submit_task

```
OpenClaw -> Bridge: submit_task istegi
Bridge: dogrulama (yapisal, allowlist, onay)
Bridge -> Runtime: oc-task-enqueue.ps1 -TaskName ... -InputBase64 ... -Source ...
Runtime -> Bridge: queued + taskId
Bridge -> OpenClaw: accepted + taskId + requestId
```

**Istek ornegi:**
```json
{
  "operation": "submit_task",
  "taskName": "create_note",
  "arguments": {"filename": "test.txt", "content": "merhaba"},
  "source": "telegram",
  "sourceUserId": "123456789",
  "requestId": "req-001",
  "approvalStatus": "preapproved"
}
```

**Basarili yanit:**
```json
{
  "status": "accepted",
  "taskId": "task-20260322-220155500-5222",
  "taskName": "create_note",
  "requestId": "req-001"
}
```

### 4.2 get_task_status

```
OpenClaw -> Bridge: get_task_status(taskId)
Bridge -> Runtime: oc-task-get.ps1 -TaskId ...
  [eger succeeded ise] Bridge -> Runtime: oc-task-output.ps1 -TaskId ...
Bridge -> OpenClaw: in_progress VEYA completed + sonuc
```

**Devam eden yanit:**
```json
{
  "status": "in_progress",
  "taskId": "task-...",
  "taskStatus": "running",
  "requestId": "req-002"
}
```

**Basarili terminal yanit:**
```json
{
  "status": "completed",
  "taskId": "task-...",
  "taskStatus": "succeeded",
  "requestId": "req-002",
  "result": {
    "summary": "Task completed successfully.",
    "outputPreview": "===== STEP 1 / write_file =====\nmerhaba"
  }
}
```

**Basarisiz terminal yanit:**
```json
{
  "status": "completed",
  "taskId": "task-...",
  "taskStatus": "failed",
  "requestId": "req-002",
  "failureReason": "Worker-level failure: runner exited with code 1"
}
```

**Iptal edilmis terminal yanit:**
```json
{
  "status": "completed",
  "taskId": "task-...",
  "taskStatus": "cancelled",
  "requestId": "req-002",
  "failureReason": "Cancelled by user before execution."
}
```

### 4.3 cancel_task

```
OpenClaw -> Bridge: cancel_task(taskId)
Bridge -> Runtime: oc-task-cancel.ps1 -TaskId ... -Source ...
Bridge -> OpenClaw: acknowledged VEYA rejected
```

**Kabul yaniti:**
```json
{
  "status": "acknowledged",
  "taskId": "task-...",
  "requestId": "req-003",
  "taskStatus": "cancel_requested"
}
```

### 4.4 get_health

```
OpenClaw -> Bridge: get_health
Bridge -> Runtime: oc-task-health.ps1
Bridge -> OpenClaw: temizlenmis saglik durumu
```

**Yanit:**
```json
{
  "status": "ok",
  "health": "ok",
  "requestId": "req-004"
}
```

Yalnizca `health` alani (`ok`/`degraded`/`error`) runtime'dan iletilir. Tum dahili detaylar (dosya yollari, worker durumu, kuyruk sayilari, zamanlanmis gorev durumlari vb.) cikarilir.

---

## 5. Uygulanan Dogrulama ve Guvenlik Kapilari

### 5.1 Baslangic: Fail-Closed Allowlist

Bridge, herhangi bir istegi islemeden once allowlist dosyasini yukler.

| Durum | Bridge davranisi | Cikis kodu |
|-------|-----------------|------------|
| Dosya yok | Baslamayi reddeder, stderr'e yazar | 2 |
| Dosya JSON degil | Baslamayi reddeder | 2 |
| Dosya bos (sifir giris) | Baslamayi reddeder | 2 |
| Dosya gecerli ve en az bir giris var | Normal baslar | — |

### 5.2 Bes Adimli Dogrulama Sirasi

Her istek su siradan gecer. Ilk hatada islem durur, runtime'a ulasilmaz.

```
Adim 1: Yapisal dogrulama
   -> operation, source, sourceUserId, requestId mevcut ve bos degil mi?
   -> Basarisiz: INVALID_INPUT

Adim 2: Islem dogrulamasi
   -> Bilinen dort islemden biri mi?
   -> Basarisiz: INVALID_INPUT

Adim 3: Allowlist uygulamasi
   -> sourceUserId yetkili listede mi?
   -> Basarisiz: SOURCE_NOT_ALLOWED

Adim 4: Islem-bazli alan dogrulamasi
   -> taskName formati, taskId formati, arguments tipi, approvalStatus degeri
   -> Basarisiz: INVALID_INPUT

Adim 5: Onay on-dogrulamasi
   -> approvalStatus = "pending" mi?
   -> Basarisiz: APPROVAL_REQUIRED
```

### 5.3 Allowlist Yapisi

```json
{
  "allowedUserIds": ["123456789", "987654321"]
}
```

- Duz `sourceUserId` listesi
- Phase 1.5'te gorev-bazli veya islem-bazli yetkilendirme yok
- Listede olan: dort dis islemin hepsine erisir
- Listede olmayan: hicbirine erisemez

---

## 6. Uygulanan Runtime Haritasi

### 6.1 Dis -> Ic Haritalama

| Dis islem | Runtime betigi | Parametre haritasi |
|-----------|---------------|-------------------|
| `submit_task` | `oc-task-enqueue.ps1` | `-TaskName` <- `taskName`, `-InputBase64` <- base64(arguments), `-Source` <- `source` |
| `get_task_status` (durum) | `oc-task-get.ps1` | `-TaskId` <- `taskId` |
| `get_task_status` (cikti) | `oc-task-output.ps1` | `-TaskId` <- `taskId` (yalnizca succeeded durumunda) |
| `cancel_task` | `oc-task-cancel.ps1` | `-TaskId` <- `taskId`, `-Source` <- `source` |
| `get_health` | `oc-task-health.ps1` | (parametre yok) |

### 6.2 Yasakli Betikler

Bridge asla su betikleri cagirmaz:

| Betik | Neden |
|-------|-------|
| `oc-run-action.ps1` | Ham eylem yuzeyi — yasak |
| `oc-run-file.ps1` | Ham dosya yurutme — yasak |
| `oc-task-retry.ps1` | Dis kontratta yok — yalnizca operator |
| `oc-task-repair.ps1` | Yalnizca operator |
| `oc-task-worker.ps1` | Runtime-dahili |
| `oc-runtime-watchdog.ps1` | Runtime-dahili |

### 6.3 Runtime Zaman Asimi

Tum runtime betik cagrilari 30 saniyelik zaman asimina tabidir. Zaman asimi durumunda:
- Calistirilan surecler sonlandirilir
- Dis yanit: `status: "error"`, `errorCode: "RUNTIME_UNAVAILABLE"`
- Denetim kaydinda `Timeout` olarak isaretlenir

### 6.4 Coklu-Cagri Terminal Yanit Montaji

`get_task_status` terminal durumda iki ardisik runtime cagrisi yapar:

1. `oc-task-get.ps1` -> gorev durumu ve metadata
2. `oc-task-output.ps1` -> adim cikti gunlukleri (yalnizca `succeeded` durumunda)

Ikinci cagri basarisiz olursa veya zaman asimina ugrarsa:
- `result.summary` yine mevcut ("Task completed successfully.")
- `result.outputPreview` cikarilir
- Yanit yine `completed` doner — basarisiz cikti alma terminal yaniti engellemez

---

## 7. Uygulanan Ret Haritasi

### 7.1 Bridge-Seviyesi Retler (runtime'dan once)

| Kosul | Dis errorCode | Yanit status |
|-------|---------------|-------------|
| Eksik/gecersiz zorunlu alanlar | `INVALID_INPUT` | `rejected` |
| Bilinmeyen islem | `INVALID_INPUT` | `rejected` |
| Yetkisiz sourceUserId | `SOURCE_NOT_ALLOWED` | `rejected` |
| approvalStatus = pending | `APPROVAL_REQUIRED` | `rejected` |

### 7.2 Runtime Ret Haritasi

| Runtime reasonCode | Dis errorCode | Yanit status |
|-------------------|---------------|-------------|
| `UNKNOWN_TASK` | `UNKNOWN_TASK` | `rejected` |
| `INVALID_TASK_INPUT` | `INVALID_INPUT` | `rejected` |
| `TASK_POLICY_DENIED` | `TASK_DISABLED` | `rejected` |
| `APPROVAL_REQUIRED` | `APPROVAL_REQUIRED` | `rejected` |
| `TASK_STATE_INVALID` (iptal icin) | `CANCEL_REJECTED` | `rejected` |
| `UNKNOWN_TASK` (iptal/durum icin) | `TASK_NOT_FOUND` | `rejected` |

### 7.3 Altyapi Hatalari

| Kosul | Dis errorCode | Yanit status |
|-------|---------------|-------------|
| Runtime zaman asimi | `RUNTIME_UNAVAILABLE` | `error` |
| Runtime beklenmeyen hata | `RUNTIME_UNAVAILABLE` | `error` |

---

## 8. Uygulanan Denetim Kaydi

### 8.1 Denetim Deposu

**Dosya:** `bridge/logs/bridge-audit.jsonl`

Yapisal JSON, istek basina bir satir. Yol, `$env:OC_BRIDGE_AUDIT_LOG` ortam degiskeniyle degistirilebilir.

### 8.2 Kaydedilen Alanlar

Her istek icin su alanlar kaydedilir:

| Alan | Kaynak | Aciklama |
|------|--------|----------|
| `ts` | Bridge | UTC ISO-8601 zaman damgasi |
| `requestId` | Dis istek | Istek kimlik bilgisi |
| `source` | Dis istek | Kaynak kanal |
| `sourceUserId` | Dis istek | Kullanici kimlik bilgisi |
| `operation` | Dis istek | Islem adi |
| `taskName` | Dis istek | Gorev adi (submit_task icin) |
| `approvalStatus` | Dis istek | Onay durumu (submit_task icin) |
| `outcome` | Bridge karari | `allowed`, `rejected`, `error` |
| `errorCode` | Bridge/runtime | Ret/hata kodu (ret durumunda) |
| `runtimeTaskId` | Runtime yaniti | Olusturulan/sorgulanan gorev kimlik bilgisi |
| `detail` | Bridge | Ek baglam bilgisi |

### 8.3 Ornek Denetim Kayitlari

**Basarili gorev gonderimi:**
```json
{"ts":"2026-03-22T22:01:55Z","requestId":"req-submit-1","source":"telegram","sourceUserId":"test-user-001","operation":"submit_task","taskName":"create_note","approvalStatus":"preapproved","outcome":"allowed","errorCode":"","runtimeTaskId":"task-20260322-220155500-5222","detail":""}
```

**Yetkisiz kullanici:**
```json
{"ts":"2026-03-22T21:57:41Z","requestId":"req-v3","source":"test","sourceUserId":"UNAUTHORIZED","operation":"get_health","taskName":"","approvalStatus":"","outcome":"rejected","errorCode":"SOURCE_NOT_ALLOWED","runtimeTaskId":"","detail":""}
```

---

## 9. Dogrulama Kaniti

### 9.1 Test Sonuclari

`test-bridge.ps1 -Suite all` ile 24 test caltirildi — **24/24 BASARILI**.

| Test Grubu | Sonuc | Detay |
|------------|-------|-------|
| Baslangic fail-closed (3 test) | 3/3 BASARILI | Eksik dosya -> exit 2, bos liste -> exit 2, bozuk JSON -> exit 2 |
| Dogrulama kapilari (7 test) | 7/7 BASARILI | Eksik alanlar, bilinmeyen islem, yetkisiz kullanici, pending onay, eksik taskId, gecersiz taskId, bozuk JSON |
| Gorev gonderimi (4 test) | 4/4 BASARILI | Basarili gonderim, taskId mevcut, requestId yankilandi, bilinmeyen gorev reddedildi |
| Polling (4 test) | 4/4 BASARILI | Terminal duruma ulasti, result mevcut, summary mevcut, failureReason yok |
| Iptal (2 test) | 2/2 BASARILI | Var olmayan gorev reddedildi, terminal gorev reddedildi |
| Saglik (4 test) | 4/4 BASARILI | status ok, health alani mevcut, requestId mevcut, dahili alan sizintisi yok |

### 9.2 Uctan Uca Dogrulama

```
1. submit_task("create_note", {filename: "bridge-test.txt", content: "Bridge Phase 1.5-E OK"})
   -> accepted, taskId alinidi

2. get_task_status(taskId) ile polling
   -> completed, taskStatus: succeeded
   -> result.outputPreview mevcut

3. Fiziksel dosya dogrulamasi
   -> results/bridge-test.txt icerigi: "Bridge Phase 1.5-E OK"
```

Uctan uca yol calisiyor: mesaj -> gorev -> yurutme -> dosya yazma -> sonuc dondurme.

### 9.3 Dogrulama Matrisi

| Kriter | Sonuc | Yontem |
|--------|-------|--------|
| Bridge allowlist olmadan baslamayi reddeder | **BASARILI** | 3 test (eksik/bos/bozuk dosya) |
| Yetkisiz sourceUserId runtime'dan once reddedilir | **BASARILI** | Test: `SOURCE_NOT_ALLOWED` |
| Pending approvalStatus runtime'dan once reddedilir | **BASARILI** | Test: `APPROVAL_REQUIRED` |
| Bozuk istek runtime'dan once reddedilir | **BASARILI** | 3 test (eksik alan, bilinmeyen islem, bozuk JSON) |
| Yalnizca dondurulan dis islemler cagrilabilir | **BASARILI** | Test: bilinmeyen islem reddedildi |
| Runtime betikleri dogrudan disa acik degil | **BASARILI** | Kod incelemesi: yalnizca `Invoke-RuntimeScript` kullaniir |
| Polling akisi calisiyor | **BASARILI** | submit -> poll -> completed dongusu |
| Terminal yanitlar dondurulan kontrata uyuyor | **BASARILI** | succeeded: result + summary, failed: failureReason |
| Cikti alma basarisizliginda belirleyici davranis | **BASARILI** | Kod incelemesi: outputPreview cikarilir, yanit yine completed doner |
| Dis saglik yaniti temizlenmis | **BASARILI** | 4 test: yalnizca health alani, dahili alan yok |
| Denetim alanlari kaydediliyor | **BASARILI** | 31 denetim satiri uretildi, tum 10 alan mevcut |

---

## 10. Bilinen Kisitlamalar

1. **Eksik gorev tanimlari:** `notepad_smoke.json`, `open_notepad.json`, `dead_letter_probe.json` diskten silinmis durumdaydi. Yalnizca `create_note.json` yeniden olusturuldu (uctan uca dogrulama icin yeterli). Digerleri bootstrap calistiirilarak olusturulabilir.

2. **Cikti alma basarisizligi testi:** Basarili ama ciktisi olmayan gorev senaryosu canli test yerine kod incelemesiyle dogrulandi. Kod yolu belirleyici: cikti sorgusu basarisiz olursa `outputPreview` cikarilir, yanit yine `completed` doner.

3. **Allowlist yalnizca test kullanicisi iceriyor:** `test-user-001` mevcut. Gercek Telegram kullanici kimlik bilgileri eklenmeli.

---

## 11. Sonraki Adimlar

| Adim | Amac | On kosul |
|------|------|----------|
| **Phase 1.5 Cikis Dogrulama** | ARCHITECTURE.md Phase 1.5 tanimina gore uctan uca dogrulama: mesaj -> gorev -> sonuc yolu calisiyor, allowlist uygulaniiyor, token politikasi kullaniliyor | Phase 1.5-E tamamlandi |
| **Phase 2** | Guvenlik / Politika Sertlestirme: gorev-bazli yetkilendirme, risk siniflandirmasi, dosya sistemi sinirlamasi | Phase 1.5 kapatildi |
| **Phase 3** | Konusma-Yurutme Urunlestirme | Phase 2 kapatildi |
| **Phase 4** | Yeniden Uretebilirlik / Felaket Kurtarma | Phase 3 kapatildi |
