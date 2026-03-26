# Sprint 10 Retrospective — Acımasız Süreç Eleştirisi

**Date:** 2026-03-25
**Scope:** Sprint 7→10 süreç analizi, Sprint 11-12 iyileştirme aksiyonları
**Author:** Copilot Agent (talep: Operator)

---

## Bölüm 1: Sayılarla Gerçek

### Kod vs Doküman Oranı

| Metrik | Değer |
|--------|-------|
| Python kod | 63 dosya, **434 KB** |
| TypeScript kod | 30 dosya, **74 KB** |
| **Toplam kod** | **508 KB** |
| Markdown doküman | 79 dosya, **798 KB** |
| Phase report sayısı | 32 |
| Evidence dosyası | 16 |

**Doküman/kod oranı: 1.57x.** Dökümantasyon kodun 1.5 katı büyük. Bu bir red flag.

### Closure Overhead

Sprint 10 implementation commit: `2763abf` (31 dosya, 2530 insertion)
Sprint 10 closure commit: `954032a` (9 dosya, 1115 insertion)

**Closure pass, implementation'ın %44'ü kadar ek iş üretti.** Bunun büyük kısmı `test_sprint_5c.py` migration'ı olmasa bile, doküman güncellemeleri, evidence capture, validator çalıştırma, drift düzeltme ciddi overhead.

### Karar Kaydı Borcu

- DECISIONS.md: **42 karar** kayıtlı (D-001→D-080, bazıları yok)
- Gerçek karar sayısı: **D-088'e kadar** (88 karar alınmış)
- **46 karar kayıt dışı.** D-021→D-058 (38 karar) + D-081→D-088 Sprint 9-10 kararları eksik.
- Bu borç her sprint "taşınıyor" ama hiç ödenmedi.

### Git Commit Hijyeni

Sprint 10'da 2 commit: 1 implementation mega-commit (31 dosya) + 1 closure commit.
Sprint 9'da 1 mega-commit (49 dosya).
Sprint 8'de 5 commit ama hepsi 1 gün içinde.

**Her sprint tek bir "dump" commit.** Granüler commit yok. Bisect, revert, blame imkansız.

---

## Bölüm 2: Süreç Hastalıkları

### H-01: Doküman Seremonisi Aşırı

32 phase report, 79 markdown dosyası, closure pass dokümanı, evidence bundle, validator... Her sprint sonunda **doküman güncellemesi kodu yazmaktan daha uzun sürüyor.**

Semptomlar:
- Sprint kapanışı 3 aşamada oluyor (implementation → closure → closure-pass fix)
- Her sprint 5+ doküman güncelliyor (STATE, NEXT, HANDOFF, TASK-BREAKDOWN, PHASE-REPORT)
- Evidence dosyaları test output'unun copy-paste'i — git log zaten evidence
- Closure pass dokümanı ("SPRINT-10-CLOSURE-PASS.md") bir dokümanı düzeltmek için başka doküman üretmek

**Teşhis: Bürokrasi döngüsü.** Doküman → dokümanı doğrula → doğrulamayı dokümanla → repeat.

### H-02: Mega-Commit Anti-Pattern

Sprint 10: 31 dosya tek commit. Task 10.1→10.8 arasında 0 ara commit.

Sonuçlar:
- `git bisect` kullanılamaz
- Tek bir task'ta sorun varsa tüm sprint revert edilmeli
- Code review yapılması imkansız (2530 satır diff)
- "Sprint push" kuralı var ama "task commit" kuralı yok

### H-03: Tekrarlanan Bilgi (DRY İhlali)

Aynı bilgi 6+ yerde yazılıyor:
1. SPRINT-10-TASK-BREAKDOWN.md (plan)
2. PHASE-5B-SPRINT-10-SSE-LIVE-UPDATES.md (rapor)
3. SESSION-HANDOFF.md (handoff)
4. docs/ai/STATE.md (state)
5. docs/ai/NEXT.md (roadmap)
6. CLAUDE.md (context)
7. SPRINT-10-CLOSURE-PASS.md (closure checklist)

Sprint 10 test count 3 yerde farklı yazıldı (114 vs 184) çünkü aynı veri 6 yerde tutulunca senkronizasyon bozuluyor.

### H-04: "Closure Pass" İkinci Sprint Problemi

Sprint 10 timeline:
- 20:45 — Sprint 9 push (geçmiş sprint!)
- 20:50 — Copilot instructions
- ~21:00-22:35 — Sprint 10 implementation
- 22:35 — Sprint 10 "COMPLETE" commit
- 22:52 — Closure pass commit (doküman düzeltmeleri)

**İmplementation'dan 17 dakika sonra "COMPLETE" denmiş, ama 17 dakika daha closure gerekmiş.** Bu "COMPLETE" etiketinin güvenilirliğini sıfırlıyor.

### H-05: DECISIONS.md Borcu Kronik

D-021→D-058 borcu Sprint 7'den beri taşınıyor. Her sprint handoff'ta "documentation debt" yazılıyor ama hiç ödenmedi. Bu artık borç değil, **kasıtlı ihmal.**

Sonuç: DECISIONS.md güvenilmez kaynak. 88 kararın 46'sı orada yok.

### H-06: Evidence Bundle Tiyatrosu

`evidence/sprint-10/` içeriği:
- `pytest-output.txt` — `git log` ve CI zaten bunu tutar
- `vitest-output.txt` — aynı
- `tsc-output.txt` — "0 errors" yazan 1 satırlık dosya
- `lint-output.txt` — aynı
- `build-output.txt` — npm build çıktısı
- `sse-stream.txt` — "test-based evidence" notu (gerçek curl yok)
- `validator-output.txt` — validator çıktısı

**Bunların %90'ı gereksiz.** CI pipeline varsa otomatik yakalanır. CI yoksa bile `git log` + test komutu yeterli. Bu dosyalar repo'yu şişiriyor ve stale kalma garantili.

### H-07: GPT Cross-Review Darboğazı

Her sprint'te "GPT review PENDING" yazılıyor. Sprint 10'da 20/21 exit criteria — tek eksik GPT review. Bu review:
- Asenkron (farklı LLM session)
- Sprint kapanışını bloklamıyor ama "COMPLETE" diyemiyorsunuz
- Gerçek bir gating function değil

**Teşhis: Ya blocker ya değil. İkisi arası olamaz.**

### H-08: Test Altyapısı Kırılganlığı

- `test_sprint_5c.py` Sprint 5'ten beri `sys.exit(0)` ile kaldı
- `conftest.py`'da `collect_ignore` ile gizlendi
- Sprint 10 closure'da fix edilene kadar **70 test pytest'ten gizliydi**
- test_sprint_5c = 56 orijinal test → 70 pytest test (assertion split sonrası)
- Başlangıçtaki "170+ test" hedefi hiç gerçekçi değilmiş — 100+14=114 gerçekti

**Kırık testi gizlemek, test sayısını şişirmekten daha kötü.**

---

## Bölüm 3: Kök Neden Analizi

| Hastalık | Kök Neden |
|----------|-----------|
| H-01 Doküman seremonisi | Protokol (D-077) çok katı yazılmış. Her sprint için same ceremony. Küçük sprint = büyük sprint = aynı overhead |
| H-02 Mega-commit | "Sprint push" kuralı var, "task commit" kuralı yok |
| H-03 DRY ihlali | 7 doküman birbirini tekrarlıyor çünkü hepsi bağımsız "source of truth" olarak tasarlandı |
| H-04 İkinci closure | İlk closure'da doküman drift fark edilmiyor çünkü review yok |
| H-05 DECISIONS borcu | İş planında karar kaydı yok — kararlar sprint task'ı olarak sayılmıyor |
| H-06 Evidence tiyatrosu | CI yok, manuel evidence → stale + redundant |
| H-07 GPT review belirsizliği | Exit criteria'da var ama enforcement yok |
| H-08 Test kırılganlığı | Eski test format migrate edilmedi, gizlendi |

---

## Bölüm 4: Sprint 11-12 İçin Aksiyonlar

### A-01: Doküman Sayısını %60 Azalt (Sprint 11 Başında)

**Mevcut 7 güncelleme noktası → 3'e indir:**

| Kaldır | Sebebi | Yerine |
|--------|--------|--------|
| Phase report (ayrı dosya) | Task breakdown zaten aynı bilgiyi taşıyor | Task breakdown'a "Results" section ekle |
| SPRINT-X-CLOSURE-PASS.md | Closure checklist'i dokümanla düzeltmek circular | Validator script'i genişlet |
| SESSION-HANDOFF.md (ayrı dosya) | CLAUDE.md zaten handoff bilgisi taşıyor | CLAUDE.md "Last Sprint" section'ı yeterli |
| Evidence dosyaları | Git log + test komutu yeterli | Validator çıktısını git commit message'a yaz |

**Sprint kapanışında güncelle:**
1. `SPRINT-N-TASK-BREAKDOWN.md` → Results section ekle (exit criteria + test count)
2. `docs/ai/STATE.md` → Aktif phase güncelle
3. `CLAUDE.md` → Last Sprint + Build & Test güncelle

**NEXT.md koruyoruz** — roadmap hâlâ gerekli ama minimal.

### A-02: Task-Level Commit Kuralı (Sprint 11'den İtibaren)

Her task tamamlandığında:
```bash
git add <task_files>
git commit -m "Sprint N Task X.Y: <description>"
```

Sprint sonunda `git push`. Ara push opsiyonel.

**Minimum:** 1 task = 1 commit. 8 task'lı sprint = minimum 8 commit.

Fayda: bisect çalışır, revert granüler, code review mümkün.

### A-03: DECISIONS.md Borç Ödeme (Sprint 11 Task 0)

Sprint 11'in ilk task'ı: D-021→D-088 arasındaki eksik kararları DECISIONS.md'ye yaz.

**Format:** Her karar 5 satır max:
```
### D-XXX: Title
**Phase:** N | **Status:** Frozen
One-line description. Trade-off: X vs Y.
```

Bu iş 1 defaya mahsus. Sonraki sprint'lerde karar alındığı anda DECISIONS.md güncellenir.

### A-04: Validator Script'i Tek Kaynak Yap

`validate_sprint_docs.py`'ı genişlet:
- Test count'u `pytest --co -q` + `vitest list` ile otomatik say
- Doküman freshness'ı git diff ile kontrol et (mtime değil)
- Çıktı: `PASS/FAIL` + summary → bu summary commit message'a girer
- Evidence dosyaları **üretme** — validator output tek evidence

```bash
python tools/validate_sprint_docs.py --sprint 11 --auto-count
# Çıktı:
# Backend: 184 tests collected
# Frontend: 29 tests collected
# STATE.md: updated (diff +3 lines)
# CLAUDE.md: updated
# Result: ALL PASS
```

### A-05: GPT Cross-Review'ı Zorunlu veya Kaldır

İki seçenek (operator karar vermeli):

**Seçenek A — Kaldır:** Exit criteria'dan çıkar. Tek agent (Copilot) sprint'i kapatabilir. GPT review opsiyonel.

**Seçenek B — Zorunlu:** Sprint implementation bitmeden GPT review yapılır. Review sonrası fix + re-review. Ancak o zaman sprint'e +1 gün ekle.

**Seçenek C (önerilen) — Asenkron ama Tracked:** GPT review sprint kapanışından sonra yapılır. Bulgular varsa **sonraki sprint'in ilk task'ı** olarak girer. Sprint COMPLETE etiketi review beklemiyor.

### A-06: Test Altyapısı Sağlık Kuralı

Yeni kural: **Hiçbir test dosyası pytest collection'dan gizlenemez.**

- `collect_ignore` kullanmak yasak
- `sys.exit()` olan test dosyaları bulununca o sprint'in blocker'ı olur
- Her sprint sonunda: `pytest --co -q | tail -1` → "N tests collected" = gerçek sayı
- CLAUDE.md'deki test count her zaman `pytest --co -q` çıktısıyla eşleşmeli

### A-07: Single Source of Truth Per Data Point

| Veri | Tek Kaynak | Diğer yerler referans verir |
|------|-----------|---------------------------|
| Test count | `pytest --co -q` / `vitest list` output | CLAUDE.md sadece komutu yazar, sayıyı değil |
| Sprint status | SPRINT-N-TASK-BREAKDOWN.md | STATE.md "Sprint N: see task breakdown" |
| Frozen decisions | DECISIONS.md | Task breakdown'da "see D-XXX in DECISIONS.md" |
| Build commands | CLAUDE.md Build & Test section | Başka yerde tekrarlanmaz |
| Architecture | CLAUDE.md + kod | Phase report'ta tekrarlanmaz |

### A-08: Sprint Kapanış Akışını Basitleştir

**Mevcut akış (Sprint 10):**
1. Implement 8 tasks
2. Tüm testleri çalıştır
3. Evidence bundle oluştur (7 dosya)
4. TASK-BREAKDOWN → COMPLETE
5. STATE.md güncelle
6. NEXT.md güncelle
7. SESSION-HANDOFF.md güncelle
8. CLAUDE.md güncelle
9. Phase report yaz
10. Validator çalıştır
11. Git commit + push
12. Closure pass dokümanı gelir → 6 aksiyon daha
13. İkinci commit + push

**Yeni akış (Sprint 11+):**
1. Her task'ta: implement → test → `git commit`
2. Tüm task'lar bittikten sonra:
   - `python tools/validate_sprint_docs.py --sprint N --auto-count`
   - TASK-BREAKDOWN.md'ye "## Results" section ekle (validator çıktısını yapıştır)
   - STATE.md 1 satır güncelle
   - CLAUDE.md "Last Sprint" güncelle
3. `git add -A && git commit -m "Sprint N closure" && git push`

**13 adım → 3 adım.** İkinci closure pass gerekmez çünkü drift oluşmaz.

---

## Bölüm 5: Uygulama Planı

### Sprint 11'de Uygulanacak

| Aksiyon | Ne Zaman | Nasıl |
|---------|----------|-------|
| A-01 | Sprint 11 başında | Phase report dosyası oluşturmayı bırak. Task breakdown'a Results section pattern'ı uygula |
| A-02 | Sprint 11 task 1'den itibaren | Her task commit → minimum 1 commit per task |
| A-03 | Sprint 11 Task 0 | D-021→D-088 boşluğunu doldur (tek seferlik) |
| A-05 | Sprint 11 başında | Operator seçim yapar: A, B, veya C |
| A-06 | Sprint 11 başında | collect_ignore kaldırıldı (zaten yapıldı), test count kuralı eklenir |

### Sprint 12'de Uygulanacak

| Aksiyon | Ne Zaman | Nasıl |
|---------|----------|-------|
| A-04 | Sprint 12 task olarak | Validator script --auto-count özelliği |
| A-07 | Sprint 12 task olarak | Tekrarlanan bilgileri referansa dönüştür |
| A-08 | Sprint 12'de doğal olarak | Sprint 11 deneyimiyle refine et |

---

## Bölüm 6: Anti-Aksiyon (Yapmayacaklarımız)

| Teklif | Neden Yapmıyoruz |
|--------|-------------------|
| CI/CD pipeline kur | Scope dışı — önce süreç düzelsin, CI sonra gelir |
| Tüm eski raporları sil | Geçmiş context kaybolur. Sadece yeni rapor üretmeyi bırakıyoruz |
| DECISIONS.md'yi otomatik oluştur | Karar kaydetmek insan kararıdır, otomatize edilemez |
| Her commit'i push et | Network overhead + gereksiz. Sprint sonunda push yeterli |

---

## Bölüm 7: Başarı Metrikleri

Sprint 12 sonunda şu metrikleri karşılaştır:

| Metrik | Sprint 10 (baseline) | Sprint 12 (hedef) |
|--------|---------------------|-------------------|
| Closure commit sayısı | 2 | 1 |
| Güncellenen doküman sayısı | 7+ | 3 |
| Oluşturulan yeni dosya (doküman) | 3 (report + closure + evidence) | 0 |
| Task commit granülerliği | 1 commit / 8 task | 1 commit / 1 task |
| DECISIONS.md boşluk | 46 kayıp karar | 0 |
| Closure süresi (implement → push) | 17+ dakika | <5 dakika |
| Doküman/kod oranı | 1.57x | <1.0x |

---

*Retrospective prepared by: Copilot Agent*
*Evidence: git log, file system metrics, commit diffs, document analysis*
*Rule: Bu retrospective bir doküman seremonisi değildir. Aksiyonlar SPRINT-11-TASK-BREAKDOWN.md'ye task olarak girecek.*
