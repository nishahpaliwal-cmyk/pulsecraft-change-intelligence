/**
 * PulseCraft "How it works" — three-chapter scrollytelling tab.
 * Exports initHowItWorks / teardownHowItWorks for app.js.
 */

let _observer = null;

function _buildDOM() {
  return `
<div class="how-wrap">

  <!-- Chapter 1: The system -->
  <section class="how-chapter how-ch1" id="how-ch1">
    <div class="how-eyebrow">The system</div>
    <h2 class="how-ch1__headline">
      <span class="how-word w1">Three</span> <span class="how-word w2">specialists.</span><br>
      <span class="how-word w3">Four</span> <span class="how-word w4">guardrails.</span><br>
      <span class="how-word w5">One</span> <span class="how-word w6">deterministic</span> <span class="how-word w7">core.</span>
    </h2>
    <p class="how-ch1__bridge">Every change — routed, reasoned, and recorded.</p>
    <p class="how-body">Product ships changes constantly. Some matter to your BU. Some don't. PulseCraft sorts signal from noise with three LLM specialists working in sequence, four deterministic hooks enforcing policy, and an append-only audit trail capturing every decision.</p>
    <p class="how-body">Nothing silent. Nothing unaudited. Every routing call defensible.</p>

    <div class="how-ch1__signals" aria-label="Unfiltered change signals — the signal is buried in the noise">
      <span class="how-signal how-signal--dim">release note · platform</span>
      <span class="how-signal">feature flag · analytics</span>
      <span class="how-signal how-signal--dim">work item · backend</span>
      <span class="how-signal how-signal--highlight">pricing tier change · affects 3 BUs</span>
      <span class="how-signal how-signal--dim">doc update · onboarding</span>
      <span class="how-signal how-signal--dim">incident · infra</span>
      <span class="how-signal">release note · mobile</span>
      <span class="how-signal how-signal--dim">flag · experiment A/B</span>
      <span class="how-signal how-signal--dim">work item · data pipeline</span>
    </div>

    <p class="how-ch1__thesis">
      Change communication is a routing problem.<br>
      PulseCraft is change infrastructure.
    </p>
  </section>

  <!-- Chapter 2: The pipeline -->
  <section class="how-chapter how-ch2" id="how-ch2">
    <div class="how-eyebrow">The approach</div>
    <h2 class="how-ch2__headline">Three specialists. Six judgments.<br>Four guardrails.</h2>
    <p class="how-body">Rather than one agent guessing, PulseCraft uses three specialists working in sequence. Each answers specific questions about a change. Code enforces what agents can't reliably judge — and every enforcement is logged alongside the agent's original preference.</p>

    <div class="how-agents" role="list" aria-label="Agent pipeline">
      <div class="how-agent how-agent--ss" role="listitem">
        <div class="how-agent__bar" aria-hidden="true"></div>
        <div class="how-agent__num">01</div>
        <div class="how-agent__name">SignalScribe</div>
        <div class="how-agent__tagline">Is this change worth communicating at all?</div>
        <div class="how-agent__gates">Gates 1 · 2 · 3</div>
        <ul class="how-agent__questions">
          <li>Worth communicating?</li>
          <li>Ripe — complete enough to act on?</li>
          <li>Clear — any open questions?</li>
        </ul>
        <div class="how-agent__verbs">COMMUNICATE · ARCHIVE · ESCALATE · HOLD</div>
      </div>
      <div class="how-pipeline-arrow" aria-hidden="true">
        <svg width="28" height="16" viewBox="0 0 28 16" fill="none"><path d="M1 8h22M17 2l8 6-8 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div class="how-agent how-agent--ba" role="listitem">
        <div class="how-agent__bar" aria-hidden="true"></div>
        <div class="how-agent__num">02</div>
        <div class="how-agent__name">BUAtlas</div>
        <div class="how-agent__tagline">Which BUs does it affect? What do they need to know?</div>
        <div class="how-agent__gates">Gates 4 · 5</div>
        <ul class="how-agent__questions">
          <li>Which BUs are affected?</li>
          <li>Worth personalizing for each?</li>
        </ul>
        <div class="how-agent__verbs">AFFECTED · ADJACENT · NOT_AFFECTED · WORTH_SENDING</div>
      </div>
      <div class="how-pipeline-arrow" aria-hidden="true">
        <svg width="28" height="16" viewBox="0 0 28 16" fill="none"><path d="M1 8h22M17 2l8 6-8 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div class="how-agent how-agent--pp" role="listitem">
        <div class="how-agent__bar" aria-hidden="true"></div>
        <div class="how-agent__num">03</div>
        <div class="how-agent__name">PushPilot</div>
        <div class="how-agent__tagline">When and how should each BU hear about it?</div>
        <div class="how-agent__gates">Gate 6</div>
        <ul class="how-agent__questions">
          <li>Send now, hold, or digest?</li>
          <li>Quiet hours and channel policy enforced by orchestrator</li>
        </ul>
        <div class="how-agent__verbs">SEND_NOW · HOLD_UNTIL · DIGEST</div>
      </div>
    </div>

    <div class="how-principle">
      <blockquote class="how-principle__quote">
        Agents express preferences based on context.<br>
        Code enforces invariants based on policy.<br>
        When they diverge, policy wins — and both are logged.
      </blockquote>
      <p class="how-principle__body">The <code>pre_deliver</code> hook is the primary site of this divergence. PushPilot says "send this now." The orchestrator runs — checks the clock, checks quiet hours, scans for restricted terms. If policy overrides, the agent decision is recorded alongside the enforcement. Over time, this enables calibration: are agent preferences drifting? Are thresholds set correctly?</p>
    </div>
  </section>

  <!-- Chapter 3: Where humans come in -->
  <section class="how-chapter how-ch3" id="how-ch3">
    <div class="how-eyebrow">Where humans come in</div>
    <h2 class="how-ch3__headline">Not every decision<br>should be automatic.</h2>
    <p class="how-body">Confident systems know when to defer. Anything uncertain, anything sensitive, anything high-stakes — routes to human review. Three-agent reasoning plus four guardrail hooks, and then a human on the final call where it matters.</p>

    <div class="how-hitl-list" role="list" aria-label="Conditions that trigger human review">
      <div class="how-hitl-row" role="listitem">
        <div class="how-hitl-tag">P0</div>
        <div class="how-hitl-desc">Priority-zero changes always get human eyes before delivery</div>
      </div>
      <div class="how-hitl-row" role="listitem">
        <div class="how-hitl-tag">2×</div>
        <div class="how-hitl-desc">Two weak signals in the same run — combined uncertainty triggers review</div>
      </div>
      <div class="how-hitl-row" role="listitem">
        <div class="how-hitl-tag">%</div>
        <div class="how-hitl-desc">Agent confidence below the policy threshold surfaces for operator override</div>
      </div>
      <div class="how-hitl-row" role="listitem">
        <div class="how-hitl-tag">⚑</div>
        <div class="how-hitl-desc">MLR-sensitive or regulated language flagged before reaching BU leadership</div>
      </div>
      <div class="how-hitl-row" role="listitem">
        <div class="how-hitl-tag">∑</div>
        <div class="how-hitl-desc">Rate-limit conflicts and suspected duplicates paused for operator decision</div>
      </div>
    </div>

    <div class="how-audit">
      <div class="how-audit__label">Every decision is traceable</div>
      <div class="how-audit__trail" aria-label="Example audit trail">
        <div class="how-audit__row how-audit__row--state">RECEIVED → INTERPRETED</div>
        <div class="how-audit__row how-audit__row--agent">signalscribe · gate 1 · COMMUNICATE · conf 0.91</div>
        <div class="how-audit__row how-audit__row--agent">buatlas · bu_alpha · AFFECTED · WORTH_SENDING</div>
        <div class="how-audit__row how-audit__row--hook">pre_deliver · quiet hours check · passed</div>
        <div class="how-audit__row how-audit__row--state">SCHEDULED → DELIVERED</div>
      </div>
      <p class="how-audit__close">Every agent decision, every hook verdict, every operator action — logged in an append-only audit trail. Any outcome can be replayed step-by-step with <code>pulsecraft explain &lt;change_id&gt;</code>.</p>
      <p class="how-audit__close how-audit__close--em">Nothing silent. Nothing unaudited. Every decision defensible.</p>
    </div>

    <div class="how-close">
      <h2 class="how-close__heading">That's PulseCraft.</h2>
    </div>

    <div class="how-cta">
      <p class="how-cta__text">See it run. Explore how it's built.</p>
      <div class="how-cta__btns">
        <button class="how-cta__btn" data-switch-tab="demo">Watch it run →</button>
        <button class="how-cta__btn how-cta__btn--secondary" data-switch-tab="architecture">Explore the architecture →</button>
      </div>
    </div>
  </section>

</div>
`;
}

export function initHowItWorks() {
  const root = document.getElementById('how-tab');
  root.innerHTML = _buildDOM();

  root.querySelectorAll('[data-switch-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelector(`.tab-btn[data-tab="${btn.dataset.switchTab}"]`)?.click();
    });
  });

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reducedMotion) {
    root.querySelectorAll('.how-chapter').forEach(el => el.classList.add('is-visible'));
    return;
  }

  _observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          _observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '-56px 0px 0px 0px' }
  );

  root.querySelectorAll('.how-chapter').forEach(el => _observer.observe(el));
}

export function teardownHowItWorks() {
  if (_observer) {
    _observer.disconnect();
    _observer = null;
  }
  const root = document.getElementById('how-tab');
  if (root) root.innerHTML = '';
}
