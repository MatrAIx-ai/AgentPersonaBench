"use strict";
const workspace = document.querySelector('#workspace');
const STEP_NAMES = ['Choose features', 'Availability check', 'Save queue'];
let busy = false;
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function button(action, label, primary = false) {
  const el = node('button', label, primary ? 'primary' : '');
  el.type = 'button';
  el.dataset.action = action;
  el.addEventListener('click', () => act(action));
  return el;
}
// Decorative cassette, seeded only from the option id (neutral palette for every tape).
function seedOf(id) { let h = 7; for (const c of String(id)) h = (h * 31 + c.charCodeAt(0)) % 100003; return h; }
function cassette(id, w) {
  const s = seedOf(id);
  const shells = ['#e9e1d3', '#d9dde3', '#e7d8c6', '#dfe3da', '#e4dbe6'];
  const stripes = ['#ff8a3d', '#6c6475', '#2f9e7e', '#c9a86a', '#8aa2c8'];
  const shell = shells[s % shells.length], stripe = stripes[Math.floor(s / 7) % stripes.length];
  const lines = 2 + (s % 3);
  let ruled = '';
  for (let i = 0; i < lines; i++) ruled += `<line x1="14" y1="${17 + i * 4}" x2="${46 + ((s >> i) % 20)}" y2="${17 + i * 4}" stroke="#9a90a4" stroke-width=".8"/>`;
  const svgNS = 'http://www.w3.org/2000/svg';
  const wrap = document.createElement('span');
  wrap.setAttribute('aria-hidden', 'true');
  wrap.innerHTML = `<svg xmlns="${svgNS}" width="${w}" height="${Math.round(w * 0.64)}" viewBox="0 0 86 55">
    <rect x="1" y="1" width="84" height="53" rx="5" fill="${shell}" stroke="#231f29" stroke-width="1.5"/>
    <rect x="8" y="7" width="70" height="30" rx="3" fill="#fffaf2" stroke="#231f29" stroke-width="1"/>
    <rect x="8" y="7" width="70" height="7" rx="2" fill="${stripe}"/>
    ${ruled}
    <rect x="22" y="22" width="42" height="12" rx="6" fill="#231f29"/>
    <circle cx="30" cy="28" r="4" fill="${shell}"/><circle cx="56" cy="28" r="4" fill="${shell}"/>
    <path d="M20 54 L25 42 H61 L66 54" fill="none" stroke="#231f29" stroke-width="1.2"/>
    <circle cx="33" cy="48" r="1.6" fill="#231f29"/><circle cx="53" cy="48" r="1.6" fill="#231f29"/>
  </svg>`;
  return wrap;
}
async function act(action) {
  if (busy) return;
  busy = true;
  workspace.querySelectorAll('button').forEach(b => b.disabled = true);
  const error = document.querySelector('#error');
  error.hidden = true;
  try {
    const response = await fetch('/action', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The change could not be saved.');
    render(data);
  } catch (exc) {
    error.textContent = exc.message;
    error.hidden = false;
    workspace.querySelectorAll('button').forEach(b => b.disabled = false);
  } finally { busy = false; }
}
function renderSteps(view) {
  const ol = document.querySelector('#steps');
  ol.replaceChildren();
  for (let i = 0; i < view.stage_count; i++) {
    const li = node('li');
    const done = view.submitted || i < view.stage_index;
    li.className = done ? 'past' : (i === view.stage_index ? 'now' : '');
    li.append(node('b', done ? '✓' : String(i + 1)), document.createTextNode(STEP_NAMES[i] || ('Step ' + (i + 1))));
    ol.append(li);
  }
}
function render(view) {
  document.title = view.app + ' · ' + view.title;
  document.querySelector('#brand').textContent = view.app;
  document.querySelector('#subtitle').textContent = view.subtitle;
  document.querySelector('#progress').textContent = view.submitted ? 'Saved' : `Step ${view.stage_index + 1} of ${view.stage_count}`;
  renderSteps(view);
  workspace.replaceChildren();
  workspace.dataset.stage = view.stage_id;
  workspace.dataset.submitted = String(view.submitted);
  workspace.dataset.sessionId = view.session_id;
  workspace.dataset.revision = view.revision;
  if (view.submitted) {
    const receipt = node('section', undefined, 'receipt'); receipt.id = 'receipt';
    const head = node('div', undefined, 'head');
    head.append(cassette('saved-queue', 86));
    const ht = node('div'); ht.append(node('h1', 'All set'), node('p', view.receipt));
    head.append(ht); receipt.append(head);
    const dl = node('dl');
    view.groups.forEach(g => {
      const selected = g.options.find(o => o.id === view.selected[g.id]);
      dl.append(node('dt', g.title));
      const value = node('dd', selected.title);
      value.dataset.slot = g.id; value.dataset.selectionId = selected.id;
      dl.append(value);
    });
    receipt.append(dl); workspace.append(receipt); window.scrollTo(0,0); return;
  }
  workspace.append(node('h1', view.title), node('p', view.intro, 'intro'));
  if (view.notice) workspace.append(node('p', view.notice, 'notice'));
  if (view.detail || view.offer) {
    const item = view.detail || view.offer;
    const panel = node('section', undefined, 'liner');
    const art = node('div', undefined, 'art');
    art.append(cassette(item.id, 190));
    const copy = node('div', undefined, 'copy');
    copy.append(node('p', view.offer ? 'Station suggestion' : 'Recording notes', 'kicker'), node('h2', item.title));
    if (item.summary) copy.append(node('p', item.summary, 'sum'));
    copy.append(node('p', item.detail || item.description, 'body'));
    if (view.offer) {
      const list = node('ul');
      item.items.forEach(o => list.append(node('li', o.title + ' — ' + o.detail)));
      copy.append(list);
    }
    const actions = node('div', undefined, 'actions');
    view.actions.forEach((a,i) => actions.append(button(a.id,a.label,i === 0)));
    copy.append(actions);
    panel.append(art, copy); workspace.append(panel);
  } else {
    const labels = Object.fromEntries(view.actions.map(a => [a.id, a.label]));
    const cols = node('div', undefined, 'features');
    view.groups.forEach(group => {
      const col = node('section', undefined, 'feature');
      col.append(node('h2', group.title));
      const list = node('ul', undefined, 'tapes');
      group.options.forEach(opt => {
        const row = node('li', undefined, 'tape');
        const selected = view.selected[group.id] === opt.id;
        row.dataset.selected = String(selected);
        row.append(cassette(opt.id, 86));
        const copy = node('div', undefined, 'copy');
        copy.append(node('strong', opt.title), node('span', opt.summary, 'summary'));
        if (selected) copy.append(node('span', 'Selected', 'chosen'));
        row.append(copy);
        row.append(button('open:' + opt.id, labels['open:' + opt.id] || ('Details · ' + opt.title)));
        list.append(row);
      });
      col.append(list); cols.append(col);
    });
    workspace.append(cols);
    const actions = node('div', undefined, 'actions');
    view.actions.filter(a => !a.id.startsWith('open:')).forEach(a => {
      actions.append(button(a.id,a.label,a.id === 'next' || a.id === 'submit'));
    });
    workspace.append(actions);
    if (!view.actions.some(a => a.id === 'next' || a.id === 'submit'))
      workspace.append(node('p','Choose one option in each section to continue.','hint'));
  }
  window.scrollTo(0,0);
}
fetch('/state').then(r => r.json()).then(render).catch(() => {
  workspace.replaceChildren(node('p','The workspace could not be opened. Please reload the page.'));
});
