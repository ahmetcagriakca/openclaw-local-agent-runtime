# Phase TG-1 — Minimal Telegram Caller Bootstrap Raporu

**Durum:** TAMAMLANDI (konfigrasyon on kosullari bekliyor)
**Tarih:** 2026-03-23
**Kapsam:** Gercek Telegram kullanicisinin dondurulan Bridge kontratina ulasmasini saglayan en ince cagiran katman

---

## 1. Ozet

Bu belge, gercek Telegram uctan uca dogrulamasini mumkun kilmak icin olusturulan minimum Telegram bot implementasyonunu raporlar. Bot, OpenClaw platformu degildir — yalnizca gercek Telegram mesajlarini dondurulan Bridge kontratina ulastiran en ince yol.

| Bilesen | Durum |
|---------|-------|
| Bridge (Phase 1.5-E) | Calisiyor |
| oc runtime | Calisiyor |
| Telegram bot kodu | Olusturuldu |
| Bot token konfigutrasyonu | **Bekliyor** |
| Gercek kullanici allowlist girisi | **Bekliyor** |

---

## 2. Olusturulan Dosyalar

| Dosya | Amac |
|-------|------|
| `telegram/oc-telegram-bot.py` | Minimal Telegram bot — mesaj alir, komut esler, Bridge cagrir |

---

## 3. Secilen Dil/Runtime

**Python 3.14** + `requests` kutuphanesi.

| Bilesen | Surum | Durum |
|---------|-------|-------|
| Python | 3.14.3 | Yuklu |
| requests | 2.32.5 | Yuklu |
| pwsh (Bridge cagrisi icin) | 7 | Yuklu |

**Neden Python:** Makinede mevcut, `requests` Telegram Bot API icin yeterli, `subprocess` Bridge cagrisi icin yeterli. Tek dosya, sifir ek bagimlilik. En ince calisan yol.

---

## 4. Telegram Komut Yuzeyi

Bot, acik komut-stili isleme kullanir. Serbest-form niyet ayristirma yok.

| Komut | Bridge islemi | Aciklama |
|-------|--------------|----------|
| `/submit <gorevAdi> <json_args>` | `submit_task` | Gorev gonder |
| `/status <taskId>` | `get_task_status` | Gorev durumu sorgula |
| `/health` | `get_health` | Runtime saglik kontrolu |
| `/help` veya `/start` | (yerel) | Komut listesi goster |

### Ornek kullanim

```
/submit create_note {"filename":"test.txt","content":"merhaba"}
/status task-20260322-221638555-1648
/health
```

### Acilmayan islemler

- Retry: yok (Phase 1.5 karari: yalnizca operator)
- List: yok (dis kontratta yok)
- Ham eylem: yok (yasak)
- Operator islemleri: yok (yerel/manuel/yonetici istisnasi)

---

## 5. Bridge Cagri Yolu

Bot, Bridge'i alt surecle cagir:

```
pwsh -NoProfile -ExecutionPolicy Bypass -File bridge/oc-bridge.ps1 -RequestJson <json>
```

- Dondurulan dis kontrat oldugu gibi kullanilir
- Runtime betikleri dogrudan cagrilmaz
- Atlama yolu yok
- 60 saniyelik alt surec zaman asimi

### Istek olusturma ornegi (submit_task)

```json
{
  "operation": "submit_task",
  "taskName": "create_note",
  "arguments": {"filename": "test.txt", "content": "merhaba"},
  "source": "telegram",
  "sourceUserId": "123456789",
  "requestId": "tg-a1b2c3d4e5f6",
  "approvalStatus": "preapproved"
}
```

`sourceUserId`, Telegram mesajindan gelen gercek numerik kullanici kimlik bilgisidir. Bot bu degeri uretmez, degistirmez veya donusturmez.

---

## 6. Gercek Kullanici Kimlik Bilgisi Isleme

Bot, her gelen Telegram guncellemesinden `message.from.id` degerini cikarir. Bu, Telegram tarafindan atanan numerik kullanici kimlik bilgisidir.

| Adim | Islem |
|------|-------|
| 1 | Telegram mesaji gelir |
| 2 | `message.from.id` cikarilir (Telegram numerik kimlik bilgisi) |
| 3 | String'e donusturulur |
| 4 | Bridge isteginde `sourceUserId` olarak kullanilir |
| 5 | Bridge, allowlist'e karsi dogrular |

Bot, kimlik bilgisini fabrikasyon yapmaz, gecersiz kilmaz veya donusturmez. Telegram'in sagladigi degeri oldugu gibi kullanir.

---

## 7. Allowlist Guncelleme

### Mevcut allowlist

```json
{
  "allowedUserIds": [
    "test-user-001"
  ]
}
```

### Gerekli guncelleme

Gercek Telegram kullanicisinin numerik kimlik bilgisi eklenmelidir:

```json
{
  "allowedUserIds": [
    "test-user-001",
    "<GERCEK_TELEGRAM_KULLANICI_ID>"
  ]
}
```

### Kimlik bilgisi nasil elde edilir

Iki yol:
1. Telegram'da `@userinfobot`'a mesaj gondererek kendi numerik kimlik bilginizi ogrenin
2. Botu token ile baslatiin, mesaj gonderin — bot konsolunda `[msg] user=<ID>` olarak gorunur, ardindan allowlist'e ekleyin

---

## 8. Konfigurasyon Gereksinimleri

### Zorunlu

| Gereksinim | Nasil | Durum |
|------------|-------|-------|
| Bot tokeni | `$env:OC_TELEGRAM_BOT_TOKEN` ortam degiskeni | **AYARLANMADI** |
| Gercek kullanici ID allowlist'te | `bridge/allowlist.json`'a numerik ID ekle | **YAPILMADI** |

### Hazir

| Gereksinim | Durum |
|------------|-------|
| Python 3.14 + requests | Yuklu |
| Bridge betigi (`bridge/oc-bridge.ps1`) | Mevcut |
| pwsh 7 | Yuklu |
| Allowlist dosyasi | Mevcut (guncellenmeli) |

### Botu baslatma

```bash
# 1. Bot tokenini ayarla
export OC_TELEGRAM_BOT_TOKEN="buraya-bot-tokeniniz"

# 2. Allowlist'e gercek kullanici ID'nizi ekleyin
# bridge/allowlist.json dosyasini duzenleyin

# 3. Botu baslatin
cd /c/Users/AKCA/oc
python telegram/oc-telegram-bot.py
```

### Beklenen baslangic ciktisi

```
[startup] Verifying bot token...
[startup] Bot: @botunuzun_adi (id=123456789)
[startup] Bridge: C:\Users\AKCA\oc\bridge\oc-bridge.ps1
[startup] Listening for messages...
```

---

## 9. Minimal Gozlemlenebilirlik

Bot stdout/stderr'e yazdirrir:

| Oneki | Ne zaman | Icerik |
|-------|----------|--------|
| `[startup]` | Baslangicta | Bot kimligi, bridge yolu dogrulamasi |
| `[msg]` | Her mesajda | Kullanici ID, chat ID, metin onizlemesi |
| `[bridge-req]` | Her Bridge isteginde | Islem, gorev adi, kullanici ID, istek ID |
| `[bridge-resp]` | Her Bridge yanitinda | Tam JSON yanit |
| `[warn]` | Gecici hatalar | Telegram API hatalari |
| `[error]` | Ciddi hatalar | Mesaj isleme hatalari |

Bu, gercek Telegram -> Bridge -> runtime yolunu kanitlamak icin yeterlidir.

---

## 10. Yapilan Dogrulama

Bot kodu yazildi ve hazir. **Gercek Telegram dogrulamasi yapilmadi** cunku:

1. `OC_TELEGRAM_BOT_TOKEN` ortam degiskeni ayarlanmadi — bot baslatilaamaz
2. Gercek Telegram kullanici numerik kimlik bilgisi allowlist'te yok

Her ikisi de kullanicinin girdisi gerektiren konfigurasyon on kosullaridir.

---

## 11. Mimari Uyumluluk

| Dondurulan karar | Bot uyumu |
|------------------|-----------|
| Dis yuzey yalnizca gorev-merkezli | Evet — yalnizca submit/status/health |
| Ham eylem cagrisi yasak | Evet — acilmadi |
| Bridge asla orkestrator degil | Evet — bot Bridge'i cagiirir, Bridge orkestrasyon yapmaz |
| Polling-only model | Evet — kullanici `/status` ile manuel yoklama yapar |
| Retry dis kontratta yok | Evet — `/retry` komutu yok |
| Operator istisnasi yerel/manuel | Evet — bot uzerinden operator islemi yok |
| Gizli bilgi sabit-kodlanmis olamaz | Evet — token ortam degiskeninden okunur |
| Allowlist zorunlu | Evet — Bridge baslangicinda uygulanir |
| approvalStatus pending reddedilir | Evet — bot `preapproved` gonderir, Bridge uygular |

---

## 12. Kalan Bosluklar

| Bosluk | Tip | Cozum |
|--------|-----|-------|
| Bot tokeni ayarlanmadi | Konfigurasyon | `OC_TELEGRAM_BOT_TOKEN` ortam degiskenini ayarlayin |
| Gercek kullanici ID allowlist'te yok | Konfigurasyon | Numerik Telegram kullanici ID'nizi `bridge/allowlist.json`'a ekleyin |

Her iki bosluk da konfigurasyon seviyesindedir, kod degisikligi gerektirmez.

---

## 13. Gercek Telegram Kapatma Hazirlik Kontrolu

### HAYIR — Gercek Telegram Kapatma oncesinde engellenmis

**Engelleyiciler:**

1. `OC_TELEGRAM_BOT_TOKEN` ortam degiskeni ayarlanmadi
2. Gercek Telegram kullanici numerik kimlik bilgisi `bridge/allowlist.json`'a eklenmedi

### Engel kaldirildiginda

Yukaridaki iki konfigurasyon tamamlandiginda:
1. Bot baslatilir (`python telegram/oc-telegram-bot.py`)
2. Telegram'dan `/submit create_note {"filename":"tg-test.txt","content":"gercek telegram OK"}` gonderilir
3. Bot Bridge'i cagiirir, runtime gorevi yurutur
4. `/status <taskId>` ile yoklama yapilir
5. Denetim kayitlari dogrulanir
6. Phase 1.5-TG gercek Telegram kapatma adimi yeniden calistirilir

---

## 14. Sonraki Adimlar

```
1. Bot tokenini ayarla:  export OC_TELEGRAM_BOT_TOKEN="..."
2. Kullanici ID'ni ogren: Telegram'da @userinfobot'a mesaj at
3. Allowlist guncelle:    bridge/allowlist.json'a ID ekle
4. Botu baslat:           python telegram/oc-telegram-bot.py
5. Test et:               Telegram'dan /submit komutu gonder
6. Dogrula:               /status ile yokla, denetim kaydini kontrol et
7. Kapat:                 Phase 1.5-TG gercek Telegram kapatma adimini calistir
```
