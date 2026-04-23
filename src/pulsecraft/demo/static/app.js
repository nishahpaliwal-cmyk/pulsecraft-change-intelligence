/**
 * PulseCraft demo app — vanilla JS, ES modules, no framework.
 * Handles scenario rendering, SSE streaming, and all UI state.
 */

// ── Constants ──────────────────────────────────────────────────────────────

const VERB_CLASS = {
  COMMUNICATE: 'positive', RIPE: 'positive', READY: 'positive',
  AFFECTED: 'positive', WORTH_SENDING: 'positive', SEND_NOW: 'positive',
  ARCHIVE: 'negative', NOT_AFFECTED: 'negative',
  HOLD_UNTIL: 'warning', HOLD_INDEFINITE: 'warning', DIGEST: 'info',
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

const AGENT_COLOR = {
  signalscribe: 'signalscribe',
  buatlas: 'buatlas',
  pushpilot: 'pushpilot',
};

const AGENT_LABEL = {
  signalscribe: 'SignalScribe',
  buatlas: 'BUAtlas',
  pushpilot: 'PushPilot',
};

const RAIL_STAGES = [
  { id: 'pre_ingest',    label: 'Pre-ingest hook',    color: 'hook' },
  { id: 'signalscribe',  label: 'SignalScribe',        color: 'ss' },
  { id: 'post_ss',       label: 'Post-agent hook (SS)', color: 'hook' },
  { id: 'buatlas',       label: 'BUAtlas',             color: 'ba' },
  { id: 'pushpilot',     label: 'PushPilot',           color: 'pp' },
  { id: 'pre_deliver',   label: 'Pre-deliver hook',    color: 'hook' },
  { id: 'terminal',      label: 'Terminal state',      color: 'ss' },
];

// ── State ──────────────────────────────────────────────────────────────────

let scenarios = [];
let activeScenarioId = null;
let currentRunId = null;
let currentEventSource = null;
let runStartMs = null;
let totalCostUsd = 0;
let elapsedTimer = null;

// Per-run rendering state
let buCardsMap = {};          // bu_id -> DOM element
let railDots = {};             // stage id -> dot element
let changeId = null;           // for audit trail

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
    card.setAttribute('aria-label', `Scenario ${s.id}: ${s.title}`);
    card.dataset.scenarioId = s.id;
    card.innerHTML = `
      <div class="scenario-num">${String(idx + 1).padStart(2, '0')}</div>
      <div class="scenario-title">${escHtml(s.title)}</div>
      <div class="scenario-desc text-secondary">${escHtml(s.description)}</div>
      <span class="scenario-run-hint" aria-hidden="true">Run →</span>
      <div class="scenario-progress-bar" id="progress-bar-${s.id}"></div>
    `;
    card.addEventListener('click', () => runScenario(s.id));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); runScenario(s.id); } });
    list.appendChild(card);
  });
}

function updateSidebarActive(scenarioId) {
  document.querySelectorAll('.scenario-card').forEach(c => {
    c.classList.toggle('active', c.dataset.scenarioId === scenarioId);
  });
}

function setScenarioBadge(scenarioId, state) {
  const card = document.querySelector(`[data-scenario-id="${scenarioId}"]`);
  if (!card) return;
  const existing = card.querySelector('.scenario-badge');
  if (existing) existing.remove();
  const badge = document.createElement('span');
  const stateClass = {
    'DELIVERED': 'delivered', 'ARCHIVED': 'archived',
    'AWAITING_HITL': 'hitl', 'HELD': 'held', 'DIGESTED': 'held',
    'FAILED': 'failed', 'REJECTED': 'failed',
  }[state] || 'archived';
  const stateLabel = {
    'DELIVERED': 'delivered', 'ARCHIVED': 'archived',
    'AWAITING_HITL': 'awaiting review', 'HELD': 'held',
    'DIGESTED': 'digested', 'FAILED': 'failed', 'REJECTED': 'rejected',
  }[state] || state.toLowerCase();
  badge.className = `scenario-badge ${stateClass}`;
  badge.textContent = stateLabel;
  card.appendChild(badge);
}

// ── Rail ───────────────────────────────────────────────────────────────────

function renderRail() {
  const track = document.getElementById('rail-track');
  track.innerHTML = '';
  RAIL_STAGES.forEach(stage => {
    const wrap = document.createElement('div');
    wrap.className = 'rail-dot-wrap';
    wrap.setAttribute('aria-label', stage.label);
    wrap.title = stage.label;
    const dot = document.createElement('div');
    dot.className = 'rail-dot';
    dot.id = `rail-${stage.id}`;
    const tooltip = document.createElement('div');
    tooltip.className = 'rail-tooltip';
    tooltip.textContent = stage.label;
    wrap.appendChild(dot);
    wrap.appendChild(tooltip);
    track.appendChild(wrap);
    railDots[stage.id] = dot;
    wrap.addEventListener('click', () => {
      const section = document.getElementById(`section-${stage.id}`);
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

function setRailActive(stageId) {
  Object.values(railDots).forEach(d => d.classList.remove('active'));
  const dot = railDots[stageId];
  if (dot) dot.classList.add('active');
}

function setRailCompleted(stageId, color) {
  const dot = railDots[stageId];
  if (!dot) return;
  dot.classList.remove('active');
  dot.classList.add(`completed-${color}`);
}

// ── Run ────────────────────────────────────────────────────────────────────

async function runScenario(scenarioId) {
  // Abort any in-progress run
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }

  activeScenarioId = scenarioId;
  currentRunId = null;
  changeId = null;
  buCardsMap = {};
  totalCostUsd = 0;

  updateSidebarActive(scenarioId);
  resetDocument();
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
    case 'run_started':            renderRunStarted(ev.payload); break;
    case 'hook_fired':             renderHookFired(ev.payload); break;
    case 'agent_started':          renderAgentStarted(ev.payload); break;
    case 'gate_decision':          renderGateDecision(ev.payload); break;
    case 'buatlas_instance_started':   renderBUAtlasStarted(ev.payload); break;
    case 'buatlas_instance_completed': renderBUAtlasCompleted(ev.payload); break;
    case 'pushpilot_decision':     renderPushpilotDecision(ev.payload); break;
    case 'hitl_triggered':         renderHITLTriggered(ev.payload); break;
    case 'delivery_rendered':      renderDeliveryRendered(ev.payload); break;
    case 'terminal_state':         renderTerminalState(ev.payload); break;
    case 'error':                  renderPipelineError(ev.payload); break;
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
      <span>${escHtml((p.change_id || '').slice(0, 8)}…</span>
      <span>${escHtml(p.source_ref || '')}</span>
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
}

function renderHookFired(p) {
  const stage = p.stage;
  const outcome = p.outcome || 'skip';
  const passed = outcome !== 'fail' && outcome !== 'blocked';
  const sectionId = `section-${stage}-hook`;

  let section = document.getElementById(sectionId);
  if (!section) {
    section = createSection(sectionId, 'hook', capitalise(stage) + ' hook', '');
    getRunContent().appendChild(section);
  }

  const body = section.querySelector('.section-body');
  const card = el('div', `hook-card${passed ? ' pass' : ''}`);
  card.innerHTML = `
    <div class="hook-card__name">${escHtml(p.name || stage)}</div>
    <div class="hook-card__reason">${passed ? '✓ passed' : '✗ ' + escHtml(p.reason || 'blocked')}</div>
  `;
  body.appendChild(card);

  const railStage = stage === 'pre_ingest' ? 'pre_ingest' :
                    stage === 'pre_deliver' ? 'pre_deliver' : 'post_ss';
  setRailCompleted(railStage, 'hook');
}

function renderAgentStarted(p) {
  const agent = p.agent;
  const sectionId = `section-${agent}`;

  let section = document.getElementById(sectionId);
  if (!section) {
    section = createSection(sectionId, agent, AGENT_LABEL[agent] || agent, agentSubtitle(agent, p));
    const body = section.querySelector('.section-body');
    // Add shimmer placeholders
    [0, 1, 2].slice(0, (p.gate_batch || []).length || 2).forEach(() => {
      const ph = el('div', 'shimmer-placeholder');
      ph.setAttribute('aria-hidden', 'true');
      body.appendChild(ph);
    });
    getRunContent().appendChild(section);
  }

  setRailActive(agent === 'signalscribe' ? 'signalscribe' : agent === 'buatlas' ? 'buatlas' : 'pushpilot');
}

function renderGateDecision(p) {
  const agent = p.agent;
  const bu_id = p.bu_id;
  const sectionId = bu_id ? `section-buatlas` : `section-${agent}`;

  let section = document.getElementById(sectionId);
  if (!section) return;

  // Remove shimmer placeholders on first real decision
  const shimmers = section.querySelectorAll('.shimmer-placeholder');
  if (shimmers.length) shimmers[0].remove();

  const body = bu_id ? getBUCardDecisions(bu_id) : section.querySelector('.section-body');
  if (!body) return;

  const staggerIdx = body.querySelectorAll('.decision-card').length;
  const card = el('div', 'decision-card');
  card.style.animationDelay = `${staggerIdx * 80}ms`;

  const verbClass = VERB_CLASS[p.verb] || 'info';
  const confPct = Math.round((p.confidence || 0) * 100);
  const confColor = agentColor(agent);

  card.innerHTML = `
    <div class="decision-card__top">
      <span class="verb-badge ${verbClass}">${escHtml(p.verb)}</span>
      <span class="gate-label text-tertiary">${GATE_LABEL[p.gate] || `Gate ${p.gate}`}</span>
      <div class="confidence-wrap">
        <div class="confidence-bar-bg"><div class="confidence-bar-fill" style="background:${confColor}" data-pct="${confPct}"></div></div>
        <span class="confidence-val text-tertiary">${(p.confidence || 0).toFixed(2)}</span>
      </div>
    </div>
    <div class="decision-card__reason text-secondary">${escHtml((p.reason || '').slice(0, 300))}</div>
  `;
  body.appendChild(card);

  // Animate confidence bar after paint
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const fill = card.querySelector('.confidence-bar-fill');
    if (fill) fill.style.width = fill.dataset.pct + '%';
  }));

  setRailCompleted(agent === 'signalscribe' ? 'signalscribe' : agent === 'buatlas' ? 'buatlas' : 'pushpilot',
                   agent === 'signalscribe' ? 'ss' : agent === 'buatlas' ? 'ba' : 'pp');
}

function renderBUAtlasStarted(p) {
  const bu_id = p.bu_id;
  let section = document.getElementById('section-buatlas');
  if (!section) {
    section = createSection('section-buatlas', 'buatlas', 'BUAtlas', 'Per-BU personalization — parallel fan-out');
    getRunContent().appendChild(section);
  }

  let grid = section.querySelector('.bu-grid');
  if (!grid) {
    grid = el('div', 'bu-grid');
    section.querySelector('.section-body').appendChild(grid);
  }

  const card = el('div', 'bu-card');
  card.id = `bu-card-${bu_id}`;
  card.innerHTML = `
    <div class="bu-card__header">
      <div class="bu-card__name">${escHtml(p.bu_name || bu_id)}</div>
      <div class="bu-card__id text-mono text-tertiary">${escHtml(bu_id)}</div>
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

  // Remove shimmers
  card.querySelectorAll('.shimmer-placeholder').forEach(s => s.remove());

  const verdict = p.verdict || '';
  const isDimmed = verdict === 'NOT_WORTH' || p.relevance === 'NOT_AFFECTED' || verdict === 'NOT_AFFECTED';
  if (isDimmed) card.classList.add('dimmed');

  setRailCompleted('buatlas', 'ba');
}

function renderPushpilotDecision(p) {
  const bu_id = p.bu_id;
  const diverged = p.diverged;
  const sectionId = `section-pushpilot-${bu_id}`;

  let section = document.getElementById(sectionId);
  if (!section) {
    section = createSection(sectionId, 'pushpilot', `PushPilot · ${bu_id}`, 'Gate 6 · delivery timing');
    getRunContent().appendChild(section);
  }

  const body = section.querySelector('.section-body');
  const block = el('div', `pp-decision${diverged ? ' pp-diverged' : ''}`);

  if (diverged) {
    block.innerHTML = `
      <div class="pp-preference-label">Agent preference</div>
      <div class="decision-card__top" style="margin-bottom:6px">
        <span class="verb-badge ${VERB_CLASS[p.preference.verb] || 'info'}">${escHtml(p.preference.verb)}</span>
      </div>
      <div class="decision-card__reason text-secondary" style="font-size:13px">${escHtml((p.preference.reason||'').slice(0,200))}</div>
      <div class="pp-arrow" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 4v16m-6-6l6 6 6-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div class="pp-enforced-label">Code enforcement</div>
      <div class="decision-card__top" style="margin-bottom:6px">
        <span class="verb-badge ${VERB_CLASS[p.enforced.verb] || 'info'}">${escHtml(p.enforced.verb)}</span>
      </div>
      <div class="decision-card__reason text-secondary" style="font-size:13px">${escHtml((p.enforced.reason||'').slice(0,200))}</div>
      <div class="pp-caption">This separation lets us calibrate policy by comparing agent judgment against enforced outcomes.</div>
    `;
  } else {
    const pref = p.preference;
    block.innerHTML = `
      <div class="decision-card__top">
        <span class="verb-badge ${VERB_CLASS[pref.verb] || 'info'}">${escHtml(pref.verb)}</span>
        <span class="gate-label text-tertiary">Gate 6 · delivery timing</span>
      </div>
      <div class="decision-card__reason text-secondary">${escHtml((pref.reason||'').slice(0,300))}</div>
    `;
  }

  body.appendChild(block);
  setRailCompleted('pushpilot', 'pp');
}

function renderHITLTriggered(p) {
  const doc = getRunContent();
  const card = el('div', 'hitl-card');
  card.innerHTML = `
    <div class="hitl-card__title">Routed to human review</div>
    <div class="hitl-card__reason">
      <strong>${escHtml(p.trigger_type || 'trigger')}</strong>: ${escHtml(p.reason || '')}
    </div>
  `;
  doc.appendChild(card);
}

function renderDeliveryRendered(p) {
  // Update BU card to show delivery channel
  const card = buCardsMap[p.bu_id];
  if (card) {
    const note = el('div', 'text-micro text-secondary');
    note.style.marginTop = '8px';
    note.textContent = `→ ${p.channel} · ${p.variant}`;
    card.appendChild(note);
  }
}

function renderTerminalState(p) {
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  const elapsed = p.elapsed_s || ((Date.now() - (runStartMs || Date.now())) / 1000).toFixed(1);
  updateCostCounter(p.total_cost_usd || 0, elapsed);

  const doc = getRunContent();
  const state = p.state || 'UNKNOWN';
  const stateClass = {
    'DELIVERED': 'delivered', 'ARCHIVED': 'archived',
    'AWAITING_HITL': 'hitl', 'HELD': 'held', 'DIGESTED': 'held',
    'FAILED': 'failed', 'REJECTED': 'failed',
  }[state] || 'archived';

  // Add a terminal section
  const section = createSection('section-terminal', 'delivery', 'Result', '');
  const body = section.querySelector('.section-body');
  const block = el('div', `terminal-block ${stateClass}`);

  const titles = {
    'DELIVERED': '✓ Delivered', 'ARCHIVED': 'Archived — no action required',
    'AWAITING_HITL': 'Awaiting human review', 'HELD': 'Held — waiting for rollout',
    'DIGESTED': 'Queued for digest', 'FAILED': 'Pipeline failed', 'REJECTED': 'Rejected',
  };
  block.innerHTML = `<div class="terminal-block__title">${titles[state] || state}</div>`;

  const bodyEl = el('div', 'terminal-block__body');

  if (state === 'DELIVERED' && p.bu_outcomes && p.bu_outcomes.length) {
    const outcomeLine = p.bu_outcomes.map(o => `${escHtml(o.bu_id)} via ${escHtml(o.channel || '?')}`).join(', ');
    bodyEl.innerHTML = `<p>Sent to: <strong>${outcomeLine}</strong></p>`;
    bodyEl.appendChild(buildMessagePreview(p.bu_outcomes));
  } else if (state === 'AWAITING_HITL') {
    bodyEl.appendChild(buildHITLPanel());
  } else if (state === 'ARCHIVED') {
    bodyEl.textContent = 'This change does not warrant BU notification. The pipeline archived it cleanly.';
  } else if (state === 'HELD') {
    const reasons = (p.bu_outcomes || []).map(o => o.reason).filter(Boolean);
    bodyEl.textContent = reasons.length ? reasons[0] : 'Change is held pending rollout conditions.';
  } else if (state === 'FAILED') {
    const errs = p.errors || [];
    bodyEl.textContent = errs.length ? errs.join(' | ') : 'An unexpected error occurred in the pipeline.';
    const retryBtn = el('button', 'footer-btn primary');
    retryBtn.textContent = 'Retry';
    retryBtn.style.marginTop = '12px';
    retryBtn.addEventListener('click', () => runScenario(activeScenarioId));
    bodyEl.appendChild(retryBtn);
  }

  block.appendChild(bodyEl);
  body.appendChild(block);
  doc.appendChild(section);

  // Footer actions
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
  setRailCompleted('terminal', 'ss');
}

function renderPipelineError(p) {
  const doc = getRunContent();
  const card = el('div', 'terminal-block failed');
  card.innerHTML = `
    <div class="terminal-block__title">Pipeline error</div>
    <div class="terminal-block__body">${escHtml(p.message || 'An error occurred.')}</div>
  `;
  doc.appendChild(card);
}

// ── Message previews ───────────────────────────────────────────────────────

function buildMessagePreview(buOutcomes) {
  const wrap = el('div', 'msg-preview');
  const tabsEl = el('div', 'msg-preview__tabs');
  wrap.appendChild(tabsEl);

  const channels = ['teams', 'email', 'push'];
  const panels = {};
  const tabs = {};

  channels.forEach((ch, idx) => {
    const tab = el('button', `msg-tab${idx === 0 ? ' active' : ''}`);
    tab.textContent = capitalise(ch === 'push' ? 'Push' : ch === 'email' ? 'Email' : 'Teams');
    tab.addEventListener('click', () => {
      Object.values(tabs).forEach(t => t.classList.remove('active'));
      Object.values(panels).forEach(p => p.hidden = true);
      tab.classList.add('active');
      panels[ch].hidden = false;
    });
    tabsEl.appendChild(tab);
    tabs[ch] = tab;

    const panel = el('div', '');
    panel.hidden = idx !== 0;
    panels[ch] = panel;
    wrap.appendChild(panel);

    const bu = buOutcomes[0] || {};
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
      <div class="teams-card-mock__title">PulseCraft Change Alert</div>
    </div>
    <div class="teams-card-mock__body">
      A change affecting <strong>${escHtml(bu.bu_id || 'your BU')}</strong> has been processed and is ready for your review.
      Please review the details and take appropriate action.
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
    <div class="email-subject">Change notification: ${escHtml(bu.bu_id || 'your BU')}</div>
    <div class="email-body">
      A marketplace change relevant to your business unit has been processed by PulseCraft.
      <br><br>
      <strong>Action recommended:</strong> Review the change summary and confirm your team is aware of the impact.
      <br><br>
      This message was generated by the PulseCraft change intelligence service.
    </div>
  `;
  return email;
}

function buildPushMock(bu) {
  const push = el('div', 'push-mock');
  push.innerHTML = `
    <div class="push-icon">🔔</div>
    <div>
      <div class="push-title">PulseCraft alert</div>
      <div class="push-body">Change affecting ${escHtml(bu.bu_id || 'your BU')} — tap to review.</div>
    </div>
  `;
  return push;
}

function buildHITLPanel() {
  const panel = el('div', 'hitl-panel');
  panel.innerHTML = `
    <div class="hitl-panel__title">Operator review panel</div>
    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:12px">
      The proposed message is pending review. An operator can approve, reject, or edit before delivery.
    </p>
    <div class="hitl-panel__actions">
      <div class="hitl-action-btn approve">Approve</div>
      <div class="hitl-action-btn reject">Reject</div>
      <div class="hitl-action-btn edit">Edit</div>
      <div class="hitl-action-btn answer">Answer question</div>
    </div>
    <div class="hitl-panel__note">
      In production, operators receive a notification and approve via
      <code>pulsecraft approve</code> CLI or a dashboard.
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
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }

function getRunContent() {
  const rc = document.getElementById('run-content');
  rc.hidden = false;
  return rc;
}

function hideWelcome() {
  document.getElementById('welcome').hidden = true;
}

function resetDocument() {
  const rc = document.getElementById('run-content');
  rc.innerHTML = '';
  rc.hidden = true;
  document.getElementById('welcome').hidden = false;
}

function resetRail() {
  Object.values(railDots).forEach(d => {
    d.className = 'rail-dot';
  });
}

function createSection(id, agentOrHook, title, subtitle) {
  const section = el('div', 'pipeline-section');
  section.id = id;
  const accent = agentOrHook === 'hook' ? 'hook' : agentOrHook;
  section.innerHTML = `
    <div class="section-header">
      <div class="section-accent ${accent}"></div>
      <div>
        <div class="section-title">${escHtml(title)}</div>
        ${subtitle ? `<div class="section-sub text-tertiary">${escHtml(subtitle)}</div>` : ''}
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
  return { signalscribe: 'var(--ss-primary)', buatlas: 'var(--ba-primary)', pushpilot: 'var(--pp-primary)' }[agent] || '#999';
}

function agentSubtitle(agent, p) {
  const gates = (p.gate_batch || []).join(', ');
  return gates ? `Gates ${gates}` : '';
}

function sourceTypeSvg(type) {
  const icons = {
    release_note:   '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M3.5 5h7M3.5 7.5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    incident:       '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L13 12H1L7 1Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M7 5v3M7 9.5v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    feature_flag:   '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2v10M2 2h8l-2 3 2 3H2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    default:        '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.2"/><path d="M7 5v4M7 3.5v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
  };
  return icons[type] || icons.default;
}

// ── Cost counter ────────────────────────────────────────────────────────────

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
    body.textContent = `Loading audit trail for change ${changeId.slice(0, 8)}…\n\n` +
      `Run: pulsecraft explain ${changeId.slice(0, 8)} --verbose\n\n` +
      `Full change ID: ${changeId}\n\n` +
      `The /explain command renders every agent decision, policy override,\n` +
      `HITL event, and delivery outcome with timing and cost.`;
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
  doc.innerHTML = `<div class="terminal-block failed"><div class="terminal-block__title">Error</div><div class="terminal-block__body">${escHtml(msg)}</div></div>`;
  hideWelcome();
}

// ── Keyboard shortcuts ──────────────────────────────────────────────────────

function handleKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 5 && scenarios[n - 1]) {
    runScenario(scenarios[n - 1].id);
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
