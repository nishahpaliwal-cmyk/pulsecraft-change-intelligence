# PulseCraft Eval Report — Buatlas

**Timestamp:** 2026-04-23T17:12:29+00:00Z  
**Commit:** 701fc82  
**Model:** claude-sonnet-4-6  
**Runs per fixture:** 3  

---

## Summary

| Fixture | Bu | Expected | Observed | Classification | Cost |
|---|---|---|---|---|---|
| 001_clearcut_communicate | bu_alpha | {affected} | affected(3/3) | ✅ stable | $0.196 |
| 006_multi_bu_affected_vs_adjacent | bu_zeta | {affected} | SKIPPED — bu_zeta not in candidate set (SignalScri | ⏭️ skipped | $0.000 |
| 006_multi_bu_affected_vs_adjacent | bu_delta | {adjacent} | SKIPPED — bu_delta not in candidate set (SignalScr | ⏭️ skipped | $0.000 |
| 007_mlr_sensitive | bu_gamma | {affected} | affected(3/3) | ✅ stable | $0.199 |

**Overall (2 evaluated, 2 skipped):** **stable:** 2  **acceptable variance:** 0  **unstable:** 0  **FALSE POSITIVE RISK:** 0  **mismatch:** 0  
**Total cost:** $0.395  
**Total elapsed:** 830s  

---

## Detail

### 001_clearcut_communicate / bu_alpha

- **Expected terminal verbs:** ['affected']
- **Observed distribution:** affected(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | affected | worth_sending | 0.91 | 36.3s | $0.066 | — |
| 2 | affected | worth_sending | 0.91 | 35.3s | $0.065 | — |
| 3 | affected | worth_sending | 0.91 | 34.1s | $0.065 | — |

> **Note:** bu_alpha owns specialty_pharmacy + hcp_portal_ordering — directly in the PA form change. AFFECTED is the only correct verdict.

---

### 006_multi_bu_affected_vs_adjacent / bu_zeta

- **Expected terminal verbs:** ['affected']
- **Classification:** ⏭️ SKIPPED
- **Reason:** bu_zeta not in candidate set (SignalScribe impact_areas=['analytics_portal_reporting_dashboard', 'data_export_workflow', 'dashboard_filtering_ui', 'clinical_operations_enrollment_summary_report']). See expectations.py note for this fixture.

> **Note:** bu_zeta owns analytics_portal + reporting_dashboard — directly in scope. Dryrun 2026-04-23 confirmed AFFECTED.

---

### 006_multi_bu_affected_vs_adjacent / bu_delta

- **Expected terminal verbs:** ['adjacent']
- **Acceptable alternates:** ['not_affected']
- **False-positive verbs:** ['affected']
- **Classification:** ⏭️ SKIPPED
- **Reason:** bu_delta not in candidate set (SignalScribe impact_areas=['analytics_portal', 'reporting_dashboard', 'data_export', 'clinical_operations_enrollment_reporting']). See expectations.py note for this fixture.

> **Note:** bu_delta owns clinical_trial_operations + reporting (generic). Analytics Portal changes may touch reporting adjacently but not core delta BU scope. ADJACENT expected; AFFECTED would be a false positive (unwanted notification). WARNING: bu_delta may not appear in the candidate set if SignalScribe uses specific impact area terms — the runner will skip if bu_delta is not a candidate.

---

### 007_mlr_sensitive / bu_gamma

- **Expected terminal verbs:** ['affected']
- **Observed distribution:** affected(3/3)
- **Classification:** ✅ **stable**

| Run | Terminal | Secondary | Confidence | Elapsed | Cost | Error |
|---|---|---|---|---|---|---|
| 1 | affected | worth_sending | 0.81 | 643.2s | $0.068 | — |
| 2 | affected | worth_sending | 0.81 | 41.5s | $0.066 | — |
| 3 | affected | worth_sending | 0.81 | 40.0s | $0.066 | — |

> **Note:** bu_gamma owns medical_information_portal + clinical_evidence_library. HCP Educational Module update directly impacts gamma's domain. Dryrun 2026-04-23 confirmed AFFECTED.

---
