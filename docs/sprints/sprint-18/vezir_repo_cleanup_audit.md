# Vezir Repo Cleanup Audit

**Date:** 2026-03-27  
**Scope:** repo structure, canonical docs, stale process/docs, archive strategy

## Executive Verdict

Sorun storage değil. Sorun **truth fragmentation** ve **process/doc drift**.

Ana problem başlıkları:
1. Aynı anda birden fazla döküman canonical truth gibi davranıyor.
2. Bazı rehber dökümanlar stale ve aktif olarak yanlış yönlendiriyor.
3. Tarihsel planning/debt/process artifact'ları aktif klasörlerde yaşıyor.
4. File count yüksekliği, yaşayan truth ile kapanmış tarihsel artifact'ların karışık tutulmasından geliyor.

Bu yüzden çözüm:
- rastgele dosya silmek değil,
- **source-of-truth compression**
- **archive boundary freeze**
- **active vs historical separation**

---

## Repo İçin Net Yönetim Modeli

### Main repo’da kalacaklar
Sadece yaşayan ve operasyonel truth:

- `README.md`
- `docs/ai/STATE.md`
- `docs/ai/NEXT.md`
- `docs/ai/DECISIONS.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/decisions/` içindeki formal decision records
- aktif sprint klasörü
- son phase closure report(lar)i
- current code / tests / configs / CI workflows

### Main repo’dan çıkacaklar
Tarihsel, kapanmış, referans değeri düşük veya tekrar eden materyal:

- eski sprint narrative docs
- eski review packets
- stale handoff/archive snapshot’ları
- resolved debt plans
- patch-history tarzı process dokümanları
- eski raw evidence bundle’ları
- duplicate closure narratives

---

## Karar Verilmiş Dosya Düzeyi Audit

## 1) KEEP — Canonical olarak kalsın

### `docs/ai/STATE.md`
Kalsın. Operasyonel truth için gerekli.

### `docs/ai/NEXT.md`
Kalsın ama sadeleşsin.
Sadece:
- current phase
- next sprint/phase
- mandatory constraints
- carry-forward items
olsun.

### `docs/ai/DECISIONS.md`
Kalsın ama hacim ve erişilebilirlik için iki katmanlı hale gelsin:
- `DECISIONS.md` = index + current frozen decision summary
- `docs/decisions/D-XXX-*.md` = tam kayıt

### `docs/architecture/ARCHITECTURE.md`
Kalsın ama Vezir reality ile senkronize edilsin.
Bu dosya canonical architecture ise yarım rebrand / yarım legacy halde kalamaz.

### `README.md`
Kalsın ama repo giriş noktası olarak sadeleştirilsin.
README her şeyi anlatmaya çalışmamalı.
README -> canonical docs’a yönlendirmeli.

---

## 2) REWRITE / MERGE — olduğu gibi kalmamalı

### `CLAUDE.md`
**Hüküm: Bu haliyle aktif rehber olarak kalmamalı.**

Problemler:
- repo-native workflow aktifmiş gibi davranıyor
- `docs/ai/handoffs/current.md` yolunu active truth gibi anlatıyor
- test/closure/context sayıları ve yönlendirmeleri stale risk taşıyor
- current state + workflow + architecture + assistant behavior her şeyi tek dosyada karıştırıyor

Yapılacak:
- ya tamamen archive edilecek
- ya da 1 sayfalık `AGENT-OPERATING-BRIEF.md` olarak yeniden yazılacak

Benim önerim:
- `CLAUDE.md` -> archive
- yerine kısa bir `docs/ai/AGENT-OPERATING-BRIEF.md`

### `docs/ai/PROCESS-GATES.md`
**Hüküm: Fazla uzun, fazla ayrıntılı, fazla bakım maliyetli.**

Problemler:
- patch-history taşıyor
- sprint-path özel ayrıntılar içeriyor
- `PROTOCOL.md` ve senin zorunlu süreç kurallarınla çakışıyor
- “aktif governance” olmaktan çok “governance history dump” olmuş

Yapılacak:
- `PROCESS-GATES.md` + `PROTOCOL.md` -> tek dosya
- yeni ad: `docs/ai/GOVERNANCE.md`

`GOVERNANCE.md` içinde sadece:
- source hierarchy
- sprint status model
- gate model
- done rule
- evidence rule
- closure rule
- archive rule
olsun.

Patch/history/old migration sections archive’a taşınsın.

### `docs/ai/PROTOCOL.md`
**Hüküm: tek başına kötü değil ama `PROCESS-GATES.md` ile ayrı yaşamamalı.**

Yapılacak:
- `GOVERNANCE.md` içine emilecek
- ayrı dosya olarak kalmayacak

---

## 3) ARCHIVE — aktif path’ten çıkar

### `docs/ai/DECISION-DEBT-BURNDOWN.md`
**Hüküm: aktif repo truth’unda gereksiz.**

Neden:
- decision debt zero deniyor
- bu dosya geçmişteki debt ödeme planı
- aktif operasyon için gerekli değil
- historical value var, current operational value yok

Yapılacak:
- archive repo’ya taşı

### Eski sprint ve closure narrative’ları
Kural:
- aktif sprint + son kapanan phase raporu main repo’da kalır
- daha eski narrative’ler archive repo’ya taşınır

### Stale handoff mantığı
Eğer gerçekten `current.md` modeline geçilmeyecekse:
- handoff/archive sistemi main repo’ya hiç sokulmasın
- historical handoff’lar archive repo’ya gitsin

### Resolved migration / debt / patch plan docs
Örnek tipler:
- debt burn-down plans
- migration model notes
- patch history docs
- retroactive closure helper docs
- one-time cleanup docs

Bunlar aktif repo’yu kalabalıklaştırıyor.
Archive repo’ya taşınmalı.

---

## 4) DELETE / QUARANTINE — koşullu

Aşağıdakiler doğrudan silinmesin; önce quarantine / archive yapılmalı:

- repo-native workflow referansları (eğer repo’da gerçek değilse)
- stale “current.md is active” referansları
- aynı sprint için birden fazla closure truth
- aynı kuralı farklı wording ile anlatan dökümanlar

Kural:
- bir bilgi active truth ise tek yerde yaşar
- diğer tüm tekrarlar silinir veya archive edilir

---

## Main Repo İçin Yeni Hedef Yapı

```text
docs/
  ai/
    STATE.md
    NEXT.md
    DECISIONS.md
    GOVERNANCE.md
    ACTIVE-SPRINT.md
    AGENT-OPERATING-BRIEF.md
  architecture/
    ARCHITECTURE.md
  decisions/
    D-105-...
    D-106-...
    ...
  phase-reports/
    PHASE-5.5-CLOSURE-REPORT.md
  sprints/
    sprint-17/
      README.md
      SPRINT-17-TASK-BREAKDOWN.md
      artifacts/
```

### Ne kaldırıyoruz
- `PROTOCOL.md` ayrı dosya olarak
- `PROCESS-GATES.md` ayrı dosya olarak
- stale `CLAUDE.md`
- resolved debt plans active path’ten
- archive/stale/handoff historical dumps main repo’dan

---

## Archive Repo Önerisi

## Ayrı archive repo mantıklı mı?
**Evet, mantıklı.** Ama sadece doğru kapsamla.

Benim net önerim:
- ayrı repo adı: `vezir-archive`
- amaç: immutable historical records
- main repo: yaşayan operasyonel gerçek
- archive repo: kapanmış tarih

### Archive repo’ya ne gider
1. eski sprint klasörleri
2. raw evidence bundle’ları
3. stale handoff/history
4. resolved debt plans
5. old review packets
6. retroactive closure docs
7. superseded process docs
8. archived phase reports (son 1-2 hariç)

### Archive repo’ya ne gitmez
1. canonical decisions
2. current architecture
3. current state/next
4. current governance
5. active sprint docs
6. code ile doğrudan referanslanan operational docs
7. CI’nin ihtiyaç duyduğu dosyalar

### Archive repo formatı
Önerilen yapı:

```text
vezir-archive/
  README.md
  phase-reports/
  sprints/
    sprint-07/
    sprint-08/
    ...
  reviews/
  handoffs/
  process-history/
  debt-plans/
  evidence/
```

### Archive repo’nun çalışma kuralı
- write-rare, read-rare
- no active truth
- no active workflows depend on archive repo
- references only from index docs if needed

---

## Dosya Sayısı Yüksekliği İçin En İyi Pratik

Dosya boyutundan çok dosya sayısı arttığında en büyük maliyet:
- navigation friction
- yanlış dokümanı truth sanma
- AI/context pollution
- review latency

Bunu azaltmak için:

### 1. “Active path budget” koy
Main repo’da docs altında aktif dosya sayısı sınırlı olsun.

Öneri:
- `docs/ai/` içinde 6–8 ana dosyadan fazlası kalmasın
- aktif sprint dışında eski sprint root’ları bulunmasın

### 2. Tek index entry kullan
Her klasörde bir README/index olsun.
Kişi dosya avcılığı yapmasın.

### 3. Historical narrative’leri dışarı taşı
Main repo’da narrative history biriktirme.
Summary kalsın, detay archive’a gitsin.

### 4. Generated evidence’ı main repo’da tutma
CI artifact ise repo’ya gömülü yaşamamalı.
Ya Actions artifact’ı olsun ya archive repo’ya taşınsın.

---

## Sıkı Temizlik Kararları

## Karar 1
`CLAUDE.md` bu haliyle canonical olmaktan çıkarılmalı.

## Karar 2
`PROCESS-GATES.md` ve `PROTOCOL.md` birleşmeli.
Yeni tek dosya: `GOVERNANCE.md`

## Karar 3
`DECISION-DEBT-BURNDOWN.md` active repo’dan archive’a gitmeli.

## Karar 4
`NEXT.md` completed sprint dump olmamalı.
Sadece ileriye bakan active roadmap olmalı.

## Karar 5
`BACKLOG.md` completed item taşımamalı.
Completed backlog archive’a gitmeli.
Active backlog = sadece open items.

## Karar 6
Repo-native handoff/current.md modeli ya gerçekten commit edilir ve freeze edilir ya da tüm referansları kaldırılır.
Ara form yasak.

## Karar 7
Archive repo açılmalı ama code/CI bağımlılığı yaratılmamalı.

---

## Uygulama Planı

## Phase A — Freeze
1. Canonical doc set’i sabitle
2. Archive boundary’yi sabitle
3. Hangi modelin aktif olduğuna karar ver:
   - STATE/NEXT modeli
   - current.md repo-native modeli
   Aynı anda ikisi olmaz.

## Phase B — Consolidate
1. `PROCESS-GATES.md` + `PROTOCOL.md` -> `GOVERNANCE.md`
2. `CLAUDE.md` -> replace/archive
3. `BACKLOG.md` -> open-only hale getir
4. `NEXT.md` -> forward-only hale getir

## Phase C — Move
1. resolved debt docs -> archive repo
2. old sprint docs -> archive repo
3. old review/handoff/process history -> archive repo
4. raw evidence -> archive repo or CI artifact strategy

## Phase D — Verify
1. README links broken mı kontrol et
2. docs referans grep’i yap
3. stale path referanslarını temizle
4. active truth listesi README’ye yaz

---

## Minimal Final Active Truth Set

Eğer agresif ama güvenli temizlik istiyorsan main repo’da şunlar kalsın:

- `README.md`
- `docs/ai/STATE.md`
- `docs/ai/NEXT.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/GOVERNANCE.md`
- `docs/ai/ACTIVE-SPRINT.md`
- `docs/ai/AGENT-OPERATING-BRIEF.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/decisions/*`
- `docs/phase-reports/PHASE-5.5-CLOSURE-REPORT.md`
- `docs/sprints/sprint-17/*`

Geri kalanların çok büyük kısmı archive repo’ya gidebilir.

---

## Final Recommendation

En iyi yol bu:

### Main repo
- code + current truth + active sprint + formal decisions

### Archive repo
- historical sprints + evidence + handoffs + review packets + resolved process/debt docs

### Hard rule
- Bir bilgi ya active truth’tur ya archive materyalidir.
- İkisi aynı anda olamaz.

Bu temizlik yapılmazsa repo büyüdükçe asıl maliyet storage değil, **yanlış karar verme** olur.
