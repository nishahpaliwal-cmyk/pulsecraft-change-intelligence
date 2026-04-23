# PulseCraft Eval Report — Pushpilot

**Timestamp:** 2026-04-23T17:17:07+00:00Z  
**Commit:** 701fc82  
**Model:** claude-sonnet-4-6  
**Runs per fixture:** 3  

---

## Summary

| Fixture | Bu | Expected | Observed | Classification | Cost |
|---|---|---|---|---|---|
| 001_clearcut_communicate | bu_alpha | {hold_until, send_now} | send_now(3/3) | ✅ stable | $0.086 |
| 006_multi_bu_affected_vs_adjacent | bu_zeta | {hold_until, send_now} | SKIPPED — bu_zeta not in candidate set (SignalScri | ⏭️ skipped | $0.000 |
| 007_mlr_sensitive | bu_gamma | {hold_until, send_now} | send_now(3/3) | ✅ stable | $0.087 |

**Overall (2 evaluated, 1 skipped):** **stable:** 2  **acceptable variance:** 0  **unstable:** 0  **FALSE POSITIVE RISK:** 0  **mismatch:** 0  
**Total cost:** $0.173  
**Total elapsed:** 77s  

---

## Detail

### 001_clearcut_communicate / bu_alpha

- **Expected terminal verbs:** ['hold_until', 'send_now']
- **False-positive verbs:** ['digest']
- **Observed distribution:** send_now(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | send_now | — | 0.96 | 10.4s | $0.028 | — |
| 2 | send_now | — | 0.95 | 11.7s | $0.029 | — |
| 3 | send_now | — | 0.95 | 12.5s | $0.029 | — |

> **Note:** bu_alpha P0 priority change during business hours. SEND_NOW is the ideal outcome; HOLD_UNTIL acceptable if agent sees timing risk. DIGEST is wrong — batching a P0 notification misrepresents urgency.

---

### 006_multi_bu_affected_vs_adjacent / bu_zeta

- **Expected terminal verbs:** ['hold_until', 'send_now']
- **False-positive verbs:** ['digest']
- **Classification:** ⏭️ SKIPPED
- **Reason:** bu_zeta not in candidate set (SignalScribe impact_areas=['analytics_portal_reporting_dashboard', 'data_export_workflow', 'clinical_operations_enrollment_summary_report_ui']).

> **Note:** bu_zeta analytics change — SEND_NOW or HOLD_UNTIL expected. bu_zeta's profile will determine whether digest is acceptable channel; since this is a high-priority feature update, DIGEST is a false positive risk.

---

### 007_mlr_sensitive / bu_gamma

- **Expected terminal verbs:** ['hold_until', 'send_now']
- **False-positive verbs:** ['digest']
- **Observed distribution:** send_now(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | send_now | — | 0.97 | 17.8s | $0.030 | — |
| 2 | send_now | — | 0.97 | 11.7s | $0.028 | — |
| 3 | send_now | — | 0.95 | 13.0s | $0.029 | — |

> **Note:** bu_gamma MLR-sensitive change. PushPilot should recommend send_now or hold_until. MLR restriction is enforced by policy (HITL trigger), not by PushPilot's gate-6 decision. DIGEST would be wrong — MLR review requires explicit approval, not batching.

---
