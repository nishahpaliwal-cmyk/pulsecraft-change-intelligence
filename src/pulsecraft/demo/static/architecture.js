/**
 * PulseCraft Architecture Tab — interactive animated SVG diagram.
 * Entry point: initArchitecture(), called when the Architecture tab is shown.
 * No framework, no dependencies beyond what the main app already loads.
 */

// ── Architecture content data ──────────────────────────────────────────────

const ARCH = {
  nodes: {
    ingest: {
      id: 'ingest',
      label: 'Ingest',
      sub: 'pre_ingest hook',
      color: 'hook',
      cx: 120, cy: 65,
      detail: {
        heading: 'Ingest + pre_ingest hook',
        body: `A ChangeArtifact arrives from any source: release notes, Jira work items, feature flags, incidents, or documents. Before it touches any agent, the pre_ingest hook scrubs PII and credentials from raw_text using regex patterns.\n\nFail mode: closed. If the hook blocks, the pipeline transitions to FAILED rather than passing unsafe content downstream.`,
        pills: ['pre_ingest hook', 'PII redaction', 'fail-closed'],
        accent: 'hook',
      },
    },
    signalscribe: {
      id: 'signalscribe',
      label: 'SignalScribe',
      sub: 'Gates 1 · 2 · 3',
      color: 'ss',
      cx: 300, cy: 65,
      detail: {
        heading: 'SignalScribe — Gates 1, 2, 3',
        body: `SignalScribe is the first agent in the pipeline. It owns three sequential judgment gates:\n\nGate 1 (worth communicating?) decides COMMUNICATE vs ARCHIVE vs ESCALATE. A pure internal refactor gets ARCHIVE; a customer-facing behavior change gets COMMUNICATE.\n\nGate 2 (ripe?) decides whether the timing is right: RIPE, HOLD_UNTIL(date), or HOLD_INDEFINITE. A feature at 1% rollout holds; GA imminent is ripe.\n\nGate 3 (clear?) confirms SignalScribe has a clean enough understanding to hand off: READY, NEED_CLARIFICATION(questions), or UNRESOLVABLE.\n\nIf any gate routes to ARCHIVE, HOLD, or HITL — later gates are skipped.`,
        pills: ['claude-sonnet-4-6', 'Gates 1–3', 'sequential'],
        accent: 'ss',
      },
    },
    post_ss: {
      id: 'post_ss',
      label: 'post_agent',
      sub: 'hook',
      color: 'hook',
      cx: 480, cy: 65,
      detail: {
        heading: 'post_agent hook',
        body: `After SignalScribe returns, the post_agent hook runs two policy checks:\n\n1. Confidence threshold — for positive verbs (COMMUNICATE + RIPE + READY), each decision must meet the gate-specific minimum confidence. If any falls short, the change routes to HITL with reason confidence_below_threshold.\n\n2. Restricted-term scan — the change brief's narrative text is scanned for commitment phrases, MLR-sensitive words, and credential patterns. A hit routes to HITL with reason restricted_term.\n\nRouting verbs (ARCHIVE, ESCALATE, HOLD_INDEFINITE) skip the confidence check — the routing decision IS the safeguard.`,
        pills: ['confidence check', 'restricted-term scan', 'fail-closed'],
        accent: 'hook',
      },
    },
    buatlas: {
      id: 'buatlas',
      label: 'BUAtlas',
      sub: 'Gates 4 · 5 · asyncio fan-out',
      color: 'ba',
      cx: 660, cy: 65,
      detail: {
        heading: 'BUAtlas — Gates 4 & 5 (parallel per-BU)',
        body: `The orchestrator first runs a deterministic BU pre-filter: it intersects the change brief's impact_areas with each BU's owned_product_areas in the registry. Only matching BUs get a BUAtlas invocation.\n\nFor each candidate BU, BUAtlas runs in parallel via asyncio.gather — every BU is reasoned about simultaneously, not sequentially. Each invocation is isolated: a failure in one BU does not affect the others.\n\nGate 4 (affected?) — AFFECTED vs ADJACENT vs NOT_AFFECTED. NOT_AFFECTED BUs are dropped; ADJACENT proceed cautiously.\n\nGate 5 (worth sending?) — WORTH_SENDING vs WEAK vs NOT_WORTH. Only WORTH_SENDING briefs reach PushPilot.\n\nEach BU gets a personalized brief with BU-specific message variants in three channels: Teams, email, push.`,
        pills: ['claude-sonnet-4-6', 'Gates 4–5', 'asyncio fan-out', 'per-BU isolation'],
        accent: 'ba',
      },
    },
    pushpilot: {
      id: 'pushpilot',
      label: 'PushPilot',
      sub: 'Gate 6',
      color: 'pp',
      cx: 840, cy: 65,
      detail: {
        heading: 'PushPilot — Gate 6 (delivery timing)',
        body: `PushPilot runs only when no HITL trigger has fired (see pre_deliver). It receives every WORTH_SENDING personalized brief and decides:\n\nSEND_NOW — notify immediately\nHOLD_UNTIL(time) — schedule for a specific time window\nDIGEST — bundle with other low-urgency items\nESCALATE — route to human if timing is genuinely ambiguous\n\nThe agent-vs-code split is intentional: PushPilot expresses its unvarnished delivery preference. The pre_deliver hook then independently enforces policy invariants (quiet hours, channel approval, HITL rules). When the two disagree, both decisions are recorded — enabling calibration of policy against agent judgment over time.`,
        pills: ['claude-sonnet-4-6', 'Gate 6', 'agent-vs-code split'],
        accent: 'pp',
      },
    },
    pre_deliver: {
      id: 'pre_deliver',
      label: 'pre_deliver',
      sub: 'hook',
      color: 'hook',
      cx: 1000, cy: 65,
      detail: {
        heading: 'pre_deliver hook — policy enforcement',
        body: `The pre_deliver hook is the last policy gate before any notification leaves the system. It enforces three classes of rules:\n\nHITL routing — when priority_p0 (BU head assigned P0 urgency), mlr_sensitive (scientific communication language detected), confidence_below_threshold, restricted_term, or a dedupe conflict triggers, the pipeline routes to AWAITING_HITL. An operator reviews and approves, rejects, or edits before delivery proceeds.\n\nQuiet hours — if the current time falls in the BU's quiet window (e.g., 21:00–07:00 local time), SEND_NOW is overridden to HOLD_UNTIL(morning).\n\nChannel approval — only channels explicitly approved in the BU's channel policy may receive notifications.\n\nThis hook runs on the code side. It has access to the system clock and policy config — things an LLM can't reliably reason about. When it overrides PushPilot's preference, the divergence is recorded in the audit trail for ongoing calibration.`,
        pills: ['HITL routing', 'quiet hours', 'channel policy', 'fail-closed', 'divergence audit'],
        accent: 'hook',
      },
    },
    terminal: {
      id: 'terminal',
      label: 'Terminal state',
      sub: 'DELIVERED · ARCHIVED · HELD · AWAITING_HITL',
      color: 'ok',
      cx: 1000, cy: 190,
      detail: {
        heading: 'Terminal states',
        body: `Every pipeline run ends in exactly one terminal state:\n\nDELIVERED — notifications sent via Teams, email, and/or push for all WORTH_SENDING BUs.\n\nARCHIVED — SignalScribe decided the change was not worth communicating. Clean and intentional.\n\nHELD — SignalScribe said HOLD_UNTIL or HOLD_INDEFINITE. Change is queued until conditions are met.\n\nDIGESTED — PushPilot chose DIGEST for all BUs. Change is bundled into the next digest.\n\nAWAITING_HITL — a policy trigger fired in pre_deliver; operators must approve, reject, or edit before delivery.\n\nFAILED — an unexpected error or hook block halted the pipeline. Retry is safe.\n\nREJECTED — an operator rejected a HITL-pending notification.`,
        pills: ['DELIVERED', 'ARCHIVED', 'HELD', 'AWAITING_HITL', 'FAILED', 'REJECTED'],
        accent: 'ok',
      },
    },
    audit: {
      id: 'audit',
      label: 'Audit trail',
      sub: 'every decision',
      color: 'neutral',
      cx: 300, cy: 190,
      detail: {
        heading: 'Audit trail — append-only JSONL',
        body: `Every significant event in the pipeline writes an AuditRecord to an append-only JSONL file, sharded by date and change ID. The audit writer never propagates exceptions — it is observability infrastructure, not correctness infrastructure.\n\nThe audit chain captures: state transitions, every agent decision with confidence and reasoning, every hook firing, HITL events, and delivery outcomes including dedupe keys.\n\nOperators can replay the full decision trail with:\n  pulsecraft explain <change_id>\n\nThe /explain command renders every step with timing, cost, and agent reasoning in a human-readable format.`,
        pills: ['append-only JSONL', 'per-change shard', 'pulsecraft explain'],
        accent: 'neutral',
      },
    },
  },

  edges: [
    { from: 'ingest',       to: 'signalscribe', label: 'artifact' },
    { from: 'signalscribe', to: 'post_ss',       label: 'decisions' },
    { from: 'post_ss',      to: 'buatlas',       label: 'brief' },
    { from: 'buatlas',      to: 'pushpilot',     label: 'per-BU briefs' },
    { from: 'pushpilot',    to: 'pre_deliver',   label: 'preference' },
    { from: 'pre_deliver',  to: 'terminal',      label: 'enforce' },
    { from: 'signalscribe', to: 'terminal',      label: 'ARCHIVE/HOLD', style: 'dashed', shortcut: true },
    { from: 'ingest',       to: 'audit',         label: '', style: 'audit' },
    { from: 'signalscribe', to: 'audit',         label: '', style: 'audit' },
    { from: 'buatlas',      to: 'audit',         label: '', style: 'audit' },
    { from: 'pushpilot',    to: 'audit',         label: '', style: 'audit' },
    { from: 'terminal',     to: 'audit',         label: '', style: 'audit' },
  ],
};

// ── SVG layout constants ───────────────────────────────────────────────────

const SVG_W = 1100;
const SVG_H = 240;
const NODE_RX = 8;
const NODE_W  = 130;
const NODE_H  = 52;
const NODE_HH = NODE_H / 2;
const NODE_HW = NODE_W / 2;

// Colour map (must match CSS variables)
const COLOR = {
  ss:      '#534AB7',
  ba:      '#0F6E56',
  pp:      '#993C1D',
  hook:    '#854F0B',
  ok:      '#3B6D11',
  neutral: '#444441',
};

// ── Module state ─────────────────────────────────────────────────────────

let _initialized = false;
let _svg = null;
let _detailPanel = null;
let _activeNodeId = null;
let _replayBtn = null;
let _entranceRafId = null;

// ── Public API ────────────────────────────────────────────────────────────

export function initArchitecture() {
  if (_initialized) {
    _runEntrance();
    return;
  }
  _initialized = true;
  _buildDOM();
  _buildSVG();
  _buildDetailPanel();
  _buildReplayBtn();
  _buildCallout();
  _bindKeys();
  _runEntrance();
}

export function teardownArchitecture() {
  if (_entranceRafId) { cancelAnimationFrame(_entranceRafId); _entranceRafId = null; }
}

// ── DOM scaffold ──────────────────────────────────────────────────────────

function _buildDOM() {
  const root = document.getElementById('arch-root');
  if (!root) return;
  root.innerHTML = '';
  root.className = 'arch-root';

  const heading = document.createElement('div');
  heading.className = 'arch-heading';
  heading.id = 'arch-heading';
  heading.innerHTML = `
    <div class="arch-heading__text">
      <h2 class="arch-heading__title">System architecture</h2>
      <p class="arch-heading__sub">Three LLM agents, four guardrail hooks, one deterministic orchestrator. Click any node.</p>
    </div>
  `;
  root.appendChild(heading);

  const canvas = document.createElement('div');
  canvas.className = 'arch-canvas';
  canvas.id = 'arch-canvas';

  _svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  _svg.setAttribute('viewBox', `0 0 ${SVG_W} ${SVG_H}`);
  _svg.setAttribute('aria-label', 'PulseCraft architecture diagram');
  _svg.setAttribute('role', 'img');
  _svg.id = 'arch-svg';
  canvas.appendChild(_svg);
  root.appendChild(canvas);

  _detailPanel = document.createElement('div');
  _detailPanel.className = 'arch-detail';
  _detailPanel.id = 'arch-detail';
  _detailPanel.setAttribute('aria-live', 'polite');
  root.appendChild(_detailPanel);
}

// ── SVG builder ───────────────────────────────────────────────────────────

function _buildSVG() {
  const defs = _svgEl('defs');

  ['main', 'dashed', 'audit'].forEach(type => {
    const color = type === 'audit' ? '#C9C1B0' : '#8D877B';
    const marker = _svgEl('marker');
    marker.id = `arrowhead-${type}`;
    marker.setAttribute('markerWidth', '8');
    marker.setAttribute('markerHeight', '6');
    marker.setAttribute('refX', '7');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    const poly = _svgEl('polygon');
    poly.setAttribute('points', '0 0, 8 3, 0 6');
    poly.setAttribute('fill', color);
    marker.appendChild(poly);
    defs.appendChild(marker);
  });
  _svg.appendChild(defs);

  _drawEdges();
  Object.values(ARCH.nodes).forEach(node => _drawNode(node));
}

function _drawEdges() {
  const g = _svgEl('g');
  g.id = 'arch-edges';
  g.setAttribute('class', 'arch-edges');

  ARCH.edges.forEach((edge, i) => {
    const from = ARCH.nodes[edge.from];
    const to   = ARCH.nodes[edge.to];
    if (!from || !to) return;

    const style = edge.style || 'solid';
    const isAudit = style === 'audit';
    const isDashed = style === 'dashed' || isAudit;
    const color = isAudit ? '#C9C1B0' : '#8D877B';
    const markerUrl = `url(#arrowhead-${isAudit ? 'audit' : isDashed ? 'dashed' : 'main'})`;

    const { x1, y1, x2, y2 } = _edgePoints(from, to);
    const d = _routePath(x1, y1, x2, y2);
    const len = _approxPathLen(d);

    const path = _svgEl('path');
    path.setAttribute('d', d);
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', isAudit ? '1' : '1.5');
    path.setAttribute('fill', 'none');
    if (isDashed) path.setAttribute('stroke-dasharray', isAudit ? '3 4' : '6 4');
    path.setAttribute('marker-end', markerUrl);
    path.setAttribute('class', `arch-edge arch-edge--${style}`);
    path.dataset.edgeIndex = i;
    path.style.strokeDasharray = len;
    path.style.strokeDashoffset = len;
    path.dataset.len = len;
    g.appendChild(path);

    if (edge.label && !isAudit) {
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;
      const text = _svgEl('text');
      text.setAttribute('x', mx);
      text.setAttribute('y', my - 5);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('class', 'arch-edge-label');
      text.textContent = edge.label;
      g.appendChild(text);
    }
  });

  _svg.appendChild(g);
}

function _drawNode(node) {
  const g = _svgEl('g');
  g.setAttribute('class', `arch-node arch-node--${node.color}`);
  g.setAttribute('tabindex', '0');
  g.setAttribute('role', 'button');
  g.setAttribute('aria-label', node.label);
  g.dataset.nodeId = node.id;

  const x = node.cx - NODE_HW;
  const y = node.cy - NODE_HH;
  const accent = COLOR[node.color] || '#8D877B';

  // BUAtlas: stacked ghost cards signal parallel per-BU fan-out at a glance.
  // Ghost cards are drawn first so they sit behind the main card in SVG stacking order.
  if (node.id === 'buatlas') {
    [{ off: 8, op: 0.22 }, { off: 4, op: 0.42 }].forEach(({ off, op }) => {
      const gr = _svgEl('rect');
      gr.setAttribute('x', x + off);
      gr.setAttribute('y', y + off);
      gr.setAttribute('width', NODE_W);
      gr.setAttribute('height', NODE_H);
      gr.setAttribute('rx', NODE_RX);
      gr.setAttribute('fill', '#FFFFFF');
      gr.setAttribute('stroke', accent);
      gr.setAttribute('stroke-width', '1.5');
      gr.setAttribute('opacity', op);
      gr.setAttribute('pointer-events', 'none');
      g.appendChild(gr);

      const gb = _svgEl('rect');
      gb.setAttribute('x', x + off);
      gb.setAttribute('y', y + off);
      gb.setAttribute('width', '4');
      gb.setAttribute('height', NODE_H);
      gb.setAttribute('rx', NODE_RX);
      gb.setAttribute('fill', accent);
      gb.setAttribute('opacity', op);
      gb.setAttribute('pointer-events', 'none');
      g.appendChild(gb);
    });
  }

  // Shadow
  const shadow = _svgEl('rect');
  shadow.setAttribute('x', x + 2);
  shadow.setAttribute('y', y + 2);
  shadow.setAttribute('width', NODE_W);
  shadow.setAttribute('height', NODE_H);
  shadow.setAttribute('rx', NODE_RX);
  shadow.setAttribute('fill', 'rgba(0,0,0,0.05)');
  shadow.setAttribute('class', 'arch-node-shadow');
  g.appendChild(shadow);

  // Main rect
  const rect = _svgEl('rect');
  rect.setAttribute('x', x);
  rect.setAttribute('y', y);
  rect.setAttribute('width', NODE_W);
  rect.setAttribute('height', NODE_H);
  rect.setAttribute('rx', NODE_RX);
  rect.setAttribute('fill', '#FFFFFF');
  rect.setAttribute('stroke', '#E5DFD4');
  rect.setAttribute('stroke-width', '1.5');
  rect.setAttribute('class', 'arch-node-rect');
  g.appendChild(rect);

  // Accent bar
  const bar = _svgEl('rect');
  bar.setAttribute('x', x);
  bar.setAttribute('y', y);
  bar.setAttribute('width', '4');
  bar.setAttribute('height', NODE_H);
  bar.setAttribute('rx', NODE_RX);
  bar.setAttribute('fill', accent);
  bar.setAttribute('class', 'arch-node-bar');
  g.appendChild(bar);

  // Label
  const label = _svgEl('text');
  label.setAttribute('x', x + NODE_HW + 2);
  label.setAttribute('y', y + 22);
  label.setAttribute('text-anchor', 'middle');
  label.setAttribute('class', 'arch-node-label');
  label.textContent = node.label;
  g.appendChild(label);

  // Subtitle
  if (node.sub) {
    const sub = _svgEl('text');
    sub.setAttribute('x', x + NODE_HW + 2);
    sub.setAttribute('y', y + 37);
    sub.setAttribute('text-anchor', 'middle');
    sub.setAttribute('class', 'arch-node-sub');
    sub.textContent = node.sub;
    g.appendChild(sub);
  }

  g.addEventListener('click', () => _selectNode(node.id));
  g.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); _selectNode(node.id); }
  });

  g.style.opacity = '0';
  g.style.transform = 'translate(0, 8px)';
  g.id = `arch-node-${node.id}`;

  _svg.appendChild(g);
}

// ── Edge routing ──────────────────────────────────────────────────────────

function _edgePoints(from, to) {
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  let x1, y1, x2, y2;

  if (Math.abs(dx) > Math.abs(dy)) {
    if (dx > 0) {
      x1 = from.cx + NODE_HW; y1 = from.cy;
      x2 = to.cx - NODE_HW;   y2 = to.cy;
    } else {
      x1 = from.cx - NODE_HW; y1 = from.cy;
      x2 = to.cx + NODE_HW;   y2 = to.cy;
    }
  } else {
    if (dy > 0) {
      x1 = from.cx; y1 = from.cy + NODE_HH;
      x2 = to.cx;   y2 = to.cy - NODE_HH;
    } else {
      x1 = from.cx; y1 = from.cy - NODE_HH;
      x2 = to.cx;   y2 = to.cy + NODE_HH;
    }
  }
  return { x1, y1, x2, y2 };
}

function _routePath(x1, y1, x2, y2) {
  const dx = x2 - x1;
  const cx1 = x1 + dx * 0.5;
  const cx2 = x2 - dx * 0.5;
  return `M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`;
}

function _approxPathLen(d) {
  const parts = d.split(/[\s,]+/).filter(Boolean);
  const x1 = parseFloat(parts[1]);
  const y1 = parseFloat(parts[2]);
  const x2 = parseFloat(parts[parts.length - 2]);
  const y2 = parseFloat(parts[parts.length - 1]);
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * 1.4 + 20;
}

// ── Detail panel ──────────────────────────────────────────────────────────

function _buildDetailPanel() {
  _detailPanel.innerHTML = `
    <div class="arch-detail__placeholder">
      <span>Click any node to see its role in the pipeline.</span>
    </div>
  `;
}

function _selectNode(nodeId) {
  const node = ARCH.nodes[nodeId];
  if (!node || !node.detail) return;

  if (_activeNodeId) {
    const old = document.getElementById(`arch-node-${_activeNodeId}`);
    if (old) old.classList.remove('selected');
  }
  _activeNodeId = nodeId;

  const el = document.getElementById(`arch-node-${nodeId}`);
  if (el) el.classList.add('selected');

  const d = node.detail;
  const accentColor = COLOR[d.accent] || '#8D877B';
  const pillsHtml = (d.pills || []).map(p =>
    `<span class="arch-pill" style="border-color:${accentColor};color:${accentColor}">${_esc(p)}</span>`
  ).join('');

  const bodyHtml = _esc(d.body).replace(/\n\n/g, '</p><p class="arch-detail__body">').replace(/\n/g, '<br>');

  _detailPanel.innerHTML = `
    <div class="arch-detail__inner">
      <div class="arch-detail__accent" style="background:${accentColor}"></div>
      <div class="arch-detail__content">
        <div class="arch-detail__heading">${_esc(d.heading)}</div>
        <p class="arch-detail__body">${bodyHtml}</p>
        ${pillsHtml ? `<div class="arch-detail__pills">${pillsHtml}</div>` : ''}
      </div>
    </div>
  `;
}

// ── Entrance choreography ─────────────────────────────────────────────────

function _runEntrance() {
  const nodeEls = _svg.querySelectorAll('.arch-node');
  nodeEls.forEach(n => {
    n.style.opacity = '0';
    n.style.transform = 'translate(0, 8px)';
    n.style.transition = '';
  });

  const edgeEls = _svg.querySelectorAll('.arch-edge');
  edgeEls.forEach(e => {
    const len = e.dataset.len || '200';
    e.style.strokeDasharray = len;
    e.style.strokeDashoffset = len;
    e.style.transition = '';
  });

  const nodeOrder = [
    'ingest', 'signalscribe', 'post_ss', 'buatlas',
    'pushpilot', 'pre_deliver', 'terminal', 'audit',
  ];

  let delay = 80;
  nodeOrder.forEach(id => {
    const el = document.getElementById(`arch-node-${id}`);
    if (!el) return;
    setTimeout(() => {
      el.style.transition = 'opacity 380ms cubic-bezier(0.2,0.8,0.2,1), transform 380ms cubic-bezier(0.2,0.8,0.2,1)';
      el.style.opacity = '1';
      el.style.transform = 'translate(0, 0)';
    }, delay);
    delay += 120;
  });

  const edgesStart = delay + 100;
  edgeEls.forEach((e, i) => {
    const dur = 400 + i * 80;
    setTimeout(() => {
      e.style.transition = `stroke-dashoffset ${dur}ms cubic-bezier(0.4,0,0.2,1)`;
      e.style.strokeDashoffset = '0';
    }, edgesStart + i * 60);
  });

  const labelsStart = edgesStart + edgeEls.length * 60 + 400;
  const labelEls = _svg.querySelectorAll('.arch-edge-label');
  labelEls.forEach((l, i) => {
    l.style.opacity = '0';
    setTimeout(() => {
      l.style.transition = 'opacity 300ms ease';
      l.style.opacity = '1';
    }, labelsStart + i * 60);
  });
}

// ── Replay button (header area, flex sibling of heading text) ────────────

function _buildReplayBtn() {
  const heading = document.getElementById('arch-heading');
  if (!heading) return;
  _replayBtn = document.createElement('button');
  _replayBtn.className = 'arch-replay-btn';
  _replayBtn.setAttribute('aria-label', 'Replay entrance animation');
  _replayBtn.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2 7a5 5 0 1 0 1.5-3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      <path d="M2 3v4h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Replay
  `;
  _replayBtn.addEventListener('click', () => {
    _activeNodeId = null;
    _svg.querySelectorAll('.arch-node.selected').forEach(n => n.classList.remove('selected'));
    _buildDetailPanel();
    _runEntrance();
  });
  heading.appendChild(_replayBtn);
}

// ── Agent-vs-code principle callout ──────────────────────────────────────

function _buildCallout() {
  const root = document.getElementById('arch-root');
  if (!root) return;
  const callout = document.createElement('div');
  callout.className = 'arch-callout';
  callout.innerHTML = `
    <p class="arch-callout__principle">Agents express preferences based on context. Code enforces invariants based on policy. When they diverge, policy wins — and both are logged.</p>
    <p class="arch-callout__explanation">The pre_deliver hook is the primary site of this divergence. Three agents reason about what should happen; guardrail hooks enforce what is allowed to happen. Both judgments are captured in the audit trail, enabling ongoing calibration between agent confidence and policy thresholds.</p>
  `;
  root.appendChild(callout);
}

// ── Keyboard nav ──────────────────────────────────────────────────────────

function _bindKeys() {
  document.addEventListener('keydown', _onKey);
}

function _onKey(e) {
  const root = document.getElementById('arch-root');
  if (!root || root.closest('[hidden]')) return;

  if (e.key === 'Escape' && _activeNodeId) {
    const el = document.getElementById(`arch-node-${_activeNodeId}`);
    if (el) el.classList.remove('selected');
    _activeNodeId = null;
    _buildDetailPanel();
    return;
  }

  const nodeOrder = Object.keys(ARCH.nodes);
  const idx = _activeNodeId ? nodeOrder.indexOf(_activeNodeId) : -1;
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault();
    _selectNode(nodeOrder[(idx + 1) % nodeOrder.length]);
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault();
    _selectNode(nodeOrder[(idx - 1 + nodeOrder.length) % nodeOrder.length]);
  }
}

// ── SVG helpers ───────────────────────────────────────────────────────────

function _svgEl(tag) {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}

function _esc(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
