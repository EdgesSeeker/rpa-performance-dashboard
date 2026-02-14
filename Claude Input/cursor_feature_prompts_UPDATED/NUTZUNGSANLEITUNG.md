# 🚀 SO NUTZT DU DIE PROMPTS - Step by Step

## Was du jetzt hast:

1. **CURSOR_REVIEW_PROMPT.md** - Cursor prüft den Plan
2. **CURSOR_IMPLEMENTATION_PROMPT.md** - Der komplette Implementation Plan

## ⚡ Die Reihenfolge (wichtig!):

### Schritt 1: Review First (5-10 Min)

**Warum?** Besser JETZT Probleme finden als nach 2 Stunden Coding.

**Was tun:**
```
1. Öffne Cursor
2. Kopiere die 3 Files ins Projekt:
   - CURSOR_REVIEW_PROMPT.md
   - CURSOR_IMPLEMENTATION_PROMPT.md
   - (CLAUDE.md und SCRATCHPAD.md hast du ja schon)

3. Öffne Cursor Chat
4. Aktiviere Plan Mode: Shift + Tab (2x)
5. Model wählen: Opus 4.5 (für kritische Review)
6. Copy-Paste den KOMPLETTEN Text aus CURSOR_REVIEW_PROMPT.md
7. Absenden
```

**Cursor wird jetzt:**
- Den Implementation Plan durchgehen
- Technische Machbarkeit prüfen
- Zeit-Schätzungen validieren
- Risiken identifizieren
- Verbesserungen vorschlagen

**Erwarte:** 3-5 Minuten bis Antwort kommt (Opus denkt durch)

---

### Schritt 2: Review-Ergebnisse analysieren

**Cursor gibt dir:**
- ✅ Was funktioniert
- ⚠️ Was angepasst werden sollte
- ❌ Was nicht geht
- 💡 Verbesserungsvorschläge
- 📋 Revidierte Zeit-Schätzung

**Deine Entscheidung:**

**FALL A: Alles grün ✅**
```
Cursor sagt: "Plan ist solid, go ahead"
→ Weiter zu Schritt 3
```

**FALL B: Kleine Anpassungen ⚠️**
```
Cursor sagt: "Change X, Y, Z"
→ Frag Cursor: "Update CURSOR_IMPLEMENTATION_PROMPT.md with your suggestions"
→ Cursor updated den Plan
→ Weiter zu Schritt 3
```

**FALL C: Major Issues ❌**
```
Cursor sagt: "Won't work because X"
→ Diskutiere mit Cursor Alternativen
→ Lass Cursor einen neuen Plan schreiben
→ Dann Review wiederholen
```

---

### Schritt 3: Implementation (2-4 Stunden)

**Nur wenn Review positiv!**

**Was tun:**
```
1. Neue Cursor Conversation (oder /clear wenn alte zu voll)
2. Plan Mode: Shift + Tab (2x)
3. Model: Sonnet 4 (schneller für Implementation)
4. Copy-Paste den KOMPLETTEN Text aus CURSOR_IMPLEMENTATION_PROMPT.md
5. Absenden
```

**Cursor wird jetzt:**
- Den kompletten Plan lesen
- Fragen stellen wenn was unklar ist
- Phase für Phase implementieren

**Wichtig:**
```
Nach JEDER Phase:
1. Cursor macht Code
2. Du testest kurz
3. Wenn ok: "Continue to next phase"
4. Wenn nicht ok: "Fix issue X, then continue"

DON'T: Alle 5 Phasen auf einmal machen lassen ohne zu testen!
```

---

### Schritt 4: Testing & Polish (30 Min)

**Nach allen Phasen:**
```
1. Dashboard starten: streamlit run frontend/streamlit_app.py
2. Prüfe jedes Feature:
   ✓ Quick Wins werden angezeigt?
   ✓ Zahlen machen Sinn?
   ✓ Weekly Trends Chart funktioniert?
   ✓ Excel Export hat Executive Summary?

3. Edge Cases testen:
   - Ändere Date Range auf nur 3 Tage → Warnung?
   - Keine Idle Patterns vorhanden → Sinnvolle Message?

4. Screenshots machen für Pitch!
```

---

## 🎓 Pro-Tips

### Tip 1: Context Management
```
Nach Phase 3 (Frontend):
→ /compact (Context wird groß)

Nach Phase 5:
→ /clear (fresh start für nächste Features)
```

### Tip 2: Wenn Cursor stuck ist
```
Nach 3x gleichem Fehler:
→ /clear
→ "Read SCRATCHPAD.md for context"
→ "I'm stuck on Phase X, issue Y"
→ "Let's try different approach: Z"
```

### Tip 3: SCRATCHPAD.md updaten
```
Nach jeder Phase:
→ "Update SCRATCHPAD.md with progress"

Cursor schreibt:
- Was done ist
- Was in progress ist
- Blockers wenn welche
```

### Tip 4: Incremental Testing
```
NICHT:
"Implement all 5 phases, then show me"

SONDERN:
"Implement Phase 1"
[du testest]
"Looks good, implement Phase 2"
[du testest]
...
```

---

## 🚨 Häufige Probleme & Lösungen

### Problem 1: "Review dauert ewig"
**Lösung:** Opus ist langsam aber gründlich. Warte ab (5 Min normal).

### Problem 2: "Cursor sagt 'won't work'"
**Lösung:** Gut! Besser jetzt als nach 3h Coding. Diskutiere Alternativen.

### Problem 3: "Implementation schlägt fehl"
**Lösung:** 
```
1. Error kopieren
2. Zu Cursor: "I got this error: [paste]"
3. Cursor debugged
4. Fix, dann weitermachen
```

### Problem 4: "Features funktionieren aber sehen nicht gut aus"
**Lösung:**
```
Nach Phase 5:
"Polish the UI:
- Improve Quick Wins visual hierarchy
- Add icons/emojis
- Better spacing
- Consistent colors"
```

### Problem 5: "Daten ergeben keinen Sinn"
**Lösung:**
```
"Debug the Quick Wins calculation:
1. Show me raw data for last 7 days
2. Show me the idle pattern detection logic
3. Let's verify the calculation step by step"
```

---

## 📊 Erfolgs-Checkliste

### Nach Review:
- [ ] Cursor hat Plan approved oder Änderungen vorgeschlagen
- [ ] Zeit-Schätzung klingt realistisch
- [ ] Keine kritischen Blocker
- [ ] Du verstehst was gebaut wird

### Nach Implementation:
- [ ] Alle 5 Phasen completed
- [ ] Dashboard lädt ohne Fehler
- [ ] Quick Wins werden angezeigt
- [ ] Zahlen machen Sinn (manuell gecheckt)
- [ ] Weekly Trends Chart funktioniert
- [ ] Excel Export hat neue Sheet
- [ ] Screenshots gemacht

### Pitch-Ready:
- [ ] Demo kann durchlaufen (3 Min)
- [ ] Quick Wins beeindrucken (konkrete Zahlen)
- [ ] Weekly Trends zeigen Verbesserung
- [ ] Excel Summary ist management-ready
- [ ] Backup-Plan (Screenshots) ready

---

## ⏱️ Zeit-Kalkulation Realistisch

### Optimistisch (alles läuft glatt):
```
Review:         10 Min
Implementation: 120 Min (2h)
Testing:        30 Min
Polish:         20 Min
Screenshots:    10 Min
─────────────────────────
TOTAL:          3h 10min
```

### Realistisch (mit Debugging):
```
Review:         15 Min
Implementation: 180 Min (3h)
Debugging:      45 Min
Testing:        30 Min
Polish:         30 Min
Screenshots:    10 Min
─────────────────────────
TOTAL:          5h 00min
```

### Mit Pausen (empfohlen):
```
Session 1:  Review + Phase 1+2     (1.5h)
Pause:      Kaffee, Test, Analyse  (30min)
Session 2:  Phase 3+4               (1.5h)
Pause:      Mittag                  (1h)
Session 3:  Phase 5 + Polish        (1h)
Test Session: Final testing         (30min)
─────────────────────────────────────────
TOTAL:      6h 00min (über den Tag verteilt)
```

**Meine Empfehlung:** Plane 5-6 Stunden mit Pausen.

---

## 🎯 Quick Decision Tree

```
START
  │
  ├─ Hast du 5+ Stunden Zeit heute?
  │   ├─ JA → Full Implementation (alle 3 Features)
  │   └─ NEIN ↓
  │
  ├─ Hast du 2-3 Stunden Zeit?
  │   ├─ JA → Nur Feature 1 (Quick Wins) - höchster Impact!
  │   └─ NEIN ↓
  │
  └─ Hast du nur 1 Stunde?
      └─ JA → Review Only + Planning Session
          (Implementation morgen)
```

---

## 🎬 Los geht's!

**STEP 1: Öffne Cursor**
**STEP 2: Plan Mode (Shift+Tab 2x)**
**STEP 3: Opus 4.5 wählen**
**STEP 4: Copy-Paste CURSOR_REVIEW_PROMPT.md**
**STEP 5: Absenden und abwarten**

**Nach Review:**
→ Wenn grün: Weiter zu CURSOR_IMPLEMENTATION_PROMPT.md
→ Wenn Anpassungen: Diskutieren, dann implementieren
→ Wenn Probleme: Alternativen mit Cursor besprechen

---

**Bereit? GO! 🚀**

**Du baust jetzt in wenigen Stunden Features, die normal Tage dauern würden!**

**Das ist die Power von Cursor + Strukturierter Plan + Eyad's Workflow!**

**Viel Erfolg - und teil mir mit wie's läuft! 💪**
