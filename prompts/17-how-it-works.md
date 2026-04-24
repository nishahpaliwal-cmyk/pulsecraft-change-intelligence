# Prompt 17 — How It Works (Scrollytelling Tab)

> **Character.** Build the third tab — "How it works" — a scroll-driven narrative that explains *why* PulseCraft is shaped the way it is, who it's for, and what problem it solves. The Demo tab shows the system running. The Architecture tab shows its structure. This tab shows its story.
>
> **Why now.** The Demo tab and Architecture tab are live, polished, and truthful. They answer "what does it do?" and "how is it built?". Neither answers "why does it exist?" or "what problem does it solve?" A Head of AI judging PulseCraft needs all three. This tab completes the narrative.
>
> **How to use.** Paste below the `---` line into Claude Code. Fully autonomous.
>
> **Expected duration:** 3-4 hours. Pure frontend work. No backend touches.
>
> **Budget:** Zero LLM cost.

---

# Instructions for Claude Code

Build the "How it works" tab. Three-chapter scrollytelling page using scroll-paced mechanics (each chapter triggers its animations when entering viewport) with a visceral opening. Reuse the Architecture tab's visual vocabulary and design system.

**Scope:** pure frontend. Stay in `src/pulsecraft/demo/static/`. Zero backend touches unless tab routing requires a minor server.py addition.

## Environment discipline

`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`. No new dependencies. Use IntersectionObserver for scroll triggers (vanilla browser API, no GSAP or framework).

## Design goals

### For a Head of AI reading top to bottom

A Head of AI or senior technical stakeholder who scrolls this page from top to bottom should leave with:

1. **A moment of recognition** — "yes, I've lived that problem" (visceral opening)
2. **A clear mental model** — three agents, six gates, four hooks, with the pipeline assembling in front of them
3. **The architectural principle stated explicitly** — agents express preferences, code enforces invariants, both are logged
4. **Understanding of human-in-the-loop** — what triggers it, what operators do, why it's architecturally first-class
5. **A sense of finish** — the story closes with the outcome: "nothing silent, nothing unaudited, every decision defensible"

Reading time target: 5-7 minutes at natural scroll pace.

### For someone scrolling quickly

Each chapter should land its main idea visually in the first screen, even if the reader doesn't wait for supporting animations. Chapter 1 opens with dramatic typography. Chapter 2 opens with pipeline structure. Chapter 3 opens with the operator review panel.

A fast scroller gets the three-beat story: *problem → solution → safeguard*.

## Chapter 1 — The problem

**Opening (fills first viewport):**

Large typographic treatment. Fraunces 500 at ~56px. Centered or left-anchored with strong presence.

Proposed opening copy:

```
Your BU lead missed the change.

Again.
```

Subtle. Breathing. Lots of whitespace above and below. The two lines should feel like a punch, not a statement.

**Supporting paragraph (fades in as the opening lands):**

Inter 400 at ~19px, max-width ~640px, centered horizontally below the opening. Two paragraphs:

> At enterprise scale, product ships changes every day. Some matter to your BU. Most don't. None of them arrive with a label that says *this affects you*.

> By the time someone notices — usually a customer, usually upset — the change is live, the field hasn't been briefed, and the BU lead is explaining why they didn't know.

**Ambient visualization (below the text, enters viewport together):**

A subtle horizontal strip of small colored dots flowing from left to right. Most dots are dim gray. Every few seconds, a bright dot appears briefly, then fades. Every dozen or so dots, a red dot appears — then fades with a small, almost imperceptible wobble.

- Dim gray dots: changes correctly ignored (noise)
- Bright momentary dots: changes correctly caught (signal)
- Red wobbly dots: changes missed (the problem)

Keep the animation atmospheric, not attention-grabbing. 6-8 dots visible at any moment, flowing at ~30 seconds across full width. Uses CSS transforms only — no JS per-dot.

**Closing line (before chapter transition):**

Inter 500 at ~22px, centered, subtle color (text-secondary):

```
Change communication is a routing problem.
PulseCraft is change infrastructure.
```

The reader should scroll into Chapter 2 feeling: *yes, I recognize this; how does PulseCraft solve it?*

## Chapter 2 — The approach and the pipeline

This chapter is the longest — it answers "how does PulseCraft route changes?" It reuses the Architecture tab's visual vocabulary but adds narrative scaffolding Architecture tab can't carry.

**Opening (as chapter enters viewport):**

Heading in Fraunces 500 at ~40px:

```
Three specialists. Six judgments. Four guardrails.
```

Subtitle in Inter 400 at ~18px, max-width ~720px:

> Rather than one agent guessing, PulseCraft uses three specialists working in sequence. Each answers specific questions about a change. Code enforces what agents can't reliably judge.

**Three agents introduced (as the next viewport enters):**

Three horizontal cards, side-by-side at wide viewports, stacked on narrow. Each ~320px wide.

Each card:
- Agent avatar as a colored vertical bar (3-4px, left edge) in the agent's color
- Agent name in Fraunces 500 24px
- One-line role tagline in Inter 400 17px
- Three gates listed as small pills

Card content:

**SignalScribe** (purple #534AB7)
Tagline: *"Is this change worth communicating at all?"*
Gates: `worth communicating?` · `ripe?` · `clear?`

**BUAtlas** (teal #0F6E56)
Tagline: *"Which BUs does it affect? What do they need to know?"*
Gates: `affected?` · `worth sending?`
Badge below: `parallel per-BU`

**PushPilot** (coral #993C1D)
Tagline: *"When and how should each BU hear about it?"*
Gates: `delivery timing`

Cards animate in with 100ms stagger on viewport entry. Each card fades + slight scale (0.95 → 1). 400ms each.

**The pipeline visualization (as the next viewport enters):**

A simplified version of the Architecture tab diagram — the same nodes and connectors, but smaller and oriented for reading alongside prose. About 60% of the Architecture tab's complexity.

Layout: horizontal flow, roughly 80% of viewport width, height ~240px. Nodes show just their name and color bar (no gate labels, no detail text — this is a structural overview). Connectors draw when they enter viewport.

On the left side (40% of the row): a narrative block that reveals progressively as the diagram builds:

```
A change artifact arrives.                      [Ingest lights up]

Pre-ingest redaction checks for sensitive data. [Ingest hook fires]

SignalScribe reads the artifact and answers three questions:
is this worth communicating, is it ripe, is it clear?  [SignalScribe node lights up]

If any answer is no — ARCHIVE, HOLD, or ESCALATE — the pipeline stops here. [Archive/Hold arrow pulses]

If all three are yes, we look up which BUs could be affected. [Arrow to BUAtlas draws]

BUAtlas fans out — one parallel instance per candidate BU —
and each decides if its BU is really affected, and whether
the change is worth sending to them specifically.          [BUAtlas stacked cards pulse]

PushPilot then picks timing and channel — per BU.          [PushPilot lights up]

And before anything leaves the system...                    [Arrow to pre_deliver]
```

The narrative block is plain text (no icons, no boxes). Each paragraph appears on scroll via IntersectionObserver. When a paragraph becomes visible, the corresponding diagram element pulses or lights up (just briefly — 400ms glow).

**The architectural principle callout (as the reader scrolls past the diagram):**

Dedicated treatment. Large Fraunces italic, center-aligned, max-width ~820px. Pale cream background container (same as Architecture tab callout).

```
Agents express preferences based on context.
Code enforces invariants based on policy.
When they diverge, policy wins — and both are logged.
```

Below in Inter 400 17px:

> The pre_deliver hook is the primary site of this divergence. PushPilot says "send this now." pre_deliver runs — checks the system clock, checks the recipient's quiet hours, scans for restricted terms. If policy overrides PushPilot's preference, the agent decision is recorded alongside the enforced decision. Over time, this enables calibration: are agent preferences drifting? Are thresholds set correctly?

This callout is Chapter 2's climax. Give it vertical breathing room — at least 120px above and below. It should feel like the reader pauses here.

## Chapter 3 — Where humans come in

**Opening (as chapter enters viewport):**

Heading in Fraunces 500 at ~36px:

```
Not every decision should be automatic.
```

Subtitle in Inter 400 at ~18px, max-width ~720px:

> Confident systems know when to defer. Anything uncertain, anything sensitive, anything high-stakes — routes to human review. Three-agent reasoning plus four guardrail hooks, and then a human on the final call where it matters.

**What triggers HITL (the concrete list):**

Heading in Fraunces 500 at ~22px: `When PulseCraft pauses for a human`

Five triggers, each with a one-line explanation. Each trigger is a small card with:
- A short label (Inter 600, 14px, tinted amber)
- A one-line explanation (Inter 400, 16px)

The five:

- **priority_p0** — The BU head has marked this class of change as requiring human review before delivery.
- **mlr_sensitive** — The drafted message contains regulated language. Medical, legal, or compliance review needed before send.
- **confidence_below_threshold** — An agent's confidence fell below the configured operating threshold for that gate. Let a human check the reasoning.
- **restricted_term** — A term in the artifact or the drafted message appears on the restricted list. Could be a product name, a brand constraint, or an internal code word.
- **dedupe_conflict** — This change is ambiguously similar to one already sent. Human decides whether it's a duplicate or genuinely new.

These cards animate in on viewport entry with 80ms stagger.

**What operators see and do (with a preview):**

Below the triggers, a smaller Inter 400 paragraph:

> An operator reviews the full decision trail — every gate, every reason, every hook verdict — and acts. Four actions: approve, reject, edit, or send a question back to the SME queue.

Then a **stylized preview of the operator review panel** (not functional, just visual):

- Card shell matching the Demo tab's operator review panel visual
- Headers showing: a sample change, "awaiting review" status with `mlr_sensitive` trigger
- Four action buttons (Approve / Reject / Edit / Answer question) in the consistent Demo tab styling
- Italic note: *In production, operators receive a notification and act via the pulsecraft approve CLI or a dashboard.*

The preview doesn't need to be interactive — it's a snapshot. If interactions are easy (e.g., the buttons highlight on hover with no real action), add them; otherwise static is fine.

**The audit trail closing paragraph:**

Below the operator preview, in Inter 400 17px:

> Every agent decision, every hook verdict, every operator action — logged in an append-only audit trail. Any outcome can be replayed step-by-step with `pulsecraft explain <change_id>`.
>
> Nothing silent. Nothing unaudited. Every decision defensible.

**The closing heading:**

Fraunces 500 at ~32px, centered:

```
That's PulseCraft.
```

Subtle, conclusive. Generous vertical space after.

## Cross-chapter — the closing CTA

Below the last heading, a small CTA area:

Two links, side-by-side on wide, stacked on narrow:

- `Watch it run →` (links to Demo tab — switches tab, not full page navigation)
- `Explore the architecture →` (links to Architecture tab)

Styled as secondary buttons matching Demo tab's CTA styling. 16px Inter 500, subtle borders, warm cream background.

No footer heavy element — the closing should feel like the end of a story.

## Layout and typography

### Layout

- Content column: max-width 960px, centered horizontally
- Side margins: 24px on narrow viewports, growing to ~80px on wide
- Full-width elements (ambient dot strip, pipeline visualization): can extend to 80% of viewport width even when main content is narrower

### Typography

Fraunces 500 for headings (40-56px for chapter openers, 24-32px for section headings).
Inter 400 for body prose (17-19px).
Inter 500/600 for small labels and buttons.
JetBrains Mono 400 for code references (`pulsecraft explain`).

### Color palette (identical to Demo/Architecture tabs)

```
Page background     #FAF7F2 warm cream
Text primary        #1F1D18
Text secondary      #5F5B52
Text tertiary       #8D877B
Agent accents       (same as other tabs: purple, teal, coral)
Hook amber          #854F0B
```

## Scroll mechanics

Use IntersectionObserver with a threshold of ~0.3 (element is considered "in view" when 30% visible). When a tracked element enters the observer's threshold:

1. Add a CSS class `.is-visible` to the element
2. CSS transitions handle the actual animation (fade + translate + any element-specific reveal)

Each chapter's animations trigger when the chapter's top enters viewport. Within a chapter, individual elements can have their own observers for staggered reveals.

**Do not use scroll-driven animations** (like `@scroll-timeline` or scroll-linked JS). Use scroll-paced: when element enters view, it plays; it doesn't pause when scrolling stops.

**Reduced motion:** respect `prefers-reduced-motion: reduce`. When set, all transitions become 200ms fades with no transforms. IntersectionObserver still fires the `.is-visible` class but the transitions are reduced to simple opacity.

## Files to create

### `src/pulsecraft/demo/static/how-it-works.html`

New HTML fragment (or full page if architecture.html is a full page). Three main sections:

```html
<section class="how-chapter how-chapter--problem" id="chapter-problem">
  <!-- Chapter 1 content -->
</section>

<section class="how-chapter how-chapter--pipeline" id="chapter-pipeline">
  <!-- Chapter 2 content -->
</section>

<section class="how-chapter how-chapter--humans" id="chapter-humans">
  <!-- Chapter 3 content -->
</section>

<section class="how-closing">
  <!-- Closing heading + CTAs -->
</section>
```

### `src/pulsecraft/demo/static/how-it-works.css`

Chapter styling, typography, animations (keyframes), layout media queries, reduced-motion overrides, the agent card styling (reuse from architecture.css where possible), pipeline visualization styling (lighter version of Architecture tab), operator panel preview styling, ambient dot strip styling.

### `src/pulsecraft/demo/static/how-it-works.js`

IntersectionObserver setup, scroll-into-view handlers for "Watch it run" and "Explore the architecture" CTAs (trigger tab switch, not page navigation), ambient dot strip animation loop (or CSS keyframes if possible — prefer CSS).

### Modify `src/pulsecraft/demo/static/index.html`

The "How it works" tab button (currently inactive per prompt 16) now becomes active. Clicking it loads the how-it-works content into view.

### Modify `src/pulsecraft/demo/static/app.js`

Tab switcher logic — when "How it works" tab is clicked, hide Demo and Architecture content, show the how-it-works section. Preserve Demo tab state (don't reset in-progress runs).

## Step-by-step work plan

### Step 1 — Read the architecture of the existing tabs

```
cat src/pulsecraft/demo/static/architecture.html
cat src/pulsecraft/demo/static/architecture.css | head -100
cat src/pulsecraft/demo/static/architecture.js | head -50
```

Understand the design system and tab-switching plumbing.

### Step 2 — Build Chapter 1 (the problem)

Typographic opening + ambient dot strip + closing line. Simplest chapter. Get the reduced-motion path right here — it propagates to the rest.

### Step 3 — Build Chapter 2 opening and agent cards

Three-agent card layout. Color accents, taglines, gate pills. Stagger animation on viewport entry.

### Step 4 — Build Chapter 2 pipeline + narrative

This is the biggest piece. Simplified pipeline diagram on the right, prose narrative on the left, synchronized reveals.

Key implementation detail: the narrative prose appears in paragraphs. Each paragraph has a `data-highlights` attribute naming which diagram nodes should pulse when that paragraph becomes visible. IntersectionObserver on paragraphs; when visible, the observer reads `data-highlights` and triggers brief pulse animations on the named nodes.

### Step 5 — Build Chapter 2 callout

Architectural principle callout — same treatment as the Architecture tab's callout. Pale cream container, Fraunces italic. Give it the breathing room it needs.

### Step 6 — Build Chapter 3 (humans)

Opening + five trigger cards + operator preview + audit paragraph + closing heading.

The operator preview can reuse the exact CSS from Demo tab's operator panel — copy the visual, don't wire functionality.

### Step 7 — Closing CTAs and tab switch wiring

Two buttons. Clicking them triggers tab switch via existing tab-switcher logic.

### Step 8 — Reduced motion pass

Verify `prefers-reduced-motion: reduce` reduces all transitions to simple fades. Check each chapter's animations individually.

### Step 9 — Responsive pass

Verify at 1440px, 1200px, 900px, 600px viewports. Agent cards stack, pipeline visualization rescales, typography sizes work.

### Step 10 — Activate the "How it works" tab

In index.html, remove any `disabled` or `aria-disabled` from the tab button. Wire the click handler.

### Step 11 — Verification

Open http://localhost:8000, click "How it works" tab. Scroll from top to bottom slowly. Confirm:

- Chapter 1 opens with the punchline ("Your BU lead missed the change. Again.")
- Dot strip animates ambiently
- Chapter 2 introduces three agent cards cleanly
- Pipeline visualization + synchronized prose reveals land
- Callout reads as a quote block, with proper breathing room
- Chapter 3 explains HITL with five trigger cards and operator preview
- Closing CTAs work — clicking Demo or Architecture switches tabs
- Tab switch preserves state (clicking back to Demo shouldn't reset any in-progress run)

Scroll back to top. Reload page. Everything should still work cleanly from a fresh load.

### Step 12 — Screenshots

Save four screenshots to `design/demo/screenshots/17/`:

- `how-chapter-1-opening.png` — "Your BU lead missed the change. Again." as the reader first sees it
- `how-chapter-2-agents.png` — three agent cards displayed
- `how-chapter-2-pipeline.png` — simplified pipeline with prose reveals
- `how-chapter-3-hitl.png` — triggers + operator preview + closing

### Step 13 — Tests

```
.venv/bin/pytest tests/ -q -m "not llm and not eval" 2>&1 | tail -3
```

Should show 642 passing (unchanged).

### Step 14 — Commit

```
feat(demo): How it works scrollytelling tab (prompt 17)

Three-chapter narrative tab explaining PulseCraft's purpose and flow.

Chapter 1 — The problem: typographic opening ("Your BU lead missed
the change. Again.") with supporting prose and ambient dot-strip
visualization showing changes flowing past, most ignored correctly,
a few caught, some missed.

Chapter 2 — The approach and the pipeline: three specialists
introduced (SignalScribe, BUAtlas, PushPilot) with their gates.
Simplified pipeline visualization revealing alongside synchronized
prose. The agent-vs-code architectural principle gets a dedicated
quote-block callout.

Chapter 3 — Where humans come in: HITL triggers (priority_p0,
mlr_sensitive, confidence_below_threshold, restricted_term,
dedupe_conflict) with explanations. Operator review panel preview
matches Demo tab's visual. Closes with the audit trail
("nothing silent, nothing unaudited, every decision defensible").

Uses IntersectionObserver for scroll-paced chapter reveals.
Respects prefers-reduced-motion. Closing CTAs link back to Demo
and Architecture tabs.

All visual elements consistent with existing Demo and Architecture
tab design vocabulary. No backend changes. Test count unchanged
at 642.

Screenshots at design/demo/screenshots/17/.
```

Do not push.

## Rules

- **Pure frontend.** Zero backend touches except tab routing.
- **Reuse design tokens.** Colors, typography, spacing — all match existing tabs.
- **Operator preview is static.** Don't wire functionality — it's a visual snapshot, not an interactive element.
- **Reduced motion is mandatory.** Test it.
- **Autonomous.** Do not hand off mid-build.
- **Visual verification required.** Screenshot before declaring done.

## Final report

1. Files created (list).
2. Chapter 1 verification — does the opening land as a punch?
3. Chapter 2 verification — does the agent-vs-code callout feel like the story's climax?
4. Chapter 3 verification — does the HITL story feel complete and well-explained?
5. Cross-chapter — do closing CTAs work to switch tabs?
6. Reduced-motion check — one line confirming.
7. Four screenshots saved — confirm filenames.
8. Test count unchanged at 642.
9. Commit hash.
10. Honest self-assessment paragraph: does this tab add new narrative value beyond Demo + Architecture? Or does it feel redundant? What's still thin?
11. Next: "Demo presentation prep."

---

## [Post-commit] Save this prompt file

After the commit lands: **"Save prompt 17 to `prompts/17-how-it-works.md`? (yes/no)"**

If yes: write verbatim, commit with `chore(prompts): archive prompt 17 in repo`.
