# Phase 1.5-D — Minimum Security Baseline Freeze Raporu

**Durum:** FROZEN
**Tarih:** 2026-03-23
**Kapsam:** Bridge implementasyonu oncesi minimum guvenlik temel cizgisi

---

## 1. Ozet

Bu belge, Phase 1.5-E (Bridge implementasyonu) oncesinde uygulanmasi zorunlu olan minimum guvenlik temel cizgisini dondurur. Tam guvenlik sertlestirmesi degil, implementasyona baslamak icin yeterli en kucuk guven sinirini tanimlar.

| Alt-faz | Durum | Icerik |
|---------|-------|--------|
| Phase 1.5-A | KAPALI | Mimari kararlar |
| Phase 1.5-B | KAPALI | Kod/artifact temizligi |
| Phase 1.5-C | KAPALI | Bridge kontrati |
| Phase 1.5-D | DONDURULDU | Guvenlik temel cizgisi (bu belge) |

---

## 2. Kaynak Dogrulama Temel Cizgisi

### 2.1 Her Dis Istekte Zorunlu Alanlar

Her dis istek Bridge'e ulastiginda, runtime'a herhangi bir cagri yapilmadan once asagidaki alanlar dogrulanir:

| Alan | Zorunlu | Dogrulama kurali | Ret kodu |
|------|---------|-------------------|----------|
| `operation` | evet | `submit_task`, `get_task_status`, `cancel_task`, `get_health` degerlerinden biri | `INVALID_INPUT` |
| `source` | evet | Bos olmayan string | `INVALID_INPUT` |
| `sourceUserId` | evet | Bos olmayan string | `INVALID_INPUT` |
| `requestId` | evet | Bos olmayan string | `INVALID_INPUT` |

### 2.2 Islem-Bazli Alan Dogrulamasi

| Alan | Hangi islemlerde zorunlu | Dogrulama kurali | Ret kodu |
|------|--------------------------|-------------------|----------|
| `taskName` | `submit_task` | Bos degil, `^[A-Za-z0-9_-]+$`, maks 128 karakter | `INVALID_INPUT` |
| `arguments` | `submit_task` | JSON nesnesi olmali (`{}` olabilir). Null, dizi, skaler olamaz. | `INVALID_INPUT` |
| `taskId` | `get_task_status`, `cancel_task` | Bos degil, `^task-[0-9]{8}-[0-9]{9}-[0-9]{4}$` | `INVALID_INPUT` |
| `approvalStatus` | `submit_task` | `"approved"`, `"preapproved"` veya `"pending"` degerlerinden biri | `INVALID_INPUT` |

### 2.3 Dogrulama Sirasi

Bridge dogrulamayi su sirada yapar. Ilk hatada islem durur, runtime'a ulasilmaz.

```
1. Yapisal dogrulama (JSON ayristirilabilir, zorunlu alanlar mevcut ve bos degil)
2. Islem dogrulamasi (bilinen islem mi?)
3. Allowlist uygulamasi (sourceUserId yetkili mi?)
4. Islem-bazli alan dogrulamasi (taskName, taskId, arguments seklinde)
5. Onay on-dogrulamasi (approvalStatus kontrolu)
6. Runtime cagrisi (yalnizca 1-5 basarili ise)
```

**Temel kural:** Adim 1-5'te herhangi birinde basarisizlik olursa, runtime'a hicbir cagri yapilmaz.

---

## 3. Allowlist Uygulama Siniri

### 3.1 Uygulama Yeri

Allowlist uygulamasi **Bridge'de** yapilir, herhangi bir runtime cagrisindan once. Runtime allowlist kontrolu yapmaz. Yetkisiz istek runtime'a ulasamaz.

### 3.2 Uygulama Anahtari

Allowlist `sourceUserId` uzerinden calisir. Bu, kaynak kanal icindeki kullanici kimligi bilgisidir (ornegin Telegram numerik kullanici kimlik bilgisi).

### 3.3 Allowlist Formati (Phase 1.5)

Duz bir `sourceUserId` listesi. Phase 1.5'te gorev-bazli, islem-bazli veya kaynak-bazli ayrintili yetkilendirme yok. Listede olan kullanici dort dis islemin hepsine erisebilir. Olmayan hicbirine erisemez.

### 3.4 Uygulama Kurallari

| Durum | Bridge davranisi | Dis yanit |
|-------|-----------------|-----------|
| `sourceUserId` eksik veya bos | Hemen reddet. Runtime'a ulasma. | `errorCode: "INVALID_INPUT"` |
| `sourceUserId` mevcut ama allowlist'te yok | Hemen reddet. Runtime'a ulasma. | `errorCode: "SOURCE_NOT_ALLOWED"` |
| `sourceUserId` mevcut ve allowlist'te var | Siradaki dogrulama adimina gec | (ret yok) |

### 3.5 Allowlist Depolama

- Allowlist, Bridge kaynak kodunda sabit-kodlanmis **olamaz**
- Konfigrasyon dosyasi veya ortam degiskeni olarak saklanmali
- Kod degisikligi olmadan guncellenebilmeli
- Bos allowlist = tum istekler reddedilir
- Allowlist dosyasi eksik veya ayristirilamaz = Bridge baslamayi reddetmeli veya tum istekleri reddetmeli

### 3.6 Allowlist Zorunludur

Bridge'in allowlist uygulamasinin devre disi birakildigi bir mod **yoktur**. "Acik mod" yoktur.

---

## 4. Onay On-Dogrulama Kurali

### 4.1 Dondurulan Karar

`approvalStatus` degeri `"pending"` ise, Bridge istegi runtime'a ulasmadan **reddetmelidir**.

Bu kesin bir kuraldir, "olabilir" degil.

### 4.2 Gerekcesi

Phase 1.5-C duzeltilmis onay modelinde belirlendi: runtime yalnizca gorev tanimi seviyesinde `preapproved` gorevleri kabul eder. Runtime'a `pending` durumunda bir istek iletmenin iki olasi sonucu var:
- Gorev preapproved degilse: runtime zaten reddeder (gereksiz cagri)
- Gorev preapproved ise: runtime sessizce yurutur, ama denetim kaydinda "pending" yazar (celiskili iz)

Her iki durum da kabul edilemez. Bridge bu durumu temiz bir sekilde engeller.

### 4.3 On-Dogrulama Kurallari

| `approvalStatus` degeri | Bridge davranisi |
|--------------------------|-----------------|
| `"approved"` | Devam et. Bridge degeri kaydeder. Runtime tanim-seviyesi onay uygular. |
| `"preapproved"` | Devam et. Bridge degeri kaydeder. Runtime tanim-seviyesi onay uygular. |
| `"pending"` | **Hemen reddet. Runtime'a ulasma.** |
| Baska deger / eksik | **Hemen reddet.** `INVALID_INPUT`. |

### 4.4 Pending Icin Ret Yaniti

```json
{
  "status": "rejected",
  "taskName": "create_note",
  "requestId": "req-20260323-001",
  "errorCode": "APPROVAL_REQUIRED",
  "errorMessage": "Task requires approval before submission. approvalStatus is pending."
}
```

### 4.5 Bridge Ne Yapmaz

- Bridge kullanicidan onay **istemez**
- Bridge gorev icin onay gerekip gerekmedigine **karar vermez**
- Bridge `approvalStatus` degerini **degistirmez**
- Bridge onay durumunu runtime'a **iletmez** (Phase 1.5-C'de donduruldu)

---

## 5. Operator Istisna Siniri

### 5.1 Tanimlama

Operator istisnasi, bakim ve kurtarma amaciyla yerel makinede dogrudan calistiirlabilen runtime betikleri kumeisidir. Bridge dis kontratinin parcasi degildir.

### 5.2 Dondurulan Ozellikler

| Ozellik | Deger |
|---------|-------|
| **Yerel mi uzak mi** | Yalnizca yerel. Operator, oc runtime'in calistigi makineye dogrudan erisime sahip olmali. |
| **Manuel mi otomatik mi** | Yalnizca manuel. Operator, betikleri yerel kabuktan etkilesimli olarak calistirir. |
| **Yalnizca yonetici mi** | Evet. Operator, oc runtime dizinine OS-seviyesi erisim ve PowerShell betik calistirma iznine sahip olmali. |
| **Bridge dis kontratinin parcasi mi** | Hayir. Bridge, operator islemlerini acmaz, vekalet etmez veya iletmez. |
| **Allowlist'i atlar mi** | Evet, dogasi geregi. Operator erisimi yerel, Bridge uzerinden degil. Operator kimligi OS-seviyesi kimlik dogrulamayla belirlenir. |

### 5.3 Yalnizca Operator Betikleri

| Betik | Amac |
|-------|------|
| `oc-task-retry.ps1` | Basarisiz gorevi yeniden deneme |
| `oc-task-repair.ps1` | Sikismis gorev/lease onarimi |
| `oc-run-action.ps1` | Ham eylem calistirma (yonetim istisnasi) |
| `oc-run-file.ps1` | Ham dosya calistirma (yonetim istisnasi) |
| `oc-task-list.ps1` | Gorev listeleme (Bridge dahili teshis icin kullanabilir, disa acamaz) |

### 5.4 Golge-Yol-Karsi Kural

Operator istisnasi bir golge entegrasyon yoluna **donusmemelidir**:

- Hicbir HTTP/API ucu noktasi operator betiklerini acamaz
- Hicbir Bridge rotasi operator betiklerine vekalet edemez
- Hicbir zamanlanmis gorev veya otomatik tetikleyici, dis cagiran adina operator betiklerini calistiiramaz
- Operator islevselliginin disa acilmasi gerekirse, yeni bir kontrat dondurmasi sureci gerektirir

---

## 6. Yasakli Dis Yollar

### 6.1 Yasakli Yol Kumesi

| Yasakli yol | Neden | Uygulama |
|-------------|-------|----------|
| Ham eylem cagrisi (`oc-run-action.ps1`) | Dis yuzey gorev-merkezli, eylem-merkezli degil | Bridge asla cagirmamali |
| Ham dosya yurutme (`oc-run-file.ps1`) | Ayni | Bridge asla cagirmamali |
| Dis cagiranlarin dogrudan runtime betiklerine erisimi | Dis cagiran Bridge kontrati uzerinden gecmeli | Bridge tek dis giris noktasi |
| WMCP ham tasima (`wmcp-call.ps1`) | Yalnizca dahili runtime tasimasi, rastgele PowerShell komutlari kabul eder | Hicbir dis cagirana acilmamali |
| Dis kontrat uzerinden retry | Phase 1.5-C karari: retry yalnizca operator | Bridge `oc-task-retry.ps1` cagirmamali |
| Dogrulama adimlarini atlayan Bridge rotasi | Tum dis istekler adim 1-5 dogrulamasindan gecmeli | Phase 1.5'te dogrulamayi atlayan hizli-yol veya hata-ayiklama-modu yok |

### 6.2 Uygulama Prensibi

Yasakli yollar, Bridge'in onlara **rota yazmamasi** ile uygulanir. Runtime tarafinda "bu betik Bridge tarafindan cagrilamaz" seklinde bir uygulama yoktur — uygulama, Bridge'in yalnizca Phase 1.5-C'de dondurulan alti izin verilen dahili betigi cagirmasi ve baska bir sey cagirmamasidir.

---

## 7. Gizli Bilgi Yonetimi Temel Cizgisi

### 7.1 Phase 1.5 Minimum Kurallari

| Kural | Durum | Detay |
|-------|-------|-------|
| **Kaynak kodunda sabit-kodlanmis gizli bilgi: yasak** | Zorunlu | Telegram bot tokeni, API anahtari veya kimlik bilgisi kaynak kodda duz metin olamaz |
| **Repo'ya eklenmis konfig dosyasinda gizli bilgi: yasak** | Zorunlu | Gizli bilgi iceren dosyalar surum kontrolunden haric tutulmali |
| **Ortam degiskeni birincil gizli bilgi kaynagi: zorunlu** | Zorunlu | Bridge, Telegram bot tokenini ve kimlik bilgilerini ortam degiskenlerinden okumalii |
| **Konfig dosyasi yedek kaynak: izinli (kisitli)** | Izinli | Repo disinda yerel konfig dosyasi yedek kaynak olabilir. Eklenmemeli. Herkese acik izinleri olmamali. |
| **Localhost-only varsayilan kimlik bilgisi: acikca gecici** | Tolere edilen | `wmcp-call.ps1` localhost icin `local-mcp-12345` kullanir. Bu bilinen gecici zayiflik. Localhost-disinda yol oldugunda degistirilmeli. |

### 7.2 Minimum Gizli Bilgi Envanteri

Bridge implementasyonu en az su gizli bilgileri yonetmeli:

| Gizli bilgi | Kaynak | Yedek |
|-------------|--------|-------|
| Telegram bot tokeni | `$env:OC_TELEGRAM_BOT_TOKEN` veya esdeger | Yok. Eksikse Bridge baslamayi reddetmeli. |
| Allowlist | Konfig dosyasi veya ortam degiskeni | Yok. Eksikse Bridge baslamayi reddetmeli veya tum istekleri reddetmeli. |

### 7.3 Phase 1.5'te Gerekli Olmayan

- Sifrelenmis gizli bilgi depolama (vault, DPAPI vb.)
- Otomatik gizli bilgi rotasyonu
- Gizli bilgi erisim denetimi
- Coklu-ortam gizli bilgi yonetimi

Bunlar Phase 2+ sertlestirme konulari.

---

## 8. Minimum Denetim Alani Kumesi

### 8.1 Zorunlu Denetim Kaydi Alanlari

Bridge tarafindan islenen her dis istek icin en az su alanlari iceren bir denetim kaydi uretilmelidir:

| Alan | Kaynak | Kaydeden katman |
|------|--------|-----------------|
| `requestId` | Dis istek | Bridge |
| `source` | Dis istek | Bridge |
| `sourceUserId` | Dis istek | Bridge |
| `operation` | Dis istek | Bridge |
| `taskName` | Dis istek (yalnizca submit_task) | Bridge |
| `approvalStatus` | Dis istek (yalnizca submit_task) | Bridge |
| `outcome` | Bridge karari: `allowed`, `rejected`, `error` | Bridge |
| `errorCode` | Bridge/runtime ret kodu (ret durumunda) | Bridge |
| `runtimeTaskId` | Runtime yaniti (gorev olusturuldugunda) | Bridge |
| `timestamp` | UTC ISO-8601 | Bridge |

### 8.2 Operator Yolu Denetimi

Yalnizca-operator cagrilari (yerel CLI), runtime tarafindan `control-plane.log` ve `worker.log` icinde kaydedilir. Bridge, operator eylemlerini denetlemez (gorunurlugu yoktur). Phase 1.5 icin kabul edilir.

### 8.3 Denetim Kaydi Formati

Phase 1.5, belirli bir denetim kaydi formati dondurmez (JSON, yapilandirilmis gunluk, veritabani satiri). Kisitlama: yukaridaki alanlar, olay sonrasinda Bridge gunluklerinden veya kayitlarindan kurtarilabilir olmalidir. Istek basina yapilandirilmis JSON gunluk satiri yeterlidir.

---

## 9. Saglik Ucu Noktasi Maruz Birakma Kurali

### 9.1 Dis Gorunurluk

`get_health`, normal Bridge kontrati uzerinden disa acik cagirilabilir. Phase 1.5-C'de dondurulan dort dis islemden biridir.

### 9.2 Erisim Kisitlamasi

`get_health`, diger tum islemlerle ayni allowlist uygulamasina tabidir. Yetkisiz `sourceUserId`, `get_health` cagiraamaz. Phase 1.5'te anonim saglik ucu noktasi yoktur.

### 9.3 Temizleme Kurali

Bridge, runtime saglik yanitini disa dondurmeden once temizlemelidir. Runtime'in `oc-task-health.ps1` betigi dahili alanlarla dolu ayrintili bir JSON nesnesi dondurur.

**Disa acilmasi guvenli:**

| Alan | Dis ad | Kaynak |
|------|--------|--------|
| Runtime saglik seviyesi | `health` | Runtime `status` alani (`"ok"`, `"degraded"`, `"error"`) |

**Disa acilmamasi gereken:**

- `basePath`, `runtimeRoot` (dosya sistemi yollari)
- `workerActive` (dahili mutex durumu)
- `scheduledTaskState`, `watchdogTaskState`, `preflightTaskState` (zamanlanmis gorev detayi)
- `pendingTickets`, `leaseTickets`, `deadLetterTickets` (kuyruk dahili bilgileri)
- `stuckTasks`, `stuckCaseA`, `stuckCaseB` (dahili kurtarma durumu)
- `statusReasons` (dahili yapiyi ifsa edebilir)
- `lastPreflightUtc`, `preflightBootTimeUtc`, `currentBootTimeUtc`, `lastWatchdogUtc` (dahili zamanlama)
- `taskDefinitions`, `tasks`, `nonTerminalTasks` sayilari (dahili kapasite detayi)

### 9.4 Dondurulan Dis Saglik Yaniti

```json
{
  "status": "ok",
  "health": "ok",
  "requestId": "req-20260323-004"
}
```

Yalnizca `health` (ok/degraded/error) iletilir. Geri kalan her sey cikarilir.

---

## 10. Acikca Ertelenen Guvenlik Sorulari

| Soru | Faz | Erteleme nedeni |
|------|-----|-----------------|
| Gorev-bazli yetkilendirme (kullanici X, Y gorevini calistirabilir ama Z'yi degil) | Phase 2 | Kaynak-gorev yetkilendirme matrisi henuz tasarlanmadi |
| Islem-bazli yetkilendirme (kullanici X gonderebilir ama iptal edemez) | Phase 2 | Phase 1.5 allowlist ya hep ya hic |
| Gorev-bazli risk seviyesi siniflandirmasi | Phase 2 | Gorev risk puanlama cercevesi gerektirir |
| Sifrelenmis/vault-tabanli gizli bilgi depolama | Phase 2 | Phase 1.5 ortam-degiskeni temel cizgisi kullanir |
| Otomatik gizli bilgi rotasyonu | Phase 2 | Phase 1.5 yalnizca manuel rotasyon yetenegi gerektirir |
| Gorev yurutme icin dosya sistemi sinirlamasi | Phase 2 | Runtime eylemleri zaten yollari dogrular; daha derin sinirlama sertlestirme |
| Hiz sinirlandirma / kisitlama | Phase 2 | Phase 1.5'te kontrat seviyesinde hiz siniri yok |
| Denetim gunlugu saklama ve kurcalama dayanikliligi | Phase 2 | Phase 1.5 yalnizca alan mevcudiyeti gerektirir |
| Coklu-kaynak allowlist (kaynak kanali basina farkli listeler) | Phase 2 | Phase 1.5 tek duz allowlist kullanir |
| Gelismis operator is akislari (uzaktan operator erisimi, zenginlestirilmis denetim izi) | Phase 2+ | Phase 1.5 operator istisnasi yerel/manuel/yalnizca-yonetici |
| Bridge-seviyesi mTLS veya tasiima sifreleme | Phase 2+ | Phase 1.5 Bridge yalnizca localhost veya guvenilir ag |

---

## 11. Phase 1.5-D Cikis Kontrolu

| Kriter | Donduruldu mu? | Kanit |
|--------|----------------|-------|
| Yetkisiz cagiran runtime'dan once durduruluyor | **EVET** | Bridge'de allowlist uygulamasi, sourceUserId uzerinden. Eksik/yetkisiz sourceUserId runtime'dan once reddedilir. |
| Hatayi bicimlendirilmis istek runtime'dan once durduruluyor | **EVET** | Yapisal dogrulama (adim 1), islem dogrulamasi (adim 2), alan-seviyesi dogrulama (adim 4) runtime cagrisindan once gerceklesir. |
| Allowlist uygulama sahibi acik | **EVET** | Bridge sahip. Runtime allowlist kontrolu yapmaz. sourceUserId uzerinden calisir. Bos/eksik allowlist = hepsini reddet. |
| Onay pending/onaylanmamis davranisi acik | **EVET** | `approvalStatus: "pending"` Bridge'de `APPROVAL_REQUIRED` ile runtime'dan once reddedilir. Kesin kural. |
| Operator istisnasi dar ve acik | **EVET** | Yerel, manuel, yalnizca-yonetici. Bridge kontratinin parcasi degil. Golge-yol-karsi kural belirtildi. |
| Yasakli dis yollar acik | **EVET** | Alti yasakli yol sayildi. Uygulama prensibi: Bridge onlara rota yazmaz. |
| Minimum gizli bilgi temel cizgisi acik | **EVET** | Sabit-kodlanmis gizli bilgi yasak. Ortam-degiskeni birincil. Telegram tokeni baslangiçta zorunlu. Localhost yedek kimlik bilgisi gecici olarak kabul edildi. |
| Minimum denetim kumesi acik | **EVET** | On alan tanimlandi. Kaydeden katman atandi. Operator denetimi runtime-tarafi. |
| Saglik maruz birakma acik | **EVET** | Disa acik, allowlist-uygulamali, tek `health` alanina temizlenmis. Dahili detay cikarilmis. |

**Tum kriterler donduruldu. Phase 1.5-D kapatilabilir.**

---

## 12. Sonraki Adimlar

| Adim | Amac | On kosul |
|------|------|----------|
| **Phase 1.5-E** | Bridge implementasyonu (dondurulan kontrat + guvenlik temel cizgisine gore) | Phase 1.5-D kapali |
| **Phase 1.5 Cikis Dogrulama** | Uctan uca yol calisiyor, allowlist uygulaniyoir, token politikasi kullaniliyor | Phase 1.5-E kapali |
| **Phase 2** | Guvenlik / Politika Sertlestirme | Phase 1.5 kapali |
