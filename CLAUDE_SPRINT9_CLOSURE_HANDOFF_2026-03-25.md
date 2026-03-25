\# Sprint 9 Closure Handoff



\## Net durum



Sprint 9 implementasyonu büyük ölçüde tamamlanmış görünüyor. Ancak bunu `COMPLETE` diye kapatmadan önce son closure turunu istiyorum.



Varsayım:

\- Kod büyük ölçüde doğru.

\- Kalan işin çoğu doc/evidence closure.

\- Sadece gerçek kontrat drift varsa kod değiştir.



\## Bu turdaki hedef



Sprint 9'u anlatıyla değil, kanıtla kapat.

Kod, report ve task breakdown aynı şeyi söyleyecek.

`partial` / `complete` etiketi evidence'a göre verilecek.



\## Şu an kabul ettiğim durum



Aşağıdaki maddeleri mevcut gerçek durum olarak al:



\- Frontend React + TypeScript + Tailwind + Vite ile kuruldu.

\- Backend proxy `:3000 -> /api -> :8003`.

\- 22 TS type / 22 Python schema parity hedefi var.

\- Polling 30s global.

\- 5 page var: Missions, Mission Detail, Health, Approvals, Telemetry.

\- Per-panel ErrorBoundary var.

\- Vitest testleri, TypeScript build ve production build başarılı görünüyor.



Ama şu noktalar kapanmış sayılmayacak:



1\. `GPT Review: Pending`

2\. Live browser verification pending

3\. Sprint 9 DoD içinde olan `npm run lint` evidence'ı yok

4\. Sprint 9 DoD içinde olan `validate\_sprint\_docs.py --sprint 9` evidence'ı yok

5\. Report "all 10 endpoints consumed" diyor ama client section 8 named function listeliyor



\## Yapılacaklar



\### 1) Endpoint inventory'yi tek gerçeğe indir



Önce sayı yalanını temizle.



Kontrol et:

\- Backend tarafında Sprint 9 UI'nin gerçekten consume ettiği endpoint listesi ne?

\- Client tarafında gerçekten kaç distinct API function var?

\- Eğer 8 function ile 10 endpoint consume ediliyorsa bunu açık yaz.

\- Eğer rapor yanlışsa raporu düzelt.

\- Eğer gerçekten eksik endpoint consumption varsa task ve report'ta bunu açık yaz; `COMPLETE` deme.



İstediğim çıktı:

\- Tek tablo: `endpoint | client function | UI consumer page | status`



\### 2) Evidence bundle'ı tamamla



Aşağıdaki komutları gerçekten çalıştır ve raw output'u kayda koy:



```bash

cd C:/Users/AKCA/oc/frontend

npm run lint

npx tsc --noEmit

npx vitest run

npm run build



cd C:/Users/AKCA/oc

python tools/validate\_sprint\_docs.py --sprint 9



Ek olarak schema/type parity ve kritik UI contract grep evidence üret:



cd C:/Users/AKCA/oc



grep -n "fresh\\|partial\\|stale\\|degraded\\|unknown\\|not\_reached" frontend/src/types/api.ts

grep -n "available\\|unavailable\\|unknown" frontend/src/types/api.ts

grep -n "usePolling" -R frontend/src

grep -n "ErrorBoundary" -R frontend/src

grep -n "FreshnessIndicator" -R frontend/src

grep -n "DataQualityBadge" -R frontend/src





Beklediğim çıktı:



evidence/sprint-9/ altında raw command outputs

kısa özet değil, gerçek stdout/stderr

3\) Live browser verification yap



Backend :8003 çalışırken frontend :3000 aç.

Aşağıdakileri tek tek doğrula:



/missions açılıyor

mission list geliyor

mission detail açılıyor

gate results görünüyor

deny forensics hidden değil

agentUsed görünüyor

/health açılıyor

capabilities tri-state distinct render ediyor

/approvals açılıyor

/telemetry açılıyor

telemetry filter çalışıyor

polling indicator header'da görünüyor

stale/degraded/unknown state'ler sessizce kaybolmuyor

bir panel hata aldığında diğer paneller çalışmaya devam ediyor



İstediğim çıktı:



kısa browser verification section

mümkünse screenshot yerine metin tabanlı checklist

her madde PASS/FAIL

4\) Sprint 9 report'u düzelt



Report içinde aşağıdakileri temizle:



GPT Review: Pending ifadesi

Live browser verification pending ifadesi

endpoint sayısı çelişkisi

evidence section eksikliği

kapanış statüsü



Kural:



Her şey gerçekten geçtiyse COMPLETE

Lint / validator / live verification / endpoint inventory'den biri eksikse PARTIAL

operator discretion gibi gevşek ifade bırakma

5\) Dokümanları birlikte hizala



Aynı commit içinde bunları hizala:



Sprint 9 phase report

docs/ai/SPRINT-9-TASK-BREAKDOWN.md

docs/ai/NEXT.md

docs/ai/STATE.md

gerekiyorsa docs/ai/BACKLOG.md



NEXT.md ancak Sprint 9 closure gerçekten kanıtlandıysa Sprint 10'a geçsin.



Karar standardı



Aşağıdaki kurala uy:



Kod doğruysa doc düzelt, gereksiz refactor yapma

Kontrat drift gerçekse küçük ve hedefli patch yap

Evidence yoksa NO EVIDENCE yaz

Test yoksa TEST MISSING yaz

Doğrulanmayan işi complete yazma

Benden beklenen final çıktı



Tek mesajda şunları ver:



Net hüküm: COMPLETE veya PARTIAL

Blocking issues kaldı mı?

Endpoint inventory tablosu

Evidence summary

Güncellenen dosyalar

Çalıştırılan verification komutları

Commit hash

Ek not



Sprint 8'i tekrar açma.

Sprint 9 closure odaklı ilerle.

Yeni feature ekleme.

SSE, mutation, pagination gibi işleri Sprint 10+ backlog'unda bırak.





En doğru pozisyon şu: \*\*Sprint 9 bitmiş olabilir, ama kapanışı henüz kanıtlanmış değil.\*\* Claude’dan isteyeceğin şey yeni geliştirme değil, \*\*closure pass\*\* olmalı.

