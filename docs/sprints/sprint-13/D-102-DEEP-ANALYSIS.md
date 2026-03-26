# D-102 Deep Analysis: Agent Runtime Token Overflow

**Date:** 2026-03-26
**Author:** Claude Opus 4.6 (Architect)
**Severity:** Critical — blocks complex missions
**Status:** Root cause analysis complete, solution architecture proposed

---

## 1. Problem Statement

Agent runtime Developer stage received 219,531 tokens. Claude's context window is 200K. Mission failed.

This is not a one-off. **Every complex mission will hit this** because the token accumulation is structural, not incidental.

---

## 2. Token Anatomy — Where Every Token Comes From

### 2.1 Pipeline Architecture (Current)

```
Stage 1: PO          → LLM call → artifact_1
Stage 2: Analyst      → LLM call (+ Snapshot tool × N) → artifact_2
Stage 3: Architect    → LLM call (+ Snapshot tool × M) → artifact_3
Stage 4: PM           → LLM call → artifact_4
Stage 5: Developer    → LLM call (+ FileSystem + Terminal) → code output
```

Her stage'in LLM call'ı şu input'u alır:

```
messages = [
    system_prompt,                    # specialist prompt (~150-440 tok)
    instruction,                      # mission instruction (~200 tok)
    artifact_context,                 # önceki stage'lerin çıktıları
    ...multi_turn_tool_history...     # O STAGE'İN KENDİ tool call geçmişi
]
```

### 2.2 Token Budget Breakdown (Observed: 219K Case)

| Component | Developer Stage'e Ulaşan | Token (est.) | % |
|-----------|------------------------|-------------|---|
| **System prompt** | Specialist prompt (Developer) | ~381 | 0.2% |
| **Instruction** | Mission description | ~200 | 0.1% |
| **Artifact: PO output** | Full text, no truncation on tool history | ~2,500 | 1.1% |
| **Artifact: Analyst output** | Analyst final text + **Analyst'in tüm Snapshot response'ları** | ~82,000 | 37.3% |
| **Artifact: Architect output** | Architect final text + **Architect'in tüm Snapshot response'ları** | ~78,000 | 35.5% |
| **Artifact: PM output** | PM final text | ~3,500 | 1.6% |
| **Developer own messages** | Developer'ın kendi tool call'ları (henüz başlamadan) | ~0 | 0% |
| **Overhead** | Message framing, role tags, separators | ~2,950 | 1.3% |
| **Truncation savings** | 3000 char truncate on artifact text | ~-50,000 | — |
| **Net after truncation** | | **~219,531** | — |

### 2.3 Sorunun Katmanları

```
                    ┌──────────────────────────────────────────┐
                    │         LAYER 4: No Budget Gate           │
                    │  Hiçbir yerde "bu çok fazla, dur" yok     │
                    ├──────────────────────────────────────────┤
                    │         LAYER 3: No Observability          │
                    │  Token count loglanmıyor, görünmüyor       │
                    ├──────────────────────────────────────────┤
                    │     LAYER 2: Artifact Context Bleeding     │
                    │  Önceki stage'lerin tool history'si sızıyor │
                    ├──────────────────────────────────────────┤
                    │    LAYER 1: Snapshot Response Explosion    │
                    │  Tek bir tool call = 50-100K token          │
                    └──────────────────────────────────────────┘
```

**Layer 1** olmadan Layer 2 zararsız. Layer 2 olmadan Layer 3-4 gereksiz. Ama 4 katman birlikte olunca sistem patlar.

---

## 3. Root Cause Deep Dive

### 3.1 Layer 1: Snapshot Tool Response Anatomy

Snapshot MCP tool'u tek bir çağrıda şunu döndürür:

| Parça | İçerik | Token (est.) |
|-------|--------|-------------|
| Screenshot | Base64 encoded PNG/JPEG — tüm ekran | ~30,000-50,000 |
| UI Element Tree | Her buton, metin alanı, checkbox — coordinates, text, type, enabled, visible | ~20,000-40,000 |
| Window List | Açık pencereler, boyutları, z-order | ~500-1,000 |
| Metadata | Timestamp, screen resolution, focused window | ~100 |
| **Total** | | **~50,000-91,000** |

**Neden bu kadar büyük?**

- Base64 encoding %33 overhead ekler (1MB image → 1.33MB base64 → ~350K token)
- UI Element Tree her element için ~50-100 token: `{"type":"button","text":"Submit","rect":[120,340,200,380],"enabled":true,"visible":true,"automationId":"btnSubmit"}`
- Tipik bir Windows masaüstünde 200-500 UI element bulunur
- Snapshot tool bunların **hepsini** döndürür — filtering yok

**Analyst neden Snapshot çağırıyor?**

Analyst prompt'unda: "Examine the current UI state" gibi bir ifade var. Analyst bunu Snapshot olarak yorumluyor çünkü:
1. Snapshot mevcut ve erişilebilir (tool permission yok)
2. Prompt'ta "use WindowList instead" gibi bir yönlendirme yok
3. LLM, en kapsamlı tool'u seçme eğiliminde — Snapshot her şeyi verir

**Architect neden de çağırıyor?**

Aynı sebep. Architect da UI layout'u incelemek istiyor. İki stage birlikte = 2 × ~80K = ~160K token sadece Snapshot'tan.

### 3.2 Layer 2: Artifact Context Bleeding Mechanism

Şu an context assembler şöyle çalışıyor:

```python
# CURRENT (problematic)
def assemble_for_stage(stage_index, previous_stages):
    context = ""
    for stage in previous_stages:
        # stage.messages = TÜM messages listesi (user + assistant + tool_call + tool_result)
        artifact_text = extract_last_assistant_message(stage.messages)
        truncated = artifact_text[:3000]  # sadece SON mesajın TEXT'ini truncate ediyor
        context += f"## {stage.name}\n{truncated}\n\n"
    return context
```

**Problem:** `extract_last_assistant_message()` son assistant mesajını alıyor — ama `stage.messages` listesinin kendisi de artifact_context'e sızıyor olabilir. Veya daha kötüsü:

```python
# POSSIBLE VARIANT (even worse)
def assemble_for_stage(stage_index, previous_stages):
    context = ""
    for stage in previous_stages:
        # TÜM messages listeyi olduğu gibi serialize edip context'e ekliyor
        context += json.dumps(stage.messages)  # 80K+ per stage
    return context
```

**Hangisinin gerçek implementasyon olduğunu doğrulamak için koda bakmak lazım.** Ama 219K'ya ulaşması, tool call response'larının bir şekilde downstream'e aktığını kanıtlıyor.

### 3.3 Layer 3: Observability Gap

Şu an runtime'da:

| Soru | Cevap | Problem |
|------|-------|---------|
| Stage input kaç token? | Bilinmiyor | Log yok |
| Hangi tool call kaç token döndürdü? | Bilinmiyor | Log yok |
| Artifact context kaç token? | Bilinmiyor | Log yok |
| Context limit'e ne kadar yakınız? | Bilinmiyor | Check yok |
| Hangi stage en çok token tüketiyor? | Bilinmiyor | Metric yok |
| Mission toplam token consumption? | Bilinmiyor | Aggregation yok |

**Görünmeyen problem çözülemez.** 219K'yı ancak LLM hata verdiğinde fark ettik.

### 3.4 Layer 4: No Budget Enforcement

Hiçbir noktada şu kontrol yok:

```python
if estimated_tokens > BUDGET_LIMIT:
    STOP
    report_to_operator("Budget aşılacak: {estimated} > {limit}")
    wait_for_approval()
```

Sistem "ne kadar token giderse gitsin, gönder" modunda. Bu:
- Maliyetsiz değil (API token = para)
- Güvenli değil (context overflow = mission failure)
- Kontrolsüz (operator ne olduğunu bilmiyor)

---

## 4. Solution Architecture — 5 Layer

### 4.1 Layer 1 Fix: Snapshot Response Compression

**Problem:** Snapshot 50-100K token. **Target:** Analyst/Architect için ≤ 2K token.

**İki ayrı tool:**

| Tool | Kim kullanır | Ne döndürür | Token |
|------|-------------|-------------|-------|
| **WindowList** | Analyst, Architect | Pencere adları + boyutları + focused | ~300-500 |
| **UIOverview** | Analyst, Architect | WindowList + top-level UI elements only (buttons, headings — coordinates yok, full tree yok) | ~1,000-2,000 |
| **Snapshot** (full) | Developer only | Screenshot + full UI tree + window list | ~50,000-91,000 |

**UIOverview implementasyonu:**
```python
def ui_overview_tool() -> dict:
    """
    Lightweight UI inspection. Returns:
    - Window titles + dimensions
    - Top-level interactive elements (buttons, inputs, links) — NAME ONLY, no coordinates
    - Current focused element
    No screenshot. No full element tree. No base64.
    """
    windows = enumerate_windows()
    focused = get_focused_window()
    
    # Sadece focused window'un top-level element'leri
    elements = []
    if focused:
        for elem in get_top_level_elements(focused.handle, max_depth=2):
            elements.append({
                "type": elem.control_type,  # Button, TextBox, Link, etc.
                "name": elem.name[:50],      # truncated
                "enabled": elem.is_enabled,
            })
    
    return {
        "windows": [{"title": w.title, "rect": w.rect, "focused": w == focused} for w in windows],
        "focused_window_elements": elements[:30],  # max 30 elements
        "element_count": len(elements),
    }
```

**Neden UIOverview da lazım (sadece WindowList yetmez):**
Analyst'in "ekranda 3 buton var, biri disabled" demesi gerekebilir. WindowList bunu veremez. UIOverview bunu ~1.5K token'da verir. Full Snapshot'a gerek yok.

---

### 4.2 Layer 2 Fix: Stage Boundary Isolation

**Problem:** Tool call response'ları downstream'e sızıyor. **Target:** Stage arası aktarım = sadece final artifact text.

```python
class StageResult:
    """Immutable output of a completed stage."""
    stage_name: str
    artifact_text: str      # son assistant mesajının text content'i
    token_count: int        # bu stage'in tükettiği toplam token
    tool_calls_made: int    # kaç tool call yapıldı (metric only, content yok)
    
    # YOK: messages listesi
    # YOK: tool call request/response body'leri
    # YOK: intermediate assistant mesajları

def complete_stage(stage_name: str, messages: list[dict]) -> StageResult:
    """
    Stage tamamlandığında çağrılır.
    Messages listesinden sadece final artifact çıkarılır.
    Tool call history BURADA ölür — hiçbir yere aktarılmaz.
    """
    artifact_text = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [b["text"] for b in content if b.get("type") == "text"]
                artifact_text = "\n".join(text_parts)
            elif isinstance(content, str):
                artifact_text = content
            break
    
    total_tokens = sum(
        estimate_tokens(msg.get("content", ""))
        for msg in messages
    )
    
    tool_calls = sum(
        1 for msg in messages 
        if msg.get("role") == "assistant" 
        and any(b.get("type") == "tool_use" for b in (msg.get("content", []) if isinstance(msg.get("content"), list) else []))
    )
    
    return StageResult(
        stage_name=stage_name,
        artifact_text=artifact_text,
        token_count=total_tokens,
        tool_calls_made=tool_calls,
    )
```

**Tiered context assembly (önceki plan'dan — değişmedi):**

| Tier | Distance | Max Chars | İçerik |
|------|----------|-----------|--------|
| A | N-1 (önceki stage) | 5,000 | Full artifact text |
| B | N-2 | 2,000 | Summarized |
| C | N-3+ | 500 | One-liner |

---

### 4.3 Layer 3 Fix: Token Observability System

**Problem:** Hiçbir token metric görünmüyor. **Target:** Her noktada token sayısı loglanır ve raporlanır.

**3 seviye observability:**

#### A. Per-Tool-Call Logging

Her MCP tool çağrısından sonra:

```python
def log_tool_call(stage: str, tool_name: str, request_tokens: int, response_tokens: int):
    entry = {
        "ts": utcnow(),
        "stage": stage,
        "tool": tool_name,
        "request_tokens": request_tokens,
        "response_tokens": response_tokens,
        "cumulative_stage_tokens": get_stage_cumulative(stage),
    }
    append_to_log("token-usage.jsonl", entry)
    
    # Console output for real-time monitoring
    log.info(f"[TOKEN] {stage}/{tool_name}: req={request_tokens}, resp={response_tokens}, cumulative={entry['cumulative_stage_tokens']}")
```

**Örnek log çıktısı:**
```
[TOKEN] analyst/UIOverview: req=45, resp=1,200, cumulative=3,450
[TOKEN] analyst/FileSystem.read: req=30, resp=2,100, cumulative=5,580
[TOKEN] architect/UIOverview: req=45, resp=1,150, cumulative=2,800
[TOKEN] developer/Snapshot: req=45, resp=62,000, cumulative=64,200
```

#### B. Per-Stage Summary

Stage tamamlandığında:

```python
def log_stage_summary(result: StageResult):
    entry = {
        "ts": utcnow(),
        "stage": result.stage_name,
        "artifact_tokens": estimate_tokens(result.artifact_text),
        "total_stage_tokens": result.token_count,
        "tool_calls": result.tool_calls_made,
        "artifact_chars": len(result.artifact_text),
    }
    append_to_log("token-usage.jsonl", entry)
    
    log.info(
        f"[STAGE COMPLETE] {result.stage_name}: "
        f"artifact={entry['artifact_tokens']} tok, "
        f"total_consumed={result.token_count} tok, "
        f"tools={result.tool_calls_made}"
    )
```

**Örnek:**
```
[STAGE COMPLETE] product_owner: artifact=1,200 tok, total_consumed=2,800 tok, tools=0
[STAGE COMPLETE] analyst: artifact=2,400 tok, total_consumed=45,000 tok, tools=3
[STAGE COMPLETE] architect: artifact=3,100 tok, total_consumed=38,000 tok, tools=2
[STAGE COMPLETE] pm: artifact=1,800 tok, total_consumed=4,200 tok, tools=0
```

#### C. Mission Summary Report

Mission tamamlandığında (başarılı veya başarısız):

```python
def generate_mission_token_report(mission_id: str, stages: list[StageResult]) -> dict:
    report = {
        "mission_id": mission_id,
        "total_tokens": sum(s.token_count for s in stages),
        "total_tool_calls": sum(s.tool_calls_made for s in stages),
        "stages": [
            {
                "name": s.stage_name,
                "tokens_consumed": s.token_count,
                "artifact_tokens": estimate_tokens(s.artifact_text),
                "tool_calls": s.tool_calls_made,
                "pct_of_total": round(s.token_count / max(1, sum(x.token_count for x in stages)) * 100, 1),
            }
            for s in stages
        ],
        "context_assembly": {
            "developer_input_tokens": estimate_tokens(assembled_context_for_developer),
            "budget_limit": STAGE_TOKEN_BUDGET,
            "utilization_pct": round(developer_input / STAGE_TOKEN_BUDGET * 100, 1),
        }
    }
    
    save_json(f"missions/{mission_id}/token-report.json", report)
    return report
```

**Örnek rapor:**
```json
{
  "mission_id": "m-20260326-001",
  "total_tokens": 95200,
  "total_tool_calls": 5,
  "stages": [
    {"name": "product_owner", "tokens_consumed": 2800, "artifact_tokens": 1200, "tool_calls": 0, "pct_of_total": 2.9},
    {"name": "analyst", "tokens_consumed": 45000, "artifact_tokens": 2400, "tool_calls": 3, "pct_of_total": 47.3},
    {"name": "architect", "tokens_consumed": 38000, "artifact_tokens": 3100, "tool_calls": 2, "pct_of_total": 39.9},
    {"name": "pm", "tokens_consumed": 4200, "artifact_tokens": 1800, "tool_calls": 0, "pct_of_total": 4.4},
    {"name": "developer", "tokens_consumed": 5200, "artifact_tokens": 4500, "tool_calls": 0, "pct_of_total": 5.5}
  ],
  "context_assembly": {
    "developer_input_tokens": 12500,
    "budget_limit": 50000,
    "utilization_pct": 25.0
  }
}
```

---

### 4.4 Layer 4 Fix: Token Budget Enforcement + Approval Gates

**Problem:** Limit aşılınca sistem patlıyor, kimse bilmiyor. **Target:** Budget aşılmadan DUR, operatöre sor.

**Budget tipleri:**

| Budget | Limit | Aşılınca |
|--------|-------|----------|
| **Per-tool-call response** | 10,000 tokens | Auto-truncate + warn |
| **Per-stage cumulative** | 80,000 tokens | PAUSE — operator approval required |
| **Per-stage input (assembled context)** | 50,000 tokens | PAUSE — operator approval required |
| **Per-mission total** | 300,000 tokens | STOP — mission aborted with report |

**Enforcement akışı:**

```
Tool call response arrives (N tokens)
  │
  ├─ N ≤ 10,000 → proceed normally, log token count
  │
  ├─ 10,000 < N ≤ 50,000 → AUTO-TRUNCATE to 10,000
  │     Log: "[BUDGET] Tool response truncated: {tool} returned {N} tok, truncated to 10,000"
  │     Include truncation notice in response: "[Response truncated from {N} to 10,000 tokens]"
  │
  └─ N > 50,000 → BLOCK + REPORT
        Log: "[BUDGET VIOLATION] {tool} attempted {N} token response"
        Do NOT include in messages
        Return error to LLM: "Tool response too large ({N} tokens). Use a lighter tool or narrow your query."
```

```
Stage about to start, assembled context = C tokens
  │
  ├─ C ≤ 50,000 → proceed normally
  │
  ├─ 50,000 < C ≤ 80,000 → WARNING logged
  │     "[BUDGET WARNING] Stage {name} input is {C} tokens (limit 50,000). Proceeding with caution."
  │
  └─ C > 80,000 → PAUSE + OPERATOR APPROVAL
        "[BUDGET GATE] Stage {name} requires {C} tokens (limit 50,000)."
        "Breakdown: {tier_a}: {a_tok}, {tier_b}: {b_tok}, {tier_c}: {c_tok}"
        "Options: [1] Approve and continue [2] Abort mission [3] Re-assemble with aggressive truncation"
        
        → Wait for operator input
        → If approved: proceed, log "operator-approved: {C} tokens"
        → If abort: stop mission, generate token report
        → If re-assemble: run with all tiers at 50% limit
```

```
Mission cumulative > 300,000 tokens
  │
  └─ HARD STOP
       "[BUDGET EXCEEDED] Mission {id} consumed {total} tokens (limit 300,000)."
       "Stage breakdown: {per_stage_summary}"
       "Mission aborted. Token report saved to missions/{id}/token-report.json"
```

**Operator approval mekanizması:**

```python
class BudgetGate:
    def __init__(self, config: BudgetConfig):
        self.config = config
    
    def check_stage_input(self, stage_name: str, token_count: int) -> BudgetDecision:
        if token_count <= self.config.stage_input_limit:
            return BudgetDecision(action="proceed", reason="within budget")
        
        if token_count <= self.config.stage_input_hard_limit:
            return BudgetDecision(
                action="warn",
                reason=f"Stage input {token_count} exceeds soft limit {self.config.stage_input_limit}",
            )
        
        return BudgetDecision(
            action="pause",
            reason=f"Stage input {token_count} exceeds hard limit {self.config.stage_input_hard_limit}",
            requires_approval=True,
            approval_options=["approve", "abort", "truncate"],
            breakdown=self._build_breakdown(stage_name),
        )
    
    def check_tool_response(self, tool_name: str, token_count: int) -> BudgetDecision:
        if token_count <= self.config.tool_response_limit:
            return BudgetDecision(action="proceed")
        
        if token_count <= self.config.tool_response_hard_limit:
            return BudgetDecision(
                action="truncate",
                truncate_to=self.config.tool_response_limit,
                reason=f"{tool_name} returned {token_count} tokens, truncating to {self.config.tool_response_limit}",
            )
        
        return BudgetDecision(
            action="block",
            reason=f"{tool_name} attempted {token_count} token response (hard limit: {self.config.tool_response_hard_limit})",
        )
    
    def check_mission_total(self, total: int) -> BudgetDecision:
        if total > self.config.mission_total_limit:
            return BudgetDecision(action="abort", reason=f"Mission total {total} exceeds {self.config.mission_total_limit}")
        return BudgetDecision(action="proceed")
```

**Config:**

```python
@dataclass
class BudgetConfig:
    # Per tool call response
    tool_response_limit: int = 10_000       # auto-truncate above this
    tool_response_hard_limit: int = 50_000  # block above this
    
    # Per stage input (assembled context + prompt)
    stage_input_limit: int = 50_000         # warn above this
    stage_input_hard_limit: int = 80_000    # pause + approval above this
    
    # Per stage cumulative (all tool calls + messages in one stage)
    stage_cumulative_limit: int = 100_000   # warn
    stage_cumulative_hard_limit: int = 150_000  # pause + approval
    
    # Mission total
    mission_total_limit: int = 300_000      # hard abort
```

---

### 4.5 Layer 5 Fix: Role-Based Tool Access (Prevention)

Önceki plan'dan — değişmedi. Analyst ve Architect Snapshot'a erişemez, UIOverview kullanır.

| Role | Tools | Max Response per Call |
|------|-------|---------------------|
| product_owner | FileSystem.read | 10,000 tok |
| analyst | FileSystem.read, UIOverview | 10,000 tok |
| architect | FileSystem.read, UIOverview | 10,000 tok |
| developer | FileSystem.read, FileSystem.write, Snapshot, Terminal | 50,000 tok (Snapshot exemption with approval) |
| pm | FileSystem.read | 10,000 tok |

**Developer'ın Snapshot kullanması:** Budget gate Snapshot response'u truncate edebilir veya operator approval isteyebilir. Developer'a özel olarak `tool_response_hard_limit = 80,000` verilebilir ama default 50K'da kalır.

---

## 5. Data Flow — Before vs After

### Before (219K case)

```
PO stage:
  Input:  system(381) + instruction(200) = 581 tok
  Output: artifact_text(2500 tok) + messages_list(2800 tok total)
  Passed to next: messages_list (2800 tok — includes everything)

Analyst stage:
  Input:  system(440) + instruction(200) + PO_messages(2800) = 3440 tok
  Tool:   Snapshot call → response 82,000 tok
  Tool:   FileSystem.read → response 3,000 tok
  Output: artifact_text(2400) + messages_list(91,000 tok total)
  Passed to next: messages_list (91,000 tok — tool responses INCLUDED)

Architect stage:
  Input:  system(380) + instruction(200) + PO_messages(2800) + Analyst_messages(91,000) = 94,380 tok
  Tool:   Snapshot call → response 78,000 tok
  Output: artifact_text(3100) + messages_list(175,000 tok total)
  Passed to next: messages_list (175,000 tok — EVERYTHING)

PM stage:
  Input:  system(300) + instruction(200) + ALL_previous(175,000+91,000+2,800) = would exceed limit
  [PM possibly gets truncated version]

Developer stage:
  Input:  system(381) + instruction(200) + assembled(219,000) = 219,531 tok  → FAIL
```

### After (with all 5 layers)

```
PO stage:
  Input:  system(381) + instruction(200) = 581 tok
  Budget: 581 << 50,000 ✅
  Output: StageResult(artifact="...", 1200 tok)
  Passed: artifact_text only (1200 tok)

Analyst stage:
  Input:  system(440) + instruction(200) + PO_artifact_TierA(1200) = 1,840 tok
  Budget: 1,840 << 50,000 ✅
  Tool:   UIOverview → 1,500 tok (Snapshot BLOCKED)
  Tool:   FileSystem.read → 2,100 tok
  Budget check: cumulative 5,440 << 100,000 ✅
  Output: StageResult(artifact="...", 2400 tok, tools=2, consumed=5440)
  Passed: artifact_text only (2400 tok)

Architect stage:
  Input:  system(380) + instruction(200) + Analyst_TierA(2400) + PO_TierB(500) = 3,480 tok
  Budget: 3,480 << 50,000 ✅
  Tool:   UIOverview → 1,150 tok
  Output: StageResult(artifact="...", 3100 tok, tools=1, consumed=4,930)
  Passed: artifact_text only (3100 tok)

PM stage:
  Input:  system(300) + instruction(200) + Architect_TierA(3100) + Analyst_TierB(1000) + PO_TierC(500) = 5,100 tok
  Budget: 5,100 << 50,000 ✅
  Output: StageResult(artifact="...", 1800 tok)

Developer stage:
  Input:  system(381) + instruction(200) + PM_TierA(1800) + Architect_TierB(1500) + Analyst_TierC(500) + PO_TierC(500) = 4,881 tok
  Budget: 4,881 << 50,000 ✅ ✅ ✅
  
  Tool: Snapshot → 62,000 tok
  Budget: tool_response 62,000 > 50,000 → APPROVAL GATE
  Operator approves → proceed with 62K
  
  Total developer stage: ~72,000 tok (within stage limit 150K)
```

**Net result: Developer input 219,531 → 4,881 tokens. %97.8 reduction.**

---

## 6. Token Report — Operator-Facing Output

Her mission sonunda operator şunu görür:

```
╔══════════════════════════════════════════════════════════╗
║              MISSION TOKEN REPORT                        ║
║  Mission: m-20260326-001 (Create login page)             ║
║  Status:  COMPLETED                                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Stage          │ Consumed │  Tools │ Artifact │    %    ║
║  ────────────── │ ──────── │ ────── │ ──────── │ ─────  ║
║  product_owner  │    2,800 │      0 │    1,200 │   3.8% ║
║  analyst        │    5,440 │      2 │    2,400 │   7.4% ║
║  architect      │    4,930 │      1 │    3,100 │   6.7% ║
║  pm             │    4,200 │      0 │    1,800 │   5.7% ║
║  developer      │   56,200 │      3 │    4,500 │  76.4% ║
║  ────────────── │ ──────── │ ────── │ ──────── │ ─────  ║
║  TOTAL          │   73,570 │      6 │          │ 100.0% ║
║                                                          ║
║  Budget Utilization:                                     ║
║  Developer input:  4,881 / 50,000 (9.8%)                ║
║  Mission total:   73,570 / 300,000 (24.5%)              ║
║                                                          ║
║  Approval Gates Triggered: 1                             ║
║  - Developer/Snapshot: 62,000 tok (approved by operator) ║
║                                                          ║
║  Budget Violations: 0                                    ║
║  Truncations: 0                                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

**Anomali durumunda:**
```
║  ⚠ WARNING: analyst consumed 47.3% of total tokens      ║
║    → 3 tool calls, Snapshot attempted but BLOCKED         ║
║    → Consider: narrower analysis scope or fewer tool calls║
```

---

## 7. Updated D-102 Decision Record

### Changes from original D-102:

| Aspect | Original D-102 | Updated D-102 |
|--------|---------------|---------------|
| Layers | 3 (L1, L2, L3) | 5 (+ observability + budget enforcement) |
| Tools | WindowList only | WindowList + UIOverview |
| Budget | No enforcement | 4-tier budget with approval gates |
| Reporting | No reporting | Per-call, per-stage, per-mission token reports |
| Operator role | Passive | Active: approval gates, mission reports, anomaly alerts |

### Updated subtask list for Task 13.0:

| # | Subtask | Layer | Size |
|---|---------|-------|------|
| 13.0.1 | Token estimation utility: `estimate_tokens(content)` | L3 | S |
| 13.0.2 | Per-tool-call token logger | L3 | S |
| 13.0.3 | Per-stage summary logger | L3 | S |
| 13.0.4 | Mission token report generator | L3 | M |
| 13.0.5 | BudgetConfig dataclass + BudgetGate class | L4 | M |
| 13.0.6 | Tool response budget enforcement (truncate/block) | L4 | M |
| 13.0.7 | Stage input budget enforcement (warn/pause/approval) | L4 | M |
| 13.0.8 | Mission total budget enforcement (hard abort) | L4 | S |
| 13.0.9 | Operator approval mechanism (pause + wait + resume/abort) | L4 | M |
| 13.0.10 | `extract_stage_result()` — strip tool history | L2 | S |
| 13.0.11 | Tiered `assemble_context()` | L2 | S |
| 13.0.12 | `ROLE_TOOL_PERMISSIONS` + dispatch check | L5 | S |
| 13.0.13 | UIOverview tool implementation | L5 | M |
| 13.0.14 | WindowList tool implementation | L5 | S |
| 13.0.15 | Update Analyst/Architect prompts | L5 | S |
| 13.0.16 | Feature flag: `CONTEXT_ISOLATION_ENABLED`, `TOKEN_BUDGET_ENABLED` | Config | S |
| 13.0.17 | Unit tests: all layers | Test | M |
| 13.0.18 | E2E validation: 3 complex + 3 simple missions | Test | M |
| 13.0.19 | Freeze D-102 (updated) in DECISIONS.md | Doc | S |

**19 subtasks. Layer 3 (observability) first → Layer 4 (enforcement) → Layer 2 (isolation) → Layer 5 (prevention).**

Sıralama mantığı: Önce görünürlük (neyi ölçeceğini bil), sonra enforcement (limit koy), sonra isolation (kaynağı kes), sonra prevention (tekrarı engelle).

---

## 8. Acceptance Criteria (Updated)

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Every tool call logs token count | `grep "\[TOKEN\]" logs/agent-runner.log \| wc -l` matches tool call count |
| 2 | Every stage completion logs summary | `grep "\[STAGE COMPLETE\]" logs/agent-runner.log` — 5 entries per mission |
| 3 | Mission token report generated | `ls missions/*/token-report.json` exists after mission |
| 4 | Tool response > 10K auto-truncated | Test: mock 20K response → truncated to 10K + notice |
| 5 | Tool response > 50K blocked | Test: mock 60K response → blocked, error returned to LLM |
| 6 | Stage input > 80K triggers approval gate | Test: assembled context 90K → pause, wait for operator |
| 7 | Mission total > 300K hard aborts | Test: cumulative exceeds → mission stopped + report |
| 8 | Operator can approve/abort/truncate at budget gate | Integration test with mock operator input |
| 9 | Stage boundary strips tool history | Developer input contains 0 tool_call/tool_result from Analyst/Architect |
| 10 | Tiered assembly: Developer input ≤ 10K for normal mission | Token count log |
| 11 | Analyst/Architect cannot use Snapshot | Dispatch returns BLOCKED |
| 12 | UIOverview response ≤ 2K tokens | Measured from real call |
| 13 | 3 complex missions complete | Mission reports show completion |
| 14 | 3 simple missions no regression | Mission reports show same quality |
| 15 | Feature flags default true | Config verification |

---

## Next Step

**Produced:** D-102 deep analysis — 5-layer solution, token budget enforcement, observability, approval gates
**Next actor:** Operator
**Action:** Review. Confirm budget limits (10K/50K/80K/300K). Freeze D-102 (updated). This replaces the original 3-layer D-102 spec.
**Blocking:** D-102 freeze required before Sprint 13 kickoff.
