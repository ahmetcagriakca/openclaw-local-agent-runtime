# Chat Bridge — Complete Requirements Document

## Proje Amacı

Claude Code'un ChatGPT ve Claude.ai chat arayüzleriyle Playwright üzerinden programatik iletişim kurmasını sağlayan headless bridge tool.

Mevcut problem: Chrome MCP extension sürekli kopuyor, her review döngüsünde 5-10 dakika kaybediliyor.
Hedef: Stabil, scriptable, JSON-in/JSON-out iletişim.

---

## 1. Core Flow

```
Claude Code
  → bash: node bridge.js --target gpt --message "pr 94 hazır"
    → Playwright headless Chromium açar
    → Persistent session ile login'siz girer
    → Chat'e mesaj yazar, Enter'a basar
    → Response tamamlanana kadar DOM'u poll eder
    → JSON stdout: { response, chatUrl, verdict, durationMs }
  → Claude Code response'u parse eder
```

---

## 2. Target Destinations

### 2a. ChatGPT — Custom GPT Projesi

**KRİTİK:** Bridge, random bir ChatGPT chat'i değil, belirli bir Custom GPT projesini hedefler.

Konfigürasyon (`~/.chat-bridge/config.json`):
```json
{
  "gpt": {
    "baseUrl": "https://chatgpt.com",
    "projectUrl": "https://chatgpt.com/g/g-p-69c05848f5cc819196f2e353529d45f6-vezir",
    "newChatUrl": "https://chatgpt.com/g/g-p-69c05848f5cc819196f2e353529d45f6-vezir",
    "model": "gpt-4o",
    "sessionDir": "~/.chat-bridge/sessions/gpt"
  },
  "claude": {
    "baseUrl": "https://claude.ai",
    "projectUrl": null,
    "newChatUrl": "https://claude.ai/new",
    "sessionDir": "~/.chat-bridge/sessions/claude"
  }
}
```

**Davranış:**
- `--target gpt` → `config.gpt.projectUrl`'e gider (Custom GPT projesi)
- `--target gpt --chat-url URL` → belirli bir chat'e devam eder
- `--target gpt --new-chat` → Custom GPT projesi içinde yeni chat açar (projectUrl kullanır)
- config.json'da projectUrl tanımlıysa, her yeni chat o proje altında açılır
- projectUrl null ise standart ChatGPT chat kullanılır

### 2b. Claude.ai

- `--target claude` → claude.ai'de yeni chat
- `--target claude --project-url URL` → belirli bir proje
- `--target claude --chat-url URL` → mevcut chat'e devam

---

## 3. Session Management

### 3a. Setup (ilk kez)

```bash
node bridge.js --setup gpt      # headed browser açılır, login ol, ENTER bas
node bridge.js --setup claude    # aynı
```

- Headed Chromium açar
- Kullanıcı login olur
- Session cookie'leri `~/.chat-bridge/sessions/{target}/` altına kaydedilir
- Persistent browser context kullanılır — her çağrıda re-login yok

### 3b. Session Lifecycle

- Cookie süresi dolduğunda `--setup` tekrar çalıştırılır
- `--health` komutu session durumunu kontrol eder
- Login expired ise screenshot alınır ve hata döner

---

## 4. Komutlar

### 4a. Mesaj Gönder (core)

```bash
node bridge.js --target gpt --message "pr 94 hazır"
node bridge.js --target gpt --chat-url URL --message "re-review please"
node bridge.js --target gpt --new-chat --message "Sprint 22 plan.yaml oluştur"
```

Çıktı (stdout, sadece JSON):
```json
{
  "ok": true,
  "target": "gpt",
  "chatUrl": "https://chatgpt.com/g/g-p-.../c/abc123",
  "response": "Sprint 22 için...",
  "truncated": false,
  "durationMs": 45200,
  "timestamp": "2026-03-28T01:23:45Z"
}
```

### 4b. Health Check

```bash
node bridge.js --health gpt
node bridge.js --health claude
node bridge.js --health all
```

Kontroller:
1. Session dosyası var mı
2. Browser context açılıyor mu
3. Hedef siteye navigate edilebiliyor mu
4. Login durumu (chat input selector visible mı)
5. Selector'lar hala valid mi

Çıktı:
```json
{
  "target": "gpt",
  "session": true,
  "loginValid": true,
  "selectorsValid": true,
  "status": "healthy"
}
```

Hata:
```json
{
  "target": "gpt",
  "session": true,
  "loginValid": false,
  "status": "unhealthy",
  "error": "Login expired",
  "screenshotPath": "/home/user/.chat-bridge/screenshots/gpt-health-2026-03-28T01-23-45.png"
}
```

### 4c. Verdict Extraction

```bash
node bridge.js --target gpt --chat-url URL --message "pr 94 hazır" --extract-verdict
```

Response'tan GPT review verdict parse eder:

Parse kuralları:
- `2. Verdict` başlığı altındaki ilk PASS veya HOLD
- `6. Blocking findings` altındaki B1, B2, ... satırları
- `7. Required patch set` altındaki P1, P2, ... satırları
- `3. Closure eligibility` altında "eligible" veya "not eligible" arar

Ek JSON alanları:
```json
{
  "response": "...",
  "verdict": "HOLD",
  "blockers": ["B1 — Final review metni...", "B2 — ..."],
  "patches": ["P1 — ...", "P2 — ..."],
  "closureEligible": false
}
```

verdict bulunamazsa: `"verdict": null, "parseError": "Verdict pattern not found"`

### 4d. Conversation Export

```bash
node bridge.js --export --target gpt --chat-url URL
```

Chat sayfasındaki tüm mesajları DOM'dan çeker:

```json
{
  "chatUrl": "...",
  "target": "gpt",
  "exportedAt": "2026-03-28T...",
  "messageCount": 24,
  "messages": [
    {"role": "user", "content": "pr 77 hazır", "index": 0},
    {"role": "assistant", "content": "PR77'yi açıyorum...", "index": 1}
  ]
}
```

### 4e. Setup

```bash
node bridge.js --setup gpt       # headed browser, login, session kaydet
node bridge.js --setup claude
```

---

## 5. Selectors (selectors.json)

Ayrı dosya — UI güncellendiğinde sadece selector'lar değişir, kod değişmez.

Her selector'ın primary + fallback versiyonu var.

```json
{
  "gpt": {
    "chatInput": {
      "primary": "[id='prompt-textarea']",
      "fallback": "textarea[placeholder*='Message']"
    },
    "sendButton": {
      "primary": "button[data-testid='send-button']",
      "fallback": "button[aria-label='Send']"
    },
    "responseContainer": {
      "primary": "[data-message-author-role='assistant']",
      "fallback": ".markdown.prose"
    },
    "lastResponse": {
      "primary": "[data-message-author-role='assistant']:last-child",
      "fallback": ".group\\/conversation-turn:last-child .markdown"
    },
    "thinkingIndicator": {
      "primary": "[class*='thinking']",
      "fallback": "text=Thought for"
    },
    "streamingIndicator": {
      "primary": "button[aria-label='Stop generating']",
      "fallback": ".result-streaming"
    },
    "rateLimitDetector": {
      "primary": "text=Too many requests",
      "fallback": "text=rate limit"
    },
    "loginCheck": {
      "primary": "[id='prompt-textarea']",
      "fallback": "textarea"
    },
    "messageList": {
      "primary": "[class*='conversation-turn']",
      "fallback": "[data-message-author-role]"
    },
    "userMessage": {
      "primary": "[data-message-author-role='user']",
      "fallback": ".group\\/conversation-turn [data-message-author-role='user']"
    },
    "assistantMessage": {
      "primary": "[data-message-author-role='assistant']",
      "fallback": ".group\\/conversation-turn .markdown"
    }
  },
  "claude": {
    "chatInput": {
      "primary": "[contenteditable='true']",
      "fallback": ".ProseMirror"
    },
    "sendButton": {
      "primary": "button[aria-label='Send Message']",
      "fallback": "button:has(svg path[d*='M3'])"
    },
    "responseContainer": {
      "primary": "[class*='response']",
      "fallback": ".font-claude-message"
    },
    "lastResponse": {
      "primary": "[class*='response']:last-child",
      "fallback": ".font-claude-message:last-child"
    },
    "streamingIndicator": {
      "primary": "[class*='stop']",
      "fallback": "button[aria-label='Stop']"
    },
    "loginCheck": {
      "primary": "[contenteditable='true']",
      "fallback": ".ProseMirror"
    }
  }
}
```

---

## 6. Timing & Resilience

### 6a. Provider-Specific Timeouts

```json
{
  "gpt": {
    "navigationTimeoutMs": 30000,
    "responseStartMs": 180000,
    "responseCompleteMs": 600000,
    "pollIntervalMs": 2000,
    "thinkingMaxMs": 300000,
    "thinkingLogIntervalMs": 15000
  },
  "claude": {
    "navigationTimeoutMs": 30000,
    "responseStartMs": 60000,
    "responseCompleteMs": 300000,
    "pollIntervalMs": 1000
  }
}
```

### 6b. GPT Extended Thinking Handling

GPT "Thought for Xs" gösterdiğinde:
1. Thinking indicator tespit et
2. Her 15 saniyede stderr'e log: `[bridge] GPT thinking... (45s elapsed)`
3. Max 5 dakika bekle
4. Thinking bitince normal response polling'e geç

### 6c. Rate Limit Backoff

Mesaj gönderdikten sonra rate limit tespit edilirse:
1. 2 saniye bekle, tekrar dene
2. Hala rate limit varsa 4 saniye bekle
3. Üçüncü denemede 8 saniye
4. Max 3 retry, sonra hata dön

### 6d. Screenshot on Failure

Her hata noktasında otomatik screenshot:
- Selector bulunamadı
- Login expired
- Response timeout
- Rate limit exceeded
- Fatal error

Kayıt: `~/.chat-bridge/screenshots/{target}-{error-type}-{timestamp}.png`

---

## 7. Response Handling

### 7a. Truncation

- Default max: 100000 karakter
- `--max-chars N` ile override
- Truncation son newline'da keser (satır bölünmez)
- Truncated response'a marker eklenir: `[TRUNCATED: 52341 chars, limit 100000]`
- JSON'da `truncated: true/false` flag'i

### 7b. Streaming Detection

Response tamamlanma kriteri:
1. Streaming indicator (stop button) kayboldu
2. Thinking indicator kayboldu
3. Son 3 poll'da response uzunluğu değişmedi
4. Minimum 2 saniye stability

---

## 8. Duplicate Prevention (Cache)

Son 5 mesajın hash'ini tut: `~/.chat-bridge/cache/recent-messages.json`

```json
[
  {
    "hash": "sha256-abc123",
    "target": "gpt",
    "chatUrl": "...",
    "timestamp": 1711612800,
    "preview": "pr 94 hazır..."
  }
]
```

- Aynı target + chatUrl + message hash tekrar gelirse:
  - stderr: `WARN: Duplicate message detected (sent 45s ago). Use --force to send anyway.`
  - `--force` olmadan gönderme, hata JSON dön
- Max 5 entry, FIFO
- TTL: 5 dakika

---

## 9. Logging

- stdout: SADECE JSON output (response, verdict, health, export)
- stderr: Human-readable log'lar

```
[bridge] Navigating to https://chatgpt.com/g/g-p-.../c/abc123
[bridge] Sending message (142 chars)
[bridge] Waiting for response...
[bridge] GPT thinking... (15s elapsed)
[bridge] GPT thinking... (30s elapsed)
[bridge] Response streaming started
[bridge] Response complete (4523 chars, 45.2s)
```

Log levels: `--verbose` flag'i ile debug log'ları açılır.

---

## 10. Config Dosyası

`~/.chat-bridge/config.json`:

```json
{
  "gpt": {
    "baseUrl": "https://chatgpt.com",
    "projectUrl": "https://chatgpt.com/g/g-p-69c05848f5cc819196f2e353529d45f6-vezir",
    "newChatUrl": "https://chatgpt.com/g/g-p-69c05848f5cc819196f2e353529d45f6-vezir",
    "sessionDir": "~/.chat-bridge/sessions/gpt"
  },
  "claude": {
    "baseUrl": "https://claude.ai",
    "projectUrl": null,
    "newChatUrl": "https://claude.ai/new",
    "sessionDir": "~/.chat-bridge/sessions/claude"
  },
  "defaults": {
    "maxResponseChars": 100000,
    "screenshotOnError": true,
    "headless": true,
    "verbose": false
  }
}
```

---

## 11. Dosya Yapısı

```
chat-bridge/
├── bridge.js              # Ana giriş noktası
├── package.json
├── selectors.json         # UI selector'ları (ayrı, code'dan bağımsız)
├── config.example.json    # Örnek config
├── check.js               # Health check wrapper
├── README.md
├── CLAUDE.md              # Claude Code entegrasyon talimatları
└── lib/
    ├── browser.js         # Playwright browser management
    ├── messaging.js       # Mesaj gönder + response bekle
    ├── parsing.js         # Verdict extraction + response parsing
    ├── cache.js           # Duplicate detection
    ├── health.js          # Health check logic
    └── export.js          # Conversation export
```

---

## 12. CLI Tam Referans

```
node bridge.js --target <gpt|claude> --message "..."                          # Mesaj gönder
node bridge.js --target <gpt|claude> --chat-url URL --message "..."           # Mevcut chat'e
node bridge.js --target <gpt|claude> --new-chat --message "..."               # Yeni chat aç
node bridge.js --target <gpt|claude> --message "..." --extract-verdict        # + verdict parse
node bridge.js --target <gpt|claude> --message "..." --max-chars 50000       # Truncation limit
node bridge.js --target <gpt|claude> --message "..." --force                  # Duplicate bypass
node bridge.js --health <gpt|claude|all>                                      # Sağlık kontrolü
node bridge.js --export --target <gpt|claude> --chat-url URL                  # Chat export
node bridge.js --setup <gpt|claude>                                           # İlk login (headed)
node bridge.js --target <gpt|claude> --message "..." --headed                 # Debug modu
node bridge.js --target <gpt|claude> --message "..." --verbose                # Debug log'ları
```

---

## 13. CLAUDE.md Entegrasyon Talimatları

Bridge kurulu olduğunda Claude Code şu şekilde kullanır:

```bash
# GPT'ye review gönder
RESULT=$(node ~/chat-bridge/bridge.js --target gpt --message "pr 94 hazır" --extract-verdict)
VERDICT=$(echo "$RESULT" | jq -r '.verdict')
CHAT_URL=$(echo "$RESULT" | jq -r '.chatUrl')

# HOLD ise patch uygula ve tekrar gönder
if [ "$VERDICT" = "HOLD" ]; then
  PATCHES=$(echo "$RESULT" | jq -r '.patches[]')
  # ... patch uygula ...
  RESULT2=$(node ~/chat-bridge/bridge.js --target gpt --chat-url "$CHAT_URL" --message "patches applied, re-review" --extract-verdict)
fi

# PASS ise closure'a geç
if [ "$VERDICT" = "PASS" ]; then
  echo "GPT PASS — proceeding to closure"
fi
```

---

## 14. Öncelik Sırası

1. Core messaging (bridge.js + selectors.json + config.json)
2. Health check (--health)
3. Verdict extraction (--extract-verdict)
4. Duplicate cache (--force)
5. Conversation export (--export)
6. CLAUDE.md entegrasyonu
