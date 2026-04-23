# PulseCraft Eval Report — Signalscribe

**Timestamp:** 2026-04-23T16:55:57+00:00Z  
**Commit:** 701fc82  
**Model:** claude-sonnet-4-6  
**Runs per fixture:** 3  

---

## Summary

| Fixture | Bu | Expected | Observed | Classification | Cost |
|---|---|---|---|---|---|
| 001_clearcut_communicate | — | {READY} | READY(3/3) | ✅ stable | $0.184 |
| 002_pure_internal_refactor | — | {ARCHIVE} | ARCHIVE(3/3) | ✅ stable | $0.112 |
| 003_ambiguous_escalate | — | {ESCALATE} | ARCHIVE(2/3) / ESCALATE(1/3) | ✅ acceptable variance | $0.099 |
| 004_early_flag_hold_until | — | {HOLD_UNTIL} | HOLD_UNTIL(3/3) | ✅ stable | $0.141 |
| 005_muddled_need_clarification | — | {HOLD_INDEFINITE, NEED_CLARIFICATION, UNRESOLVABLE} | HOLD_INDEFINITE(3/3) | ✅ stable | $0.126 |
| 006_multi_bu_affected_vs_adjacent | — | {READY} | READY(3/3) | ✅ stable | $0.174 |
| 007_mlr_sensitive | — | {READY} | READY(2/3) / NEED_CLARIFICATION(1/3) | 🟡 unstable | $0.172 |
| 008_post_hoc_already_shipped | — | {READY} | READY(3/3) | ✅ stable | $0.165 |

**Overall (8 evaluated, 0 skipped):** **stable:** 6  **acceptable variance:** 1  **unstable:** 1  **FALSE POSITIVE RISK:** 0  **mismatch:** 0  
**Total cost:** $1.173  
**Total elapsed:** 707s  

---

## Detail

### 001_clearcut_communicate

- **Expected terminal verbs:** ['READY']
- **Observed distribution:** READY(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | READY | — | 0.92 | 37.5s | $0.062 | — |
| 2 | READY | — | 0.91 | 36.7s | $0.062 | — |
| 3 | READY | — | 0.91 | 35.6s | $0.060 | — |

> **Note:** Clear rollout signal — redesigned PA validation form visible to all HCP portal users. Should proceed through all 3 gates without early stop.

---

### 002_pure_internal_refactor

- **Expected terminal verbs:** ['ARCHIVE']
- **False-positive verbs:** ['READY']
- **Observed distribution:** ARCHIVE(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | ARCHIVE | — | 0.97 | 18.8s | $0.036 | — |
| 2 | ARCHIVE | — | 0.97 | 15.2s | $0.037 | — |
| 3 | ARCHIVE | — | 0.97 | 17.0s | $0.039 | — |

> **Note:** Internal message-queue client migration, no user-visible change. ARCHIVE at gate 1 is the only correct outcome. READY would mean the agent committed to communicating a purely internal refactor.

---

### 003_ambiguous_escalate

- **Expected terminal verbs:** ['ESCALATE']
- **Acceptable alternates:** ['ARCHIVE', 'HOLD_INDEFINITE', 'NEED_CLARIFICATION', 'UNRESOLVABLE']
- **False-positive verbs:** ['READY']
- **Observed distribution:** ARCHIVE(2/3) / ESCALATE(1/3)
- **Classification:** ✅ **acceptable variance**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | ARCHIVE | — | 0.88 | 16.7s | $0.032 | — |
| 2 | ARCHIVE | — | 0.88 | 12.2s | $0.032 | — |
| 3 | ESCALATE | — | 0.32 | 15.4s | $0.035 | — |

> **Note:** Designed-ambiguous: 'Portal Release — Sprint 47 Improvements' with vague language. Design intent is ESCALATE (ask a human). Dryrun 2026-04-23 shows ARCHIVE 2/2 times. ARCHIVE is defensible (too vague to act on) but differs from design intent. All uncertainty signals acceptable; READY would mean the agent committed to communicating a deliberately vague artifact.

---

### 004_early_flag_hold_until

- **Expected terminal verbs:** ['HOLD_UNTIL']
- **Acceptable alternates:** ['HOLD_INDEFINITE']
- **False-positive verbs:** ['READY']
- **Observed distribution:** HOLD_UNTIL(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | HOLD_UNTIL | — | 0.88 | 29.3s | $0.047 | — |
| 2 | HOLD_UNTIL | — | 0.88 | 24.4s | $0.046 | — |
| 3 | HOLD_UNTIL | — | 0.88 | 23.3s | $0.047 | — |

> **Note:** Feature flag enabled but not yet rolled out. HOLD_UNTIL at gate 2 is the expected verdict (hold until rollout is confirmed). HOLD_INDEFINITE is acceptable (agent chose longer-form hold). READY would mean the agent treated a not-yet-deployed feature as ready to communicate.

---

### 005_muddled_need_clarification

- **Expected terminal verbs:** ['HOLD_INDEFINITE', 'NEED_CLARIFICATION', 'UNRESOLVABLE']
- **Acceptable alternates:** ['ARCHIVE']
- **False-positive verbs:** ['READY']
- **Observed distribution:** HOLD_INDEFINITE(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | HOLD_INDEFINITE | — | 0.80 | 24.6s | $0.041 | — |
| 2 | HOLD_INDEFINITE | — | 0.88 | 25.1s | $0.042 | — |
| 3 | HOLD_INDEFINITE | — | 0.88 | 25.3s | $0.042 | — |

> **Note:** Muddled artifact with contradictory or incomplete signals. Any 'uncertainty' terminal verb is correct. ARCHIVE is acceptable (truly unresolvable). READY would mean the agent committed to communicating muddled content.

---

### 006_multi_bu_affected_vs_adjacent

- **Expected terminal verbs:** ['READY']
- **Observed distribution:** READY(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | READY | — | 0.85 | 42.8s | $0.058 | — |
| 2 | READY | — | 0.88 | 33.9s | $0.058 | — |
| 3 | READY | — | 0.88 | 34.7s | $0.058 | — |

> **Note:** Analytics Portal new filtering/export capabilities — clear new feature. Should proceed through all 3 gates.

---

### 007_mlr_sensitive

- **Expected terminal verbs:** ['READY']
- **Observed distribution:** READY(2/3) / NEED_CLARIFICATION(1/3)
- **Classification:** 🟡 **unstable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | NEED_CLARIFICATION | — | 0.72 | 45.4s | $0.060 | — |
| 2 | READY | — | 0.81 | 39.0s | $0.055 | — |
| 3 | READY | — | 0.78 | 41.1s | $0.057 | — |

> **Note:** HCP Educational Module update — clinical content. SignalScribe should say READY; MLR review is enforced by policy at step 5, not gate 3. Agent should NOT self-censor on MLR sensitivity.

---

### 008_post_hoc_already_shipped

- **Expected terminal verbs:** ['READY']
- **Acceptable alternates:** ['ARCHIVE']
- **Observed distribution:** READY(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | READY | — | 0.90 | 41.7s | $0.058 | — |
| 2 | READY | — | 0.91 | 37.8s | $0.056 | — |
| 3 | READY | — | 0.91 | 33.2s | $0.051 | — |

> **Note:** Post-hoc already-shipped change (notification wording standardization). READY is expected (retroactive communication still valuable). ARCHIVE is acceptable (agent may recognize it as already complete). No false-positive risk — READY on a shipped change is not harmful.

---
