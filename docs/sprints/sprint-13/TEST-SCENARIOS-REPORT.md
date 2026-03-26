# Test Senaryolari Raporu — Sprint 12+ Gelistirmeler

**Tarih:** 2026-03-26
**Ortam:** Backend :8003, Frontend :3001, WMCP :8001
**Test edilen ozellikler:** D-102 token budget, role-based tool access, stage pipeline, rework cycles, quality gates

---

## Senaryo Ozeti

| # | Karmasiklik | Goal | Sonuc | Stage | Rework | Tool Calls | Policy Deny | Sure |
|---|-------------|------|-------|-------|--------|------------|-------------|------|
| 1 | Trivial | Python versiyon + pip paket sayisi raporla | Completed* | 4 | 0 | 35 | 11 | ~6m |
| 2 | Simple | capabilities.json tool/risk analizi | Completed | 11 | 6 | 60 | 5 | ~12m |
| 3 | Medium | BudgetConfig sinifi inceleme/degerlendirme | Completed | 4 | 0 | 29 | 1 | ~6.5m |
| 4 | Complex | API mimari degerlendirme (router, endpoint, guvenlik) | Completed | 8 | 0 | 50 | 2 | ~7m |
| 5 | Medium+ | Matematik web servisi gelistir (FastAPI, port 9000) | Running** | 8 | - | - | - | - |

*Senaryo 1: str.get() crash nedeniyle stuck kalmisti — manuel fix ile completed'a alindi.
**Senaryo 5: Mission agent pipeline calisiyor; servis paralelde manuel olusturuldu ve 9000'de calistiriliyor.

---

## Senaryo 1: Trivial — Sistem Bilgisi Sorgulama

**Goal:** "Sistemdeki Python versiyonunu ve pip paketlerinin sayisini raporla"
**Complexity:** trivial
**Mission ID:** mission-20260326074224-55352
**Sonuc:** Running (tum stage'ler completed, summary bekleniyor)

### Stage Pipeline
| # | Role | Status | Tool Calls | Policy Deny | Sure |
|---|------|--------|------------|-------------|------|
| 1 | Analyst | completed | 10 | 3 | 50.1s |
| 2 | Developer | completed | 9 | 5 | 96.2s |
| 3 | Tester | completed | 10 | 1 | 115.8s |
| 4 | Reviewer | completed | 6 | 2 | 98.2s |

### Bulgular
- **Policy deny sayisi yuksek (11):** Trivial gorev icin bile tool access enforcement aktif calisiyor. Analyst ve Developer rolleri kisitli tool'lara erismek istemis ve engellenimis.
- 4 stage, 0 rework — basit gorev dogru pipeline'dan gecti.

---

## Senaryo 2: Simple — Dosya Analizi (Rework Donguleri)

**Goal:** "config/capabilities.json dosyasini oku ve icindeki tool sayisini, risk dagilimini analiz et"
**Complexity:** simple
**Mission ID:** mission-20260326074232-55352
**Sonuc:** Completed (11 stages, 6 rework)

### Stage Pipeline
| # | Role | Status | Tool Calls | Policy Deny | Sure | Not |
|---|------|--------|------------|-------------|------|-----|
| 1 | Analyst | completed | 10 | 0 | 73.7s | |
| 2 | Developer | completed | 7 | 1 | 83.2s | |
| 3 | Tester | completed | 4 | 0 | 59.3s | Gate fail |
| 4 | Developer | completed | 9 | 1 | 161.2s | Rework #1 |
| 5 | Tester | completed | 5 | 0 | 49.6s | Rework #1 |
| 6 | Developer | completed | 5 | 1 | 62.1s | Rework #2 |
| 7 | Tester | completed | 7 | 0 | 59.7s | Rework #2 |
| 8 | Developer | completed | 5 | 0 | 80.2s | Rework #3 |
| 9 | Tester | completed | 1 | 0 | 15.4s | Rework #3 |
| 10 | Reviewer | completed | 6 | 2 | 45.4s | Gate pass |
| 11 | Manager | completed | 1 | 0 | 44.0s | Final |

### Bulgular
- **3 Developer-Tester rework dongusu:** Quality gate'ler calisiyor — Tester red verdikce Developer tekrar calisti.
- **Son Reviewer gate PASS:** 3. rework'ten sonra Reviewer onayladi.
- Dashboard'da rework ikonlari (circled arrow) ve gate check sonuclari (X/check) gorsel olarak gorunuyor.
- Toplam 60 tool call, 5 policy deny — yuksek tool kullanimli senaryo.

---

## Senaryo 3: Medium — Kod Inceleme ve Degerlendirme

**Goal:** "agent/context/token_budget.py BudgetConfig sinifini incele, her limitin amacini acikla ve degerlerin uygunlugunu degerlendir"
**Complexity:** medium
**Mission ID:** mission-20260326074241-55352
**Sonuc:** Completed (4 stages, 0 rework)

### Stage Pipeline
| # | Role | Status | Tool Calls | Policy Deny | Sure |
|---|------|--------|------------|-------------|------|
| 1 | Analyst | completed | 10 | 0 | 70.9s |
| 2 | Developer | completed | 7 | 1 | 86.3s |
| 3 | Tester | completed | 3 | 0 | 56.4s |
| 4 | Reviewer | completed | 9 | 0 | 166.1s |

### Bulgular
- **Temiz pipeline:** 4 stage, 0 rework, tum gate'ler ilk denemede gecti.
- Reviewer 166s surmus — kapsamli kod incelemesi yapildi.
- 1 policy deny (Developer'da) — tool access enforcement calisiyor.
- Gate Passed: gate_3_review PASS, review_decision = Approved.

---

## Senaryo 4: Complex — Mimari Degerlendirme (Tam 8-Stage Pipeline)

**Goal:** "Mission Control API mimarisini degerlendir: tum router'lari listele, endpoint sayisi, tutarsizliklar, guvenlik katmanlari"
**Complexity:** complex
**Mission ID:** mission-20260326074249-55352
**Sonuc:** Completed (8 stages, 0 rework)

### Stage Pipeline
| # | Role | Status | Tool Calls | Policy Deny | Sure |
|---|------|--------|------------|-------------|------|
| 1 | Product-Owner | completed | 0 | 0 | 10.2s |
| 2 | Analyst | completed | 10 | 0 | 57.4s |
| 3 | Architect | completed | 10 | 0 | 77.6s |
| 4 | Project-Manager | completed | 0 | 0 | 12.2s |
| 5 | Developer | completed | 10 | 0 | 54.7s |
| 6 | Tester | completed | 10 | 0 | 83.1s |
| 7 | Reviewer | completed | 10 | 2 | 98.1s |
| 8 | Manager | completed | 0 | 0 | 12.7s |

### Bulgular
- **Tam 9-role pipeline calisti:** PO → Analyst → Architect → PM → Developer → Tester → Reviewer → Manager.
- PO, PM ve Manager rolleri tool kullanmiyor (toolPolicy: no_tools) — dogru davranis.
- Analyst ve Architect `take_screenshot` kullanamadi (D-102 Layer 5 enforcement) — 2 policy deny Reviewer'da.
- 8 artifact uretildi, tum gate'ler ilk denemede gecti.
- Toplam ~7 dakika — 8 stage icin makul.

---

## Senaryo 5: Medium+ — Matematik Web Servisi Gelistirme

**Goal:** "Python FastAPI ile matematik islemleri web servisi gelistir. POST /api/add, /api/subtract, /api/multiply, /api/divide. Port 9000'de calistir."
**Complexity:** medium (8-stage pipeline)
**Mission ID:** mission-20260326-082046-9f9a9c
**Sonuc:** Mission agent pipeline calisiyor; servis paralelde hazir kodla olusturuldu ve deploy edildi.

### Telegram Mesaj Ornegi

Asagidaki metin Telegram'dan OpenClaw bot'una gonderilebilir:

```
Bir Python FastAPI web servisi gelistir:
1) Toplama, cikarma, carpma, bolme endpoint'leri olsun (POST /api/add, /api/subtract, /api/multiply, /api/divide)
2) Her endpoint JSON body ile iki sayi alsin: {"a": 10, "b": 5}
3) Bolmede sifira bolme hatasi handle edilsin
4) Sonuc {"result": 15, "operation": "add"} formatinda donulsun
5) Port 9000'de calissin
6) Uygulamayi olustur, test et ve 9000 portunda calistir
```

### Olusturulan Dosyalar

| Dosya | Amac |
|-------|------|
| `agent/math_service/app.py` | FastAPI uygulamasi — 4 math endpoint + health |
| `agent/math_service/test_app.py` | 8 test (add, subtract, multiply, divide, zero div, negative, decimal, health) |

### Test Sonuclari

```
test_app.py::test_add               PASSED
test_app.py::test_subtract          PASSED
test_app.py::test_multiply          PASSED
test_app.py::test_divide            PASSED
test_app.py::test_divide_by_zero    PASSED
test_app.py::test_add_negative      PASSED
test_app.py::test_multiply_decimal  PASSED
test_app.py::test_health            PASSED
8 passed in 0.67s
```

### Endpoint Dogrulama (port 9000)

```
POST /api/add      {"a":10,"b":5}  → {"result":15.0,"operation":"add"}
POST /api/subtract {"a":10,"b":3}  → {"result":7.0,"operation":"subtract"}
POST /api/multiply {"a":4,"b":6}   → {"result":24.0,"operation":"multiply"}
POST /api/divide   {"a":20,"b":4}  → {"result":5.0,"operation":"divide"}
POST /api/divide   {"a":10,"b":0}  → 400 {"detail":"Sifira bolme hatasi"}
GET  /health                       → {"status":"ok","service":"math-service","port":9000}
```

### Genisletilebilirlik

Yeni matematik senaryolari eklemek icin `app.py`'ye yeni endpoint eklenip `test_app.py`'ye test yazilabilir. Ornek:
- `POST /api/power` — us alma
- `POST /api/modulo` — mod alma
- `POST /api/sqrt` — karekök

---

## Dogrulanan Ozellikler

### D-102 Token Budget Enforcement
- [x] Tool response truncation calisiyor (>10K truncate, >50K block)
- [x] Per-stage token logging calisiyor
- [x] Token Usage Report (D-102) paneli UI'da gorunuyor
- [ ] Token report JSON dosyasi — dashboard placeholder ID ile controller ID uyumsuzlugu nedeniyle "No token report" gosteriyor (bilinen bug, fix gerekli)

### Role-Based Tool Access (Layer 5)
- [x] `take_screenshot` analyst/architect/tester'dan kaldirildi
- [x] Runtime enforcement calisiyor — policy deny sayilari bunu dogruluyor
- [x] Senaryo 1'de 11 policy deny, Senaryo 2'de 5, Senaryo 3'te 1, Senaryo 4'te 2

### Quality Gates & Rework
- [x] Gate check'ler calisiyor (gate_1_requirements, gate_2_code_test, gate_3_review)
- [x] Rework donguleri calisiyor (Senaryo 2: 3 Developer-Tester cycle)
- [x] Gate fail sonrasi rework, gate pass sonrasi ilerleme

### Stage Pipeline
- [x] Trivial: 4-stage pipeline (Analyst → Developer → Tester → Reviewer)
- [x] Simple: 4-stage + rework (11 total)
- [x] Medium: 4-stage temiz
- [x] Complex: 8-stage tam pipeline (PO → Analyst → Architect → PM → Dev → Test → Review → Manager)

### UI Ozellikleri
- [x] Stage Pipeline gorsel timeline
- [x] Running stage animasyonu (pulse)
- [x] Rework ikonlari ve cycle sayaci
- [x] Gate check sonuclari (pass/fail)
- [x] Policy deny sayaci
- [x] State transitions timeline
- [x] Retry butonu failed mission'larda gorunuyor
- [x] Token Usage Report paneli (collapsible)

---

## Bilinen Sorunlar ve Fixler

1. **Token report ID uyumsuzlugu:** Dashboard placeholder mission ID ile controller'in olusturdugu mission ID farkli. Token report controller ID ile yaziliyor ama UI dashboard ID ile ariyor. Fix: normalizer'da controller ID resolve edilmeli.

2. **Senaryo 1 `str.get()` crash (FIXED):** Trivial mission tum stage'leri tamamlamasina ragmen `AttributeError: 'str' object has no attribute 'get'` ile crash etti. Sebep: `tool_calls_detail` listesinde bazen dict yerine string eleman olabiliyor. `_emit_mission_summary` fonksiyonunda `isinstance(tc, dict)` guard clause eklendi. Dashboard placeholder "failed" gosteriyor ama controller tarafinda 4/4 stage completed.

3. **Rework stage sayisi:** Senaryo 2'de "simple" olmasina ragmen 6 rework stage olusmus (11 total). Complexity routing ile stage sayisi sinirlanabilir.

---

## Ekler

- GIF kaydi: `mission-test-scenarios.gif` (16 frame, dashboard etklesimi)
- Mission dosyalari: `logs/missions/mission-20260326074*-55352*`
