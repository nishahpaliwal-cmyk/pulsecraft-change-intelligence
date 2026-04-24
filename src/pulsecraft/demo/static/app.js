/**
 * PulseCraft demo app — vanilla JS, ES modules, no framework.
 * Handles scenario rendering, SSE streaming, and all UI state.
 */

import { initArchitecture, teardownArchitecture } from './architecture.js';

// ── Constants ──────────────────────────────────────────────────────────────

const VERB_CLASS = {
  COMMUNICATE: 'positive', RIPE: 'positive', READY: 'positive',
  AFFECTED: 'positive', WORTH_SENDING: 'positive', SEND_NOW: 'positive',
  ARCHIVE: 'negative', NOT_AFFECTED: 'negative', NOT_WORTH: 'negative',
  HOLD_UNTIL: 'warning', HOLD_INDEFINITE: 'warning', DIGEST: 'info',
  ADJACENT: 'info', WEAK: 'warning',
  NEED_CLARIFICATION: 'warning', UNRESOLVABLE: 'danger', ESCALATE: 'danger',
  FAILED: 'danger',
};

const GATE_LABEL = {
  1: 'Gate 1 · worth communicating?',
  2: 'Gate 2 · ripe?',
  3: 'Gate 3 · clear?',
  4: 'Gate 4 · affected?',
  5: 'Gate 5 · worth sending?',
  6: 'Gate 6 · delivery timing?',
};

const AGENT_LABEL = {
  signalscribe: 'SignalScribe',
  buatlas: 'BUAtlas',
  pushpilot: 'PushPilot',
};

// Rail stages: id, label, color class suffix
const RAIL_STAGES = [
  { id: 'pre_ingest',  label: 'pre_ingest hook',   color: 'hook' },
  { id: 'signalscribe', label: 'SignalScribe',      color: 'ss' },
  { id: 'post_ss',     label: 'post_agent hook',    color: 'hook' },
  { id: 'buatlas',     label: 'BUAtlas fan-out',    color: 'ba' },
  { id: 'pushpilot',   label: 'PushPilot',          color: 'pp' },
  { id: 'pre_deliver', label: 'pre_deliver hook',   color: 'hook' },
  { id: 'terminal',    label: 'Terminal state',     color: 'ok' },
];

// State → { cssClass, accentClass, title }
const STATE_META = {
  DELIVERED:    { css: 'terminal-delivered', accent: 'delivery', title: 'Delivered' },
  AWAITING_HITL:{ css: 'terminal-hitl',      accent: 'info',     title: 'Awaiting Human Review' },
  ARCHIVED:     { css: 'terminal-archived',  accent: 'neutral',  title: 'Archived' },
  HELD:         { css: 'terminal-held',      accent: 'warn',     title: 'Held' },
  DIGESTED:     { css: 'terminal-held',      accent: 'info',     title: 'Queued for Digest' },
  FAILED:       { css: 'terminal-failed',    accent: 'danger',   title: 'Pipeline Failed' },
  REJECTED:     { css: 'terminal-failed',    accent: 'danger',   title: 'Rejected' },
};

// ── State ──────────────────────────────────────────────────────────────────

let scenarios = [];
let activeScenarioId = null;
let currentRunId = null;
let currentEventSource = null;
let runStartMs = null;
let totalCostUsd = 0;
let elapsedTimer = null;
let hasRunBefore = false;

// Per-run rendering state
let buCardsMap = {};
let railDots = {};
let changeId = null;
let lastHitlTriggerType = null;

// ── Init ───────────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch('/api/scenarios');
    const data = await resp.json();
    scenarios = data.scenarios;
    renderSidebar();
    renderRail();
  } catch (e) {
    console.error('Failed to load scenarios', e);
  }

  document.addEventListener('keydown', handleKeydown);
  document.getElementById('drawer-close').addEventListener('click', closeDrawer);
  document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);

  // Tab switching
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Scroll-aware top bar shadow
  window.addEventListener('scroll', () => {
    document.getElementById('top-bar').classList.toggle('scrolled', window.scrollY > 4);
  }, { passive: true });
}

// ── Tab switching ──────────────────────────────────────────────────────────

let _activeTab = 'demo';

function switchTab(tab) {
  if (tab === _activeTab) return;
  _activeTab = tab;

  // Update tab button states
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    const isActive = btn.dataset.tab === tab;
    btn.classList.toggle('tab-btn--active', isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });

  const demoLayout  = document.querySelector('.layout');
  const archTab     = document.getElementById('arch-tab');

  if (tab === 'demo') {
    teardownArchitecture();
    demoLayout.removeAttribute('hidden');
    archTab.setAttribute('hidden', '');
  } else if (tab === 'architecture') {
    demoLayout.setAttribute('hidden', '');
    archTab.removeAttribute('hidden');
    initArchitecture();
  }
}

// ── Sidebar ────────────────────────────────────────────────────────────────

function renderSidebar() {
  const list = document.getElementById('scenario-list');
  list.innerHTML = '';
  scenarios.forEach((s, idx) => {
    const card = document.createElement('div');
    card.className = 'scenario-card';
    card.setAttribute('role', 'listitem');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', `Scenario ${idx + 1}: ${s.title}`);
    card.dataset.scenarioId = s.id;
    card.innerHTML = `
      <div class="scenario-num">${String(idx + 1).padStart(2, '0')}</div>
      <div class="scenario-title">${escHtml(s.title)}</div>
      <div class="scenario-desc">${escHtml(s.description)}</div>
      <span class="scenario-run-hint" aria-hidden="true">Run →</span>
      <div class="scenario-progress-bar" id="progress-bar-${escHtml(s.id)}"></div>
    `;
    card.addEventListener('click', () => runScenario(s.id));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); runScenario(s.id); }
    });
    list.appendChild(card);
  });
}

function updateSidebarActive(scenarioId) {
  document.querySelectorAll('.scenario-card').forEach(c => {
    const isActive = c.dataset.scenarioId === scenarioId;
    c.classList.toggle('active', isActive);
    c.classList.toggle('running', isActive);
    // Remove past-run badge while running
    if (isActive) {
      const badge = c.querySelector('.scenario-badge');
      if (badge) badge.remove();
      const running = document.createElement('span');
      running.className = 'scenario-badge running';
      running.textContent = 'running';
      c.appendChild(running);
    }
  });
}

function setScenarioBadge(scenarioId, state) {
  const card = document.querySelector(`[data-scenario-id="${scenarioId}"]`);
  if (!card) return;
  card.classList.remove('running');
  const existing = card.querySelector('.scenario-badge');
  if (existing) existing.remove();
  const meta = STATE_META[state];
  if (!meta) return;
  const stateClass = {
    'terminal-delivered': 'delivered',
    'terminal-hitl': 'hitl',
    'terminal-archived': 'archived',
    'terminal-held': 'held',
    'terminal-failed': 'failed',
  }[meta.css] || 'archived';
  const stateLabel = {
    DELIVERED: 'delivered', ARCHIVED: 'archived', AWAITING_HITL: 'awaiting review',
    HELD: 'held', DIGESTED: 'digested', FAILED: 'failed', REJECTED: 'rejected',
  }[state] || state.toLowerCase();
  const badge = document.createElement('span');
  badge.className = `scenario-badge ${stateClass}`;
  badge.textContent = stateLabel;
  card.appendChild(badge);
}

// ── Rail ───────────────────────────────────────────────────────────────────

function renderRail() {
  const track = document.getElementById('rail-track');
  track.innerHTML = '';
  railDots = {};
  RAIL_STAGES.forEach(stage => {
    const wrap = document.createElement('div');
    wrap.className = 'rail-dot-wrap';
    wrap.setAttribute('aria-label', stage.label);

    const dot = document.createElement('div');
    dot.className = 'rail-dot';
    dot.id = `rail-${stage.id}`;

    const tooltip = document.createElement('div');
    tooltip.className = 'rail-tooltip';
    tooltip.textContent = stage.label;

    wrap.appendChild(dot);
    wrap.appendChild(tooltip);
    track.appendChild(wrap);
    railDots[stage.id] = { el: dot, color: stage.color };

    wrap.addEventListener('click', () => {
      const section = document.getElementById(`section-${stage.id}`);
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

function resetRail() {
  Object.values(railDots).forEach(({ el }) => { el.className = 'rail-dot'; });
}

function setRailActive(stageId) {
  const info = railDots[stageId];
  if (!info) return;
  // Remove active from all, then set for this one
  Object.values(railDots).forEach(({ el }) => {
    el.className = el.className.replace(/\bactive-\w+\b/, '');
  });
  info.el.classList.add(`active-${info.color}`);
}

function setRailDone(stageId) {
  const info = railDots[stageId];
  if (!info) return;
  info.el.className = `rail-dot done-${info.color}`;
}

// ── Run ────────────────────────────────────────────────────────────────────

async function runScenario(scenarioId) {
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }

  activeScenarioId = scenarioId;
  currentRunId = null;
  changeId = null;
  buCardsMap = {};
  totalCostUsd = 0;
  lastHitlTriggerType = null;

  updateSidebarActive(scenarioId);
  clearRunContent();     // clear previous run, don't re-show welcome
  hideWelcome();         // hide welcome (with animation on first run)
  resetRail();
  resetCostCounter();

  try {
    const resp = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    if (!resp.ok) {
      showError(`Failed to start run: ${resp.statusText}`);
      return;
    }
    const data = await resp.json();
    currentRunId = data.run_id;
    connectSSE(currentRunId);
  } catch (e) {
    showError(`Network error: ${e.message}`);
  }
}

function connectSSE(runId) {
  runStartMs = Date.now();
  startElapsedTimer();
  const source = new EventSource(`/api/runs/${runId}/events`);
  currentEventSource = source;

  source.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      routeEvent(event);
    } catch (err) {
      console.error('SSE parse error', err, e.data);
    }
  };

  source.onerror = () => {
    source.close();
    currentEventSource = null;
    stopElapsedTimer();
  };
}

// ── Event routing ──────────────────────────────────────────────────────────

function routeEvent(ev) {
  announce(ev.type);
  switch (ev.type) {
    case 'run_started':               renderRunStarted(ev.payload); break;
    case 'hook_fired':                renderHookFired(ev.payload); break;
    case 'agent_started':             renderAgentStarted(ev.payload); break;
    case 'gate_decision':             renderGateDecision(ev.payload); break;
    case 'buatlas_instance_started':  renderBUAtlasStarted(ev.payload); break;
    case 'buatlas_instance_completed':renderBUAtlasCompleted(ev.payload); break;
    case 'pushpilot_decision':        renderPushpilotDecision(ev.payload); break;
    case 'hitl_triggered':            renderHITLTriggered(ev.payload); break;
    case 'delivery_rendered':         renderDeliveryRendered(ev.payload); break;
    case 'terminal_state':            renderTerminalState(ev.payload); break;
    case 'error':                     renderPipelineError(ev.payload); break;
    default: console.log('Unhandled event', ev.type, ev.payload);
  }
}

// ── Event handlers ─────────────────────────────────────────────────────────

function renderRunStarted(p) {
  changeId = p.change_id;
  hideWelcome();

  const doc = getRunContent();
  const header = el('div', 'change-header');
  const sourceIcon = sourceTypeSvg(p.source_type);
  header.innerHTML = `
    <div class="change-header__source">${sourceIcon}<span>${escHtml(p.source_type || 'release_note')}</span></div>
    <div class="change-header__title">${escHtml(p.title || 'Change artifact')}</div>
    <div class="change-header__meta">
      <span class="text-mono">${escHtml((p.change_id || '').slice(0, 8))}…</span>
      <span class="text-mono">${escHtml(p.source_ref || '')}</span>
    </div>
  `;
  if (p.raw_text) {
    const toggle = el('button', 'change-header__raw-toggle');
    toggle.textContent = 'Show raw text ↓';
    toggle.setAttribute('aria-expanded', 'false');
    const rawDiv = el('div', 'change-header__raw');
    rawDiv.textContent = p.raw_text;
    const fade = el('div', 'change-header__raw-fade');
    rawDiv.appendChild(fade);
    toggle.addEventListener('click', () => {
      const expanded = rawDiv.classList.toggle('expanded');
      toggle.textContent = expanded ? 'Hide raw text ↑' : 'Show raw text ↓';
      toggle.setAttribute('aria-expanded', String(expanded));
    });
    header.appendChild(toggle);
    header.appendChild(rawDiv);
  }
  doc.appendChild(header);
  setRailActive('pre_ingest');
}

function renderHookFired(p) {
  const stage = p.stage;
  const outcome = p.outcome || 'skip';
  const blocked = outcome === 'fail' || outcome === 'blocked';
  const downgraded = outcome === 'downgraded';
  const passed = !blocked && !downgraded;

  const sectionId = `section-${stage}-hook`;
  let section = document.getElementById(sectionId);
  if (!section) {
    section = createSection(sectionId, 'hook', capitalise(stage.replace(/_/g, ' ')) + ' hook', '');
    getRunContent().appendChild(section);
  }

  const body = section.querySelector('.section-body');
  const cardClass = blocked ? 'hook-card fail' : downgraded ? 'hook-card downgraded' : 'hook-card pass';
  const card = el('div', cardClass);

  const iconSvg = passed
    ? '<svg class="hook-card__icon" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5 6.5-7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    : blocked
      ? '<svg class="hook-card__icon" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4L4 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
      : '<svg class="hook-card__icon" viewBox="0 0 16 16" fill="none"><path d="M8 3v6M8 11v1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';

  const label = passed ? '✓ Passed' : blocked ? '✗ Blocked' : '↓ Downgraded';
  const reason = p.reason ? ` — ${p.reason}` : '';

  card.innerHTML = `
    ${iconSvg}
    <div class="hook-card__content">
      <div class="hook-card__name">${escHtml(p.name || stage)}</div>
      <div class="hook-card__reason">${escHtml(label + reason)}</div>
    </div>
  `;
  body.appendChild(card);

  const railStage = stage === 'pre_ingest' ? 'pre_ingest'
                  : stage === 'pre_deliver' ? 'pre_deliver'
                  : 'post_ss';
  setRailDone(railStage);
}

function renderAgentStarted(p) {
  const agent = p.agent;
  const sectionId = `section-${agent}`;

  if (!document.getElementById(sectionId)) {
    const section = createSection(sectionId, agent, AGENT_LABEL[agent] || agent, agentSubtitle(agent, p));
    const body = section.querySelector('.section-body');
    // PushPilot gets 0 shimmers — per-BU decisions arrive individually with no aggregate loading phase
    const count = agent === 'signalscribe' ? 3 : agent === 'pushpilot' ? 0 : 2;
    for (let i = 0; i < count; i++) {
      const ph = el('div', 'shimmer-placeholder md');
      ph.setAttribute('aria-hidden', 'true');
      body.appendChild(ph);
    }
    getRunContent().appendChild(section);
  }

  const railId = agent === 'signalscribe' ? 'signalscribe'
               : agent === 'buatlas' ? 'buatlas'
               : 'pushpilot';
  setRailActive(railId);
}

function renderGateDecision(p) {
  const agent = p.agent;
  const bu_id = p.bu_id;
  const sectionId = bu_id ? 'section-buatlas' : `section-${agent}`;
  const section = document.getElementById(sectionId);
  if (!section) return;

  // Remove first shimmer on first real decision for this section
  const shimmers = section.querySelectorAll('.shimmer-placeholder');
  if (shimmers.length) shimmers[0].remove();

  if (bu_id) {
    // BU card gate row
    const decisions = getBUCardDecisions(bu_id);
    if (!decisions) return;
    const staggerIdx = decisions.querySelectorAll('.bu-gate-row').length;
    const row = el('div', 'bu-gate-row');
    row.style.animationDelay = `${staggerIdx * 60}ms`;
    const verbClass = VERB_CLASS[p.verb] || 'info';
    const confPct = Math.round((p.confidence || 0) * 100);
    const color = 'var(--color-ba)';
    row.innerHTML = `
      <span class="verb-badge ${verbClass}">${escHtml(p.verb)}</span>
      <span class="bu-gate-label">${GATE_LABEL[p.gate] || `Gate ${p.gate}`}</span>
      <div class="bu-mini-conf">
        <div class="bu-mini-conf-bg">
          <div class="bu-mini-conf-fill" style="background:${color}" data-pct="${confPct}"></div>
        </div>
        <span class="bu-mini-conf-val">${(p.confidence || 0).toFixed(2)}</span>
      </div>
    `;
    decisions.appendChild(row);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const fill = row.querySelector('.bu-mini-conf-fill');
      if (fill) fill.style.width = fill.dataset.pct + '%';
    }));
  } else {
    // Full decision card
    const body = section.querySelector('.section-body');
    if (!body) return;
    const staggerIdx = body.querySelectorAll('.decision-card').length;
    const card = el('div', 'decision-card');
    card.style.animationDelay = `${staggerIdx * 60}ms`;
    const verbClass = VERB_CLASS[p.verb] || 'info';
    const confPct = Math.round((p.confidence || 0) * 100);
    const color = agentColor(agent);
    card.innerHTML = `
      <div class="decision-card__top">
        <span class="verb-badge ${verbClass}">${escHtml(p.verb)}</span>
        <span class="gate-label">${GATE_LABEL[p.gate] || `Gate ${p.gate}`}</span>
        <div class="confidence-wrap">
          <div class="confidence-bar-bg">
            <div class="confidence-bar-fill" style="background:${color}" data-pct="${confPct}"></div>
          </div>
          <span class="confidence-val">${(p.confidence || 0).toFixed(2)}</span>
        </div>
      </div>
      <div class="decision-card__reason">${escHtml((p.reason || '').slice(0, 400))}</div>
    `;
    body.appendChild(card);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const fill = card.querySelector('.confidence-bar-fill');
      if (fill) fill.style.width = fill.dataset.pct + '%';
    }));

    const railId = agent === 'signalscribe' ? 'signalscribe'
                 : agent === 'buatlas' ? 'buatlas'
                 : 'pushpilot';
    setRailDone(railId);
  }
}

function renderBUAtlasStarted(p) {
  const bu_id = p.bu_id;
  let section = document.getElementById('section-buatlas');
  if (!section) {
    section = createSection('section-buatlas', 'buatlas', 'BUAtlas', 'Parallel per-BU personalization');
    // Remove default shimmers — BU cards provide their own
    section.querySelector('.section-body').innerHTML = '';
    getRunContent().appendChild(section);
  }

  let grid = section.querySelector('.bu-grid');
  if (!grid) {
    grid = el('div', 'bu-grid');
    section.querySelector('.section-body').appendChild(grid);
  }

  // All cards mount simultaneously with the same base animation, no stagger
  const card = el('div', 'bu-card');
  card.id = `bu-card-${bu_id}`;
  card.innerHTML = `
    <div class="bu-card__header">
      <div class="bu-card__name">${escHtml(p.bu_name || bu_id)}</div>
      <div class="bu-card__id">${escHtml(bu_id)}</div>
    </div>
    <div class="bu-card__decisions">
      <div class="shimmer-placeholder sm" aria-hidden="true"></div>
      <div class="shimmer-placeholder sm" aria-hidden="true"></div>
    </div>
  `;
  grid.appendChild(card);
  buCardsMap[bu_id] = card;
}

function renderBUAtlasCompleted(p) {
  const bu_id = p.bu_id;
  const card = buCardsMap[bu_id];
  if (!card) return;

  card.querySelectorAll('.shimmer-placeholder').forEach(s => s.remove());

  const verdict = p.verdict || '';
  const relevance = p.relevance || '';
  const isDimmed = verdict === 'NOT_WORTH' || relevance === 'NOT_AFFECTED' || verdict === 'NOT_AFFECTED';
  if (isDimmed) card.classList.add('dimmed');

  // Show message variants if WORTH_SENDING
  if (verdict === 'WORTH_SENDING' && p.message_variants) {
    const variants = p.message_variants;
    const variantEl = el('div', 'bu-variants');
    const channels = Object.keys(variants).filter(k => variants[k]);
    if (channels.length > 0) {
      const tabs = el('div', 'bu-variant-tabs');
      const panels = {};
      channels.forEach((ch, idx) => {
        const tab = el('button', `bu-variant-tab${idx === 0 ? ' active' : ''}`);
        tab.textContent = capitalise(ch);
        const panel = el('div', 'bu-variant-body');
        panel.textContent = variants[ch] || '';
        panel.hidden = idx !== 0;
        panels[ch] = panel;
        tab.addEventListener('click', () => {
          tabs.querySelectorAll('.bu-variant-tab').forEach(t => t.classList.remove('active'));
          Object.values(panels).forEach(pp => { pp.hidden = true; });
          tab.classList.add('active');
          panel.hidden = false;
        });
        tabs.appendChild(tab);
        variantEl.appendChild(panel);
      });
      variantEl.prepend(tabs);
      card.appendChild(variantEl);
    }
  }

  setRailDone('buatlas');
}

function renderPushpilotDecision(p) {
  const bu_id = p.bu_id;
  const diverged = p.diverged;
  const sectionId = 'section-pushpilot';

  let section = document.getElementById(sectionId);
  if (!section) {
    // agent_started should have created this; create defensively if missing
    section = createSection(sectionId, 'pushpilot', 'PushPilot', 'Gate 6 · delivery timing');
    getRunContent().appendChild(section);
  }

  const body = section.querySelector('.section-body');

  // BU label — helps distinguish when multiple BUs each get a PushPilot decision
  const buLabel = el('div', 'pp-bu-label');
  buLabel.textContent = bu_id;
  body.appendChild(buLabel);

  if (diverged && p.preference && p.enforced) {
    // The architectural moment — animated two-card layout
    const wrap = el('div', 'pp-diverged-wrap');

    // Top card: agent preference
    const topCard = el('div', 'pp-card top-card');
    topCard.innerHTML = `
      <div class="pp-card-label preference">Agent preference</div>
      <div class="decision-card__top" style="margin-bottom:10px">
        <span class="verb-badge ${VERB_CLASS[p.preference.verb] || 'info'}">${escHtml(p.preference.verb)}</span>
        <span class="gate-label">Gate 6 · delivery timing</span>
        ${p.preference.confidence != null ? `
        <div class="confidence-wrap">
          <div class="confidence-bar-bg">
            <div class="confidence-bar-fill" style="background:var(--color-pp)" data-pct="${Math.round((p.preference.confidence || 0) * 100)}"></div>
          </div>
          <span class="confidence-val">${(p.preference.confidence || 0).toFixed(2)}</span>
        </div>` : ''}
      </div>
      <div class="decision-card__reason">${escHtml((p.preference.reason || '').slice(0, 300))}</div>
    `;
    wrap.appendChild(topCard);

    // SVG connector with stroke animation
    const connectorWrap = el('div', 'pp-connector');
    connectorWrap.innerHTML = `
      <svg width="24" height="40" viewBox="0 0 24 40" fill="none" aria-hidden="true">
        <path class="pp-connector-line" d="M12 0 L12 32 M6 26 L12 32 L18 26"
          stroke="#8D877B" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
    wrap.appendChild(connectorWrap);

    // Bottom card: code enforcement
    const botCard = el('div', 'pp-card bot-card');
    botCard.innerHTML = `
      <div class="pp-card-label enforcement">Code enforcement</div>
      <div class="decision-card__top" style="margin-bottom:10px">
        <span class="verb-badge ${VERB_CLASS[p.enforced.verb] || 'info'}">${escHtml(p.enforced.verb)}</span>
        <span class="gate-label">pre_deliver policy</span>
      </div>
      <div class="decision-card__reason">${escHtml((p.enforced.reason || '').slice(0, 300))}</div>
    `;
    wrap.appendChild(botCard);

    // Caption
    const caption = el('p', 'pp-caption');
    caption.textContent = 'This separation lets us calibrate policy by comparing agent judgment against enforced outcomes.';
    wrap.appendChild(caption);

    body.appendChild(wrap);

    // Trigger arrow draw after top card has had time to enter
    requestAnimationFrame(() => requestAnimationFrame(() => {
      setTimeout(() => {
        const line = connectorWrap.querySelector('.pp-connector-line');
        if (line) line.classList.add('drawn');
      }, 620);
    }));
  } else {
    // Non-diverged: standard card (no confidence bar — PushPilot's timing decision has no confidence score)
    const pref = p.preference || p;
    const card = el('div', 'pp-decision');
    const verbClass = VERB_CLASS[pref.verb] || 'info';
    card.innerHTML = `
      <div class="decision-card__top">
        <span class="verb-badge ${verbClass}">${escHtml(pref.verb)}</span>
        <span class="gate-label">Gate 6 · delivery timing</span>
      </div>
      <div class="decision-card__reason">${escHtml((pref.reason || '').slice(0, 400))}</div>
    `;
    body.appendChild(card);
  }

  setRailDone('pushpilot');
}

function renderHITLTriggered(p) {
  lastHitlTriggerType = p.trigger_type || null;
  const doc = getRunContent();
  const card = el('div', 'hitl-trigger-card');
  card.innerHTML = `
    <div class="hitl-trigger-card__title">Routed to human review</div>
    <div class="hitl-trigger-card__reason">
      <strong>${escHtml(p.trigger_type || 'trigger')}</strong>: ${escHtml(p.reason || '')}
    </div>
  `;
  doc.appendChild(card);
}

function renderDeliveryRendered(p) {
  const card = buCardsMap[p.bu_id];
  if (card) {
    const note = el('div', 'bu-delivery-note');
    note.textContent = `→ ${p.channel || '?'} · ${p.variant || '?'}`;
    card.appendChild(note);
  }
}

function renderTerminalState(p) {
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  // Issue 1: clean up any unfilled shimmer placeholders (gates that never fired)
  document.querySelectorAll('#run-content .shimmer-placeholder').forEach(s => s.remove());

  const elapsed = p.elapsed_s || ((Date.now() - (runStartMs || Date.now())) / 1000).toFixed(1);
  updateCostCounter(p.total_cost_usd || 0, elapsed);

  const doc = getRunContent();
  const state = p.state || 'UNKNOWN';
  const meta = STATE_META[state] || { css: 'terminal-archived', accent: 'neutral', title: state };

  // Issue 2: section divider shows trigger type for HITL; no title for other terminal states
  // (the body heading — terminal-summary__title or hitl-panel — carries the visual weight)
  const sectionTitle = state === 'AWAITING_HITL'
    ? (lastHitlTriggerType || 'awaiting_hitl')
    : '';

  const section = createSection('section-terminal', meta.accent, sectionTitle, '');
  section.classList.add(meta.css);
  const body = section.querySelector('.section-body');

  // Summary heading — only for non-HITL states (HITL panel has its own "Operator review panel" heading)
  if (state !== 'AWAITING_HITL') {
    const summary = el('div', 'terminal-summary');
    summary.innerHTML = `
      <div class="terminal-summary__title">${escHtml(meta.title)}</div>
    `;
    body.appendChild(summary);
  }

  // State-specific body
  if (state === 'DELIVERED') {
    const buList = (p.bu_outcomes || []).map(o => `${escHtml(o.bu_id)} via ${escHtml(o.channel || '?')}`).join(', ');
    if (buList) {
      const sentTo = el('p', '');
      sentTo.style.cssText = 'font-size:14px;color:var(--text-secondary);margin-bottom:16px';
      sentTo.innerHTML = `Sent to: <strong>${buList}</strong>`;
      body.appendChild(sentTo);
    }
    body.appendChild(buildMessagePreview(p.bu_outcomes || []));
  } else if (state === 'AWAITING_HITL') {
    if (p.hitl_reason) {
      const sub = el('p', '');
      sub.style.cssText = 'font-size:13px;font-weight:500;letter-spacing:0.02em;color:var(--color-info);margin-bottom:12px';
      sub.textContent = p.hitl_reason;
      body.appendChild(sub);
    }
    body.appendChild(buildHITLPanel());
  } else if (state === 'ARCHIVED') {
    const reason = (p.reason || (p.bu_outcomes && p.bu_outcomes[0] && p.bu_outcomes[0].reason) || 'No user-visible impact. Archived cleanly.');
    const quote = el('blockquote', 'archive-quote');
    quote.textContent = reason;
    body.appendChild(quote);
  } else if (state === 'HELD') {
    const reason = (p.reason || (p.bu_outcomes && p.bu_outcomes[0] && p.bu_outcomes[0].reason) || 'Change is held pending rollout conditions.');
    const quote = el('blockquote', 'archive-quote');
    quote.style.borderLeftColor = 'var(--color-warn)';
    quote.textContent = reason;
    body.appendChild(quote);
  } else if (state === 'DIGESTED') {
    const note = el('p', '');
    note.style.cssText = 'font-size:14px;color:var(--text-secondary)';
    note.textContent = 'Queued for the next digest bundle. Recipients will receive a digest summary at the scheduled time.';
    body.appendChild(note);
  } else if (state === 'FAILED' || state === 'REJECTED') {
    const errs = p.errors || [];
    const errMsg = el('p', '');
    errMsg.style.cssText = 'font-size:14px;color:var(--text-secondary);margin-bottom:8px';
    errMsg.textContent = errs.length ? errs.join(' | ') : 'An unexpected error occurred in the pipeline.';
    body.appendChild(errMsg);
    const btn = el('button', 'retry-btn');
    btn.textContent = 'Retry this scenario';
    btn.addEventListener('click', () => runScenario(activeScenarioId));
    body.appendChild(btn);
  }

  // Metadata line
  const costUsd = p.total_cost_usd != null ? `$${Number(p.total_cost_usd).toFixed(3)} cost` : null;
  const elapsedStr = elapsed != null ? `${elapsed}s elapsed` : null;
  if (costUsd || elapsedStr) {
    const metaEl = el('div', 'terminal-meta');
    metaEl.textContent = [costUsd, elapsedStr].filter(Boolean).join(' · ');
    body.appendChild(metaEl);
  }

  doc.appendChild(section);

  // Footer
  const footer = el('div', 'run-footer');
  const auditBtn = el('button', 'footer-btn');
  auditBtn.textContent = 'View audit trail';
  auditBtn.addEventListener('click', openDrawer);
  const rerunBtn = el('button', 'footer-btn primary');
  rerunBtn.textContent = 'Run again';
  rerunBtn.addEventListener('click', () => runScenario(activeScenarioId));
  footer.appendChild(auditBtn);
  footer.appendChild(rerunBtn);
  doc.appendChild(footer);

  setScenarioBadge(activeScenarioId, state);
  setRailDone('terminal');
}

function renderPipelineError(p) {
  const doc = getRunContent();
  const wrap = el('div', '');
  wrap.style.marginTop = '24px';
  wrap.innerHTML = `
    <p style="font-size:14px;color:var(--color-danger);margin-bottom:8px">
      <strong>Pipeline error</strong>: ${escHtml(p.message || 'An error occurred.')}
    </p>
  `;
  doc.appendChild(wrap);
}

// ── Message previews ───────────────────────────────────────────────────────

function buildMessagePreview(buOutcomes) {
  const bu = buOutcomes[0] || {};
  const wrap = el('div', 'msg-preview');
  const tabsEl = el('div', 'msg-preview__tabs');
  wrap.appendChild(tabsEl);

  const channels = ['teams', 'email', 'push'];
  const panels = {};
  const tabEls = {};

  channels.forEach((ch, idx) => {
    const tab = el('button', `msg-tab${idx === 0 ? ' active' : ''}`);
    tab.textContent = ch === 'push' ? 'Push' : ch === 'email' ? 'Email' : 'Teams';
    const panel = el('div', 'msg-panel');
    panel.hidden = idx !== 0;
    panels[ch] = panel;
    tabEls[ch] = tab;

    tab.addEventListener('click', () => {
      Object.values(tabEls).forEach(t => t.classList.remove('active'));
      Object.values(panels).forEach(p => { p.hidden = true; });
      tab.classList.add('active');
      panel.hidden = false;
    });
    tabsEl.appendChild(tab);
    wrap.appendChild(panel);

    if (ch === 'teams') panel.appendChild(buildTeamsCard(bu));
    else if (ch === 'email') panel.appendChild(buildEmailMock(bu));
    else panel.appendChild(buildPushMock(bu));
  });

  return wrap;
}

function buildTeamsCard(bu) {
  const card = el('div', 'teams-card-mock');
  card.innerHTML = `
    <div class="teams-card-mock__header">
      <div class="teams-avatar">PC</div>
      <div class="teams-header-info">
        <div class="teams-app-name">PulseCraft Change Alert</div>
        <div class="teams-timestamp">Today, ${new Date().toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</div>
      </div>
    </div>
    <div class="teams-card-mock__title">Change notification — action recommended</div>
    <div class="teams-card-mock__body">
      A marketplace change affecting <strong>${escHtml(bu.bu_id || 'your BU')}</strong> has been reviewed and approved. Please review the change details and confirm your team is prepared for any required actions.
    </div>
    <div class="teams-actions">
      <div class="teams-btn primary">View details</div>
      <div class="teams-btn">Acknowledge</div>
    </div>
  `;
  return card;
}

function buildEmailMock(bu) {
  const email = el('div', 'email-mock');
  email.innerHTML = `
    <div class="email-header">
      <div class="email-row"><span>From:</span><span>PulseCraft &lt;noreply@pulsecraft.internal&gt;</span></div>
      <div class="email-row"><span>To:</span><span>${escHtml(bu.bu_id || 'bu_head')}@internal</span></div>
    </div>
    <div class="email-subject">Change notification — ${escHtml(bu.bu_id || 'your BU')} — action recommended</div>
    <div class="email-body">
      A marketplace change relevant to ${escHtml(bu.bu_id || 'your business unit')} has been processed and approved by PulseCraft.
      <br><br>
      <strong>Recommended action:</strong> Review the change summary and confirm your team is aware of the expected impact before the rollout date.
      <br><br>
      This message was generated by the PulseCraft change intelligence service and reviewed by an operator before delivery.
    </div>
  `;
  return email;
}

function buildPushMock(bu) {
  const push = el('div', 'push-mock');
  push.innerHTML = `
    <div class="push-icon">🔔</div>
    <div>
      <div class="push-app">PulseCraft · now</div>
      <div class="push-title">Change affects ${escHtml(bu.bu_id || 'your BU')}</div>
      <div class="push-body">Review required — tap for details.</div>
    </div>
  `;
  return push;
}

function buildHITLPanel() {
  const panel = el('div', 'hitl-panel');
  panel.innerHTML = `
    <div class="hitl-panel__title">Operator review panel</div>
    <p class="hitl-panel__desc">
      The proposed message is pending review. An operator can approve, reject, or edit before delivery proceeds.
    </p>
    <div class="hitl-panel__actions">
      <div class="hitl-btn approve">Approve</div>
      <div class="hitl-btn reject">Reject</div>
      <div class="hitl-btn edit">Edit</div>
      <div class="hitl-btn answer">Answer question</div>
    </div>
    <div class="hitl-panel__note">
      In production, operators receive a notification and act via <code>pulsecraft approve</code> CLI or a dashboard.
    </div>
  `;
  return panel;
}

// ── DOM helpers ────────────────────────────────────────────────────────────

function el(tag, className) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}

function escHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }

function getRunContent() {
  const rc = document.getElementById('run-content');
  rc.hidden = false;
  return rc;
}

function clearRunContent() {
  const rc = document.getElementById('run-content');
  rc.innerHTML = '';
  rc.hidden = true;
}

// Welcome hide — animated on first call, instant thereafter
function hideWelcome() {
  const welcome = document.getElementById('welcome');
  if (welcome.hidden) return;
  if (!hasRunBefore) {
    hasRunBefore = true;
    welcome.classList.add('exiting');
    setTimeout(() => {
      welcome.hidden = true;
      welcome.classList.remove('exiting');
    }, 300);
  } else {
    welcome.hidden = true;
  }
}

function resetRailVisual() {
  Object.values(railDots).forEach(({ el }) => { el.className = 'rail-dot'; });
}

function createSection(id, agentOrAccent, title, subtitle) {
  const section = el('div', 'pipeline-section');
  section.id = id;
  section.innerHTML = `
    <div class="section-header">
      <div class="section-accent ${agentOrAccent}"></div>
      <div>
        ${title ? `<div class="section-title">${escHtml(title)}</div>` : ''}
        ${subtitle ? `<div class="section-sub">${escHtml(subtitle)}</div>` : ''}
      </div>
    </div>
    <div class="section-body"></div>
  `;
  return section;
}

function getBUCardDecisions(bu_id) {
  const card = buCardsMap[bu_id];
  if (!card) return null;
  let decisions = card.querySelector('.bu-card__decisions');
  if (!decisions) {
    decisions = el('div', 'bu-card__decisions');
    card.appendChild(decisions);
  }
  return decisions;
}

function agentColor(agent) {
  return {
    signalscribe: 'var(--color-ss)',
    buatlas:      'var(--color-ba)',
    pushpilot:    'var(--color-pp)',
  }[agent] || 'var(--text-tertiary)';
}

function agentSubtitle(agent, p) {
  const gates = (p.gate_batch || []).join(', ');
  return gates ? `Gates ${gates}` : '';
}

function sourceTypeSvg(type) {
  const icons = {
    release_note: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M3.5 5h7M3.5 7.5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    incident:     '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L13 12H1L7 1Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M7 5v3M7 9.5v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    feature_flag: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2v10M2 2h8l-2 3 2 3H2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    default:      '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.2"/><path d="M7 5v4M7 3.5v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
  };
  return icons[type] || icons.default;
}

// ── Cost / elapsed counter ──────────────────────────────────────────────────

function resetCostCounter() {
  document.getElementById('cost-counter').textContent = '—';
}

function updateCostCounter(costUsd, elapsedS) {
  const cost = costUsd != null ? `$${Number(costUsd).toFixed(3)}` : '$0.000';
  const elapsed = elapsedS != null ? `${Number(elapsedS).toFixed(1)}s` : '—';
  document.getElementById('cost-counter').textContent = `${cost} · ${elapsed}`;
}

function startElapsedTimer() {
  elapsedTimer = setInterval(() => {
    if (!runStartMs) return;
    const s = ((Date.now() - runStartMs) / 1000).toFixed(1);
    const counter = document.getElementById('cost-counter');
    const cur = counter.textContent;
    if (cur === '—') {
      counter.textContent = `$0.000 · ${s}s`;
    } else {
      counter.textContent = cur.replace(/[\d.]+s$/, `${s}s`);
    }
  }, 200);
}

function stopElapsedTimer() {
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
}

// ── Audit drawer ────────────────────────────────────────────────────────────

function openDrawer() {
  const drawer = document.getElementById('audit-drawer');
  const overlay = document.getElementById('drawer-overlay');
  drawer.removeAttribute('hidden');
  overlay.removeAttribute('hidden');

  const body = document.getElementById('drawer-body');
  if (changeId) {
    body.textContent =
      `Audit trail for change ${changeId.slice(0, 8)}…\n\n` +
      `Run locally:\n  pulsecraft explain ${changeId.slice(0, 8)}\n\n` +
      `Full change ID:\n  ${changeId}\n\n` +
      `The /explain command renders every agent decision, policy override,\n` +
      `HITL event, and delivery outcome with timing and cost.\n\n` +
      `Use --all to show all runs for this change ID,\n` +
      `or --list-runs to enumerate run boundaries.`;
  } else {
    body.innerHTML = '<p class="drawer__hint">No run completed yet. Start a scenario to see its audit trail.</p>';
  }
}

function closeDrawer() {
  document.getElementById('audit-drawer').setAttribute('hidden', '');
  document.getElementById('drawer-overlay').setAttribute('hidden', '');
}

// ── Error display ───────────────────────────────────────────────────────────

function showError(msg) {
  const doc = getRunContent();
  doc.innerHTML = `
    <div style="margin-top:24px;padding:20px;background:var(--color-danger-surface);border:1px solid var(--color-danger);border-radius:10px">
      <div style="font-family:'Fraunces',serif;font-size:18px;color:var(--color-danger);margin-bottom:8px">Error</div>
      <div style="font-size:14px;color:var(--text-secondary)">${escHtml(msg)}</div>
    </div>
  `;
}

// ── Keyboard shortcuts ──────────────────────────────────────────────────────

function handleKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 5 && scenarios[n - 1]) {
    runScenario(scenarios[n - 1].id);
    return;
  }
  if (e.key === 'Escape') closeDrawer();
}

// ── Accessibility ───────────────────────────────────────────────────────────

function announce(msg) {
  const el = document.getElementById('sr-announcer');
  if (el) el.textContent = msg;
}

// ── Bootstrap ──────────────────────────────────────────────────────────────

init();
