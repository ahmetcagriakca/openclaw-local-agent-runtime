# Sprint-End Documentation Policy (D-077)

**Date:** 2026-03-25
**Status:** FROZEN
**Enforce:** `tools/validate_sprint_docs.py`

---

## Kural

Sprint "done" sayılmadan önce aşağıdaki dökümanlar güncellenmiş olmalı.
Validation script tüm kontrolleri çalıştırır ve FAIL olan varsa sprint kapanmaz.

## Zorunlu Döküman Matrisi

| # | Dosya | Güncelleme Kuralı |
|---|-------|-------------------|
| D1 | `docs/ai/STATE.md` | Aktif phase, sprint no, component status, test count |
| D2 | `docs/ai/NEXT.md` | Sonraki sprint/task bilgisi |
| D3 | `docs/ai/DECISIONS.md` | Sprint'te alınan D-XXX kararları |
| D4 | `docs/ai/BACKLOG.md` | Tamamlanan B-XXX, yeni item'lar |
| D5 | `docs/ai/PROTOCOL.md` | Süreç değişikliği varsa güncel |
| D6 | `SESSION-HANDOFF.md` | Sprint snapshot: durum, kararlar, sonraki adım |
| D7 | `config/capabilities.json` | Auto-generated (elle güncelleme YASAK) |
| D8 | Sprint plan doc | Çıkış kriterleri checklist doldurulmuş |

## Çalıştırma

```bash
python tools/validate_sprint_docs.py --sprint N --sprint-date YYYY-MM-DD
```

Exit code 0 = sprint kapanabilir. Exit code 1 = sprint kapanmaz.

## Sprint Kapanış Workflow

1. Tüm code task'ları tamamla
2. `validate_sprint_docs.py` çalıştır
3. FAIL varsa → düzelt, tekrar çalıştır
4. 0 FAIL → rapor oluştur → commit → push

---

*Sprint-End Doc Policy — OpenClaw (D-077)*
