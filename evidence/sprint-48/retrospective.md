# Sprint 48 Retrospective — Debt-First Hybrid

**Date:** 2026-03-31
**Model:** A (full closure)
**Class:** Governance + Runtime Contract + Data Normalization

---

## Key Questions (from plan)

### 1. open-items.md cleanup kaç resolved item ortaya çıkardı?
**4 item retired:** Backend restructure (D-115 superseded), UIOverview+WindowList (D-102 CONTEXT_ISOLATION done), D-102 criteria 3-8 (S40 covered), Jaeger deployment (docker-compose'da mevcut). 4 item güncellendi ve korundu.

### 2. Normalizer consolidation sonrası API response regression var mı?
**Hayır.** 96 API test (test_cost_api + test_api + test_e2e) tamamı geçti. `_load_file_missions()` cost_api ve dashboard_api'den kaldırıldı, normalizer.list_missions_enriched() ile değiştirildi. Aynı data shape korundu.

### 3. Field normalization frontend breaking change yarattı mı?
**Hayır.** Normalizer._build_stages() zaten dual-read yapıyordu (specialist/role, tool_call_count/toolCalls). API tarafında snake_case referans kalmadı. 217 frontend test değişiklik olmadan geçti.

### 4. D-133 contract B-107 implementation'a yeterli mi?
**Evet.** Input contract (policyContext + timeoutConfig + missionConfig + toolRequest) ve output contract (allow/deny/escalate/degrade) tanımlı. Default rules (WMCP degradation, risk escalation, timeout, budget) belirli. YAML rule format ve storage path frozen. S49'da code + API + tests eklenecek.

### 5. OTel attribute contract GenAI conventions ile ne kadar uyumlu?
**Kısmi.** 47 internal attribute ve 17 metric documented. GenAI Semantic Conventions (gen_ai.*) ile mapping tablosu oluşturuldu ama migration yapılmadı. Full migration S50+ carry-forward.

### 6. Local preflight developer adoption barrier var mı?
**Düşük.** `bash tools/preflight.sh` tek komut, 5 adım (ruff + tsc + OpenAPI drift + pytest + vitest). Pre-commit hook olarak OpenAPI drift eklendi (pre-push stage). Barrier: Windows'ta bash gerekiyor (Git Bash veya WSL).

---

## What Went Well

- **Cleanup gate etkili:** T-1 reconciliation 4 stale item temizledi, T-8 decision merge tek decision directory yarattı.
- **policyContext + timeout birlikte tasarlandı:** B-013 ve B-014 aynı commit'te, D-133 ile tutarlı input contract.
- **Normalizer consolidation clean:** Duplicate _load_file_missions kaldırıldı, 0 regression.
- **31 yeni test:** PolicyContext, TimeoutConfig, TIMED_OUT state, WMCP check, build_policy_context — hepsi covered.

## What Could Improve

- **G1/G2 gate'leri atlandı:** GPT cross-review mid-sprint ve final'de yapılmadı. Governance Rule 5 ihlali.
- **Preflight evidence geç oluşturuldu:** Sprint closure sırasında preflight-output.txt kaydedilmemişti.
- **OpenAPI regenerate gerekti:** Preflight çalışırken openapi.json güncellenince stage dirty olabilirdi.

## Concrete Actions

1. **S49'da G1/G2 gate'leri atlanmayacak** — GPT review mid-sprint zorunlu.
2. **Sprint closure checklist'e preflight evidence** adımı eklenmeli (Rule 16 amendment candidate).
3. **OpenAPI drift** pre-commit hook'u test edilmeli.

---

## Metrics

| Metric | Value |
|--------|-------|
| Tasks planned | 9 implementation + 4 gate/process |
| Tasks completed | 9/9 implementation |
| Gates completed | 0/2 (G1, G2 skipped) |
| Tests added | +31 backend |
| Test total | 966 (736+217+13) |
| Decisions frozen | 2 (D-131, D-133) + 1 deferred (D-132) |
| Commits | 7 implementation + 2 closure |
| Regressions | 0 |
| Blockers encountered | 0 |
