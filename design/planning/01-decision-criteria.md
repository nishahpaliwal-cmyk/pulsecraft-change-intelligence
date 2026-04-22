# PulseCraft — Decision Criteria for Agent Judgment

> **Purpose of this document.** PulseCraft's agents are not task-executors. They are *decision-makers* at specific gates in the change-communication workflow. This document defines what each decision means, what signals to weigh, what the legitimate outputs are, and what failure modes to avoid. It is the load-bearing intellectual content of the agent prompts — the prompts will *encode* this document, not replace it.
>
> **How this document is used.** Each agent's prompt draws its judgment rules from the gate(s) it owns here. When we need to change how an agent decides, we change this document first, then regenerate the prompt.
>
> **Validation path.** Draft v1. Must be reviewed with a real AbbVie communications or change-management professional and adjusted to reflect AbbVie's actual norms before go-live.
>
> **Status:** Draft v1.

---

## Overview — the six gates

| # | Gate | Owner | Decision verbs |
|---|---|---|---|
| 1 | Is this change worth communicating at all? | SignalScribe | `COMMUNICATE` / `ARCHIVE` / `ESCALATE` |
| 2 | Is this change ripe (is the timing right to start communicating)? | SignalScribe | `RIPE` / `HOLD_UNTIL(date)` / `HOLD_INDEFINITE` |
| 3 | Is my understanding clear enough to hand off? | SignalScribe | `READY` / `NEED_CLARIFICATION(questions)` / `UNRESOLVABLE` |
| 4 | Is this BU actually affected (vs. merely adjacent)? | BUAtlas (per BU) | `AFFECTED` / `ADJACENT` / `NOT_AFFECTED` |
| 5 | Is the message I've drafted worth this BU head's attention? | BUAtlas (per BU) | `WORTH_SENDING` / `WEAK` / `NOT_WORTH` |
| 6 | Is right now the right time to send this? | PushPilot | `SEND_NOW` / `HOLD_UNTIL(time)` / `DIGEST` / `ESCALATE` |

Each gate can also emit `ESCALATE` to route to human review when confidence is too low.

**Flow between gates:**

- Gates 1 → 2 → 3 run inside SignalScribe, sequentially. If gate 1 returns `ARCHIVE`, gates 2 and 3 are skipped. If gate 2 returns `HOLD_UNTIL`, SignalScribe returns without attempting gate 3. If gate 3 returns `NEED_CLARIFICATION`, the whole change goes to HITL with questions.
- SignalScribe hands the `ChangeBrief` + decision trail to the orchestrator, which fans out to BUAtlas (one invocation per candidate BU).
- Gates 4 → 5 run inside each BUAtlas invocation. If gate 4 returns `NOT_AFFECTED`, gate 5 is skipped.
- The orchestrator collects all BUAtlas decisions and passes `WORTH_SENDING` personalized briefs to PushPilot.
- Gate 6 runs inside PushPilot, once per notification.

---

## Gate 1 — Is this change worth communicating at all?

**Owner:** SignalScribe
**Decision verbs:** `COMMUNICATE` | `ARCHIVE` | `ESCALATE`

### What this decision means

Not every release note or change artifact warrants a BU-head notification. A bug fix that no one noticed, a silent internal refactor, a copy tweak — these do not belong in a BU head's inbox. Pushing them through creates noise, erodes trust, and teaches recipients to ignore future notifications.

A thoughtful communications lead asks: *"Is there any party, inside or outside AbbVie, whose work or experience will change because of this?"* If no, archive. If yes, continue.

### Signals that favor `COMMUNICATE`

- **Visible behavior change** — users, HCPs, patients, partners, or internal operators will see or feel something different.
- **Customer-facing surface affected** — UI, API response, email content, notification wording, document output.
- **Workflow change** — a step is added, removed, reordered, or restricted.
- **Integration impact** — downstream systems (Veeva, ServiceNow, data pipelines, reporting) consume the affected behavior.
- **Support load implication** — the change will likely generate questions, tickets, or confusion if not pre-communicated.
- **Regulatory or compliance relevance** — even if minor, changes touching labeling, consent flows, audit trails, PV workflows, or data-retention behavior warrant communication.
- **Reversal of a previously communicated state** — we said X last month; now we're doing Y.
- **New capability introduced** — something recipients could now do that they couldn't before.

### Signals that favor `ARCHIVE`

- **Pure internal refactor** — code structure changed, no behavior change, no user impact.
- **Dependency version bumps** with no functional effect.
- **Copy-only edits** where the meaning is unchanged (typo fixes, grammar).
- **Infrastructure changes** transparent to users with no user-observable effect.
- **Bug fixes for edge cases statistically unlikely to have been noticed.**
- **Internal-tool-only changes** where no downstream or external party is affected.

### Signals that favor `ESCALATE`

- **Ambiguous scope** — the artifact says "various improvements" without specifics.
- **Security-sensitive** — the change touches authentication, authorization, or data access in ways that might be sensitive to communicate openly.
- **Unclear reversal** — appears to undo something previously communicated, but the original state is not referenced.
- **Potentially regulated territory** — looks like it might touch GxP, PV, or labeling; when in doubt, route to a human.

### Failure modes to avoid

- **Over-communicating to look thorough.** A communications system's job is to reduce cognitive load, not demonstrate its own work. If in doubt, favor `ARCHIVE` unless a specific signal above is present.
- **Under-communicating because "they'll find out."** If a real workflow or experience changes, communicate.
- **Routing "I'm not sure" to `COMMUNICATE`.** Use `ESCALATE` instead.

### Confidence calibration

- `COMMUNICATE` with confidence ≥ 0.75: proceed.
- `COMMUNICATE` with confidence 0.5–0.75: proceed but flag `low_confidence: true` for HITL sampling.
- `ARCHIVE` with confidence ≥ 0.6: archive with reason.
- Anything below those thresholds, or active uncertainty: `ESCALATE`.

---

## Gate 2 — Is this change ripe to communicate now?

**Owner:** SignalScribe
**Decision verbs:** `RIPE` | `HOLD_UNTIL(date)` | `HOLD_INDEFINITE`

### What this decision means

A change that's worth communicating is not automatically worth communicating *today*. A feature flagged to 1% of internal users is not the same as one ramping to GA next week. Communicating too early creates noise about a state that may never ship. Communicating too late creates surprise. The decision is: *"is the timing right to put this in front of BU leaders now?"*

### Signals that favor `RIPE`

- **Imminent user-visible rollout** — GA is within ~30 days, or a phased rollout begins within ~14 days.
- **A decision window is open** — BU heads may need to prepare teams, update documentation, or weigh in on rollout sequencing.
- **The change has shipped and was not previously communicated** — post-hoc awareness is still useful.
- **A dependency, documentation, or training artifact is now available.**
- **A previous `HOLD_UNTIL` date has arrived** and no signals have changed.

### Signals that favor `HOLD_UNTIL(date)`

- **Early-stage flag rollout** (<10% internal) with no imminent ramp.
- **Feature still being tuned** — behavior may change before GA.
- **Rollout window scheduled but far out** (>60 days) — hold until ~30 days before rollout unless P0.
- **Dependency not ready** — related documentation, training, or support material is still being authored.
- **Change blocked on approvals** — regulatory, legal, or leadership approval pending.

**When choosing `HOLD_UNTIL`, supply:** (a) the date to re-evaluate, and (b) the signal that would trigger re-evaluation.

### Signals that favor `HOLD_INDEFINITE`

- **Change is speculative** — marked as "exploring" or "prototype" with no committed path.
- **Change has been explicitly deferred** or deprioritized.
- **Change is contingent on external events** with no known timeline.

`HOLD_INDEFINITE` items are not forgotten — they go into a backlog reviewed periodically via `/pending`.

### Failure modes to avoid

- **Communicating experiments as if they were plans.** Hold until they graduate.
- **Holding indefinitely as a way to avoid a hard `ARCHIVE` decision.** If a change genuinely isn't worth communicating, archive it.
- **Missing the communication window.** When in doubt, `RIPE` with a note about early rollout is better than `HOLD_UNTIL` that crosses the rollout start.

---

## Gate 3 — Is my understanding clear enough to hand off?

**Owner:** SignalScribe
**Decision verbs:** `READY` | `NEED_CLARIFICATION(questions)` | `UNRESOLVABLE`

### What this decision means

Even if a change passes gates 1 and 2, the *interpretation* SignalScribe has produced may not be good enough to hand to BUAtlas. A muddled ChangeBrief produces muddled BU personalizations and poor notifications. The question is: *"Do I have enough to produce a useful message? Or should I go back, ask, or give up?"*

This gate is self-reflective. SignalScribe evaluates its own output.

### Signals that favor `READY`

- **Before/after behavior is concretely described.**
- **Impact areas are named, not gestured at** — "affects order submission for specialty pharmacy" beats "affects some workflows."
- **Timeline is specified** — even "Q3" is enough.
- **Confidence score ≥ 0.75** on the ChangeBrief as a whole.
- **Required actions, if any, are identifiable.**
- **Source citations support every non-trivial claim.**

### Signals that favor `NEED_CLARIFICATION`

- **Vague behavior description** — "improved," "optimized," "updated" without specifics.
- **Impact is inferred, not stated** — the artifact doesn't say what's affected; SignalScribe is guessing.
- **Timeline references are inconsistent** — the title says May 1, the body says "rolling out throughout Q3."
- **Key actors are missing** — no indication of who owns the change, who to ask, what team is affected.
- **Confidence score is 0.5–0.75.**

Supply specific, answerable questions — not "can you clarify?" but "does this change affect only US-region submissions, or all regions?"

### Signals that favor `UNRESOLVABLE`

- **Artifact is internally contradictory** and no external sources resolve it.
- **Artifact references documents that cannot be retrieved** and the referenced content is load-bearing.
- **Confidence < 0.5** after multiple interpretation attempts.
- **Change requires specialized domain knowledge** neither the artifact nor tools can surface.

### Failure modes to avoid

- **Proceeding with muddy interpretations.** When in doubt, `NEED_CLARIFICATION`.
- **Asking too many questions.** Aim for ≤3 sharp questions.
- **Using `NEED_CLARIFICATION` to avoid interpretive judgment.** Some ambiguity is normal; interpret confidently and mark uncertainty explicitly.

---

## Gate 4 — Is this BU actually affected?

**Owner:** BUAtlas (per-BU invocation)
**Decision verbs:** `AFFECTED` | `ADJACENT` | `NOT_AFFECTED`

### What this decision means

The BU registry pre-filter surfaces *candidate* BUs. But candidate does not mean affected. "My team uses the product that changed" is not the same as "my team's work will be different because of this change." BUAtlas's first responsibility for each candidate BU is to distinguish *real impact* from *topical proximity*.

This is the single most important quality gate in the system. False positives here produce "not relevant" feedback from BU heads and train them to ignore notifications.

### Signals that favor `AFFECTED`

- **The change touches a workflow the BU executes.**
- **The change alters an output the BU consumes** — a report format, a data feed, an API contract.
- **The change requires preparation the BU must do** — update training, SOPs, notify field teams, prepare FAQs.
- **The change creates a decision the BU must make** — opt in, opt out, configure, prioritize.
- **The change has a visible rollout inside the BU's user base.**
- **The BU owns or co-owns the affected product area.**

### Signals that favor `ADJACENT`

- **The BU uses the broader product but not the specific surface that changed.**
- **The change might theoretically interact with the BU's work but no concrete mechanism is identified.**
- **The BU has historical interest in the product area but no current active use.**
- **The BU would want to know "for awareness" but has no action to take.**

`ADJACENT` is legitimate — does not produce a push notification, may produce a digest line.

### Signals that favor `NOT_AFFECTED`

- **Registry match was on a stale relationship** — BU once owned this area but transferred it.
- **Keyword overlap is coincidental** — the change and the BU share a term but refer to different concepts.
- **Change is scoped to a user segment that excludes the BU.**

### Failure modes to avoid

- **Defaulting to `AFFECTED` to be safe.** The frame is *"would this BU head thank me for sending this, or curse me?"* When in doubt, choose `ADJACENT`.
- **Confusing topical match for functional impact.** Ask: *what will this BU's people do differently because of this change?* If the answer is "nothing concrete," it's `ADJACENT` or `NOT_AFFECTED`.
- **Inheriting the pre-filter's optimism.** Pre-filter is tuned for recall. It is BUAtlas's job to apply precision.

### Confidence calibration

- `AFFECTED` requires identifying at least one concrete mechanism of impact.
- Confidence < 0.6 on `AFFECTED` → downgrade to `ADJACENT` and note uncertainty.
- Confidence < 0.5 on any decision → `ESCALATE` to HITL.

---

## Gate 5 — Is the drafted message worth this BU head's attention?

**Owner:** BUAtlas (per-BU invocation, after gate 4 returns `AFFECTED`)
**Decision verbs:** `WORTH_SENDING` | `WEAK` | `NOT_WORTH`

### What this decision means

Even when a BU is genuinely affected, the message BUAtlas has drafted may not be worth sending. A notification that cannot clearly articulate *why this matters to you* and *what, if anything, you should do* is worse than no notification — it trains the recipient to tune out.

### Signals that favor `WORTH_SENDING`

- **The "why it matters" sentence names a specific BU-relevant consequence** — not "this may affect your team" but "your field reps will need updated talking points for the May forum."
- **The recommended action is concrete and owner-identified.**
- **The message length matches the message weight** — short for awareness, medium for actions required, long only when necessary.
- **The timing reference is specific enough to act on.**
- **A BU head reading this in 20 seconds could walk away knowing the one thing they need to do.**

### Signals that favor `WEAK`

- **"Why it matters" is generic** — could be sent to any BU unchanged.
- **Recommended action is vague** — "please review" without specifying what to review for.
- **The message restates the ChangeBrief without BU-specific framing.**
- **The message is defensively hedged** — "may," "could," "might potentially" to the point no one can tell the actual claim.

`WEAK` signals regeneration before sending, either by BUAtlas retry or HITL.

### Signals that favor `NOT_WORTH`

- **Affected technically but impact is trivially small.**
- **The BU's OKRs and current priorities make this a distraction.**
- **Adding this notification to recent volume would violate noise control.**

`NOT_WORTH` items may go into a digest, or be marked for delegate notification only.

### Failure modes to avoid

- **Marking everything `WORTH_SENDING` because gate 4 said `AFFECTED`.** Affected + weak draft ≠ worth sending.
- **Using `NOT_WORTH` to second-guess gate 4.** `NOT_WORTH` is about the *message*, not the *impact*. Weak draft of real impact → `WEAK`, not `NOT_WORTH`.
- **Hedging the self-critique.** This is where quality is actually decided.

### Confidence calibration

- `WORTH_SENDING` with confidence 0.6–0.75 → proceed but flag for HITL sampling.
- `WEAK` → orchestrator requests regeneration once; if still `WEAK`, HITL.

---

## Gate 6 — Is now the right time to send this?

**Owner:** PushPilot
**Decision verbs:** `SEND_NOW` | `HOLD_UNTIL(time)` | `DIGEST` | `ESCALATE`

### What this decision means

A correctly-interpreted, genuinely-relevant, well-drafted message can still be sent at the wrong moment. Quiet hours, weekends, crises, mid-submission windows, recent notification fatigue — all argue for holding, digesting, or escalating.

*Note on agent vs. code split:* The agent's job is to **decide** what should happen and **explain why**. The code's job is to **enforce invariants** policy forbids (never send during documented quiet-hours, never exceed per-BU weekly rate cap). If agent says `SEND_NOW` but policy forbids it, policy wins and result is `HOLD_UNTIL` with a policy reason.

### Signals that favor `SEND_NOW`

- **Priority is P0 or P1** and recipient is within working hours.
- **Rollout window is imminent** — delay would push delivery past the event.
- **No quiet-hours conflict, no rate-limit pressure, no dedupe hit.**
- **Message is time-sensitive** — "decision needed by Friday."

### Signals that favor `HOLD_UNTIL(time)`

- **Recipient is in quiet hours** — hold until end of quiet window.
- **After-hours Friday and the change is not urgent** — hold until Monday 9 AM recipient-local.
- **Recipient has on-calendar busy signal** (vacation, earnings, submission window) — hold until window ends.
- **Message is a weekly-cadence update** that should land predictably.

Supply time and reason.

### Signals that favor `DIGEST`

- **Priority is P2 (awareness-only)** — digest is the natural channel.
- **Recipient has opted into digest format.**
- **Notification volume for this recipient this week is already high.**
- **Multiple related changes are pending** — bundle them.

### Signals that favor `ESCALATE`

- **Dedupe conflict** with a recent send — human decides whether this supersedes.
- **Policy hook flagged content** after drafting — late-detected restricted term.
- **Rate limit would be breached** — human decides which to defer.
- **PushPilot itself is uncertain** — timing signals argue plausibly in opposite directions.

### Failure modes to avoid

- **Optimizing for "send fast" at the expense of recipient attention.** Faster is not better.
- **Defaulting to `SEND_NOW` because the message is "ready."** Content-ready and moment-ready are different.
- **Using `DIGEST` as a way to punt.** `HOLD_UNTIL` is for timing; `DIGEST` is for format-fit.
- **Overriding policy invariants via reasoning.** Policy-enforced rules cannot be reasoned around.

---

## Cross-cutting principles

### Principle 1 — Recipient attention is the scarce resource

Every gate has the option to stop the message. The default bias is toward *not sending* unless the signals to send are concrete and specific. A missed notification is a measurable cost (coverage). An unwanted notification is an unmeasurable cost (eroded trust). Optimize for the one we can measure, tightly.

### Principle 2 — Uncertainty is information, not failure

`ESCALATE`, `HOLD_UNTIL`, `NEED_CLARIFICATION`, `WEAK` are first-class outputs. An agent that always produces a decisive answer is a worse agent when underlying information is uncertain.

### Principle 3 — Decisions must be reasoned, not announced

Every decision includes a short reason naming specific signals. "The change is not ripe" is useless; "flag at 2% internal, no ramp scheduled, HOLD_UNTIL ramp announcement" is useful.

### Principle 4 — Gates do not second-guess upstream gates

BUAtlas does not re-decide whether a change is worth communicating. PushPilot does not re-decide whether a message is worth sending. Each gate owns its decision, trusts upstream decisions, and adds its own judgment. If an upstream decision was wrong, the fix is HITL, not downstream override.

### Principle 5 — Policy is the floor, not the ceiling

Code-enforced policies are invariants. Agents reason within them. Agents can be *more* conservative than policy (hold when policy would allow send), but never less. Conflict → policy wins, logged for review.

---

## What this document is *not*

- **Not a rulebook.** Signals above are heuristics, not complete specifications. Agents still need judgment.
- **Not final.** Draft v1. Must be reviewed with a real AbbVie change-management or internal-communications professional.
- **Not exhaustive.** Edge cases will surface during pilot. Update this document, regenerate prompts, re-eval.

---

## Revision history

| Version | Author | Summary |
|---|---|---|
| v1 | Oṁ | Initial draft covering all six gates with signals, failure modes, confidence calibration, cross-cutting principles. |
