"use strict";
const workspace=document.querySelector('#workspace');
let busy=false;
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined&&text!==null)el.textContent=text;if(cls)el.className=cls;return el;}
function button(action,label,cls){const el=node('button',label,cls||'');el.type='button';el.dataset.action=action;el.addEventListener('click',()=>act(action));return el;}
function actionFor(view,id){return view.actions.find(a=>a.id===id);}
async function act(action){
  if(busy)return;busy=true;workspace.querySelectorAll('button').forEach(b=>b.disabled=true);
  const error=document.querySelector('#error');error.hidden=true;
  try{const response=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});const view=await response.json();if(!response.ok)throw new Error(view.error);render(view);}
  catch(e){error.textContent=e.message;error.hidden=false;workspace.querySelectorAll('button').forEach(b=>b.disabled=false);}
  finally{busy=false;}
}
/* Decorative covers: colours and pattern come from the option id only. */
function hash(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
const PAL=[['#2f4858','#f2e8d5','#d9a86c'],['#5a3e4b','#f5ebdc','#e0b07a'],['#34505a','#efe6d6','#c98f6b'],['#4b4a6b','#f3eadb','#d7b27c'],['#3d4f3f','#f1e7d3','#c9a15f'],['#6a4a3a','#f4eadb','#b9c4c9']];
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function coverSVG(id,title){
  const h=hash(id),p=PAL[h%PAL.length],k=(h>>>4)%4;let s=`<svg viewBox="0 0 120 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect width="120" height="180" fill="${p[0]}"/>`;
  if(k===0)s+=`<circle cx="60" cy="72" r="30" fill="${p[2]}"/><rect x="0" y="100" width="120" height="3" fill="${p[1]}" opacity=".6"/>`;
  else if(k===1){for(let i=0;i<6;i++)s+=`<rect x="0" y="${30+i*12}" width="120" height="5" fill="${i%2?p[2]:p[1]}" opacity="${.35+i*.1}"/>`;}
  else if(k===2)s+=`<path d="M0 110 L40 60 L66 88 L88 52 L120 100 L120 180 L0 180Z" fill="${p[2]}" opacity=".9"/>`;
  else s+=`<rect x="22" y="30" width="76" height="76" fill="none" stroke="${p[2]}" stroke-width="5"/><rect x="38" y="46" width="44" height="44" fill="${p[1]}" opacity=".5"/>`;
  s+=`<rect x="0" y="0" width="5" height="180" fill="#000" opacity=".18"/>`;
  const words=String(title).split(' ');let lines=[''];words.forEach(w=>{if((lines[lines.length-1]+' '+w).trim().length>13)lines.push(w);else lines[lines.length-1]=(lines[lines.length-1]+' '+w).trim();});
  lines.slice(0,3).forEach((l,i)=>{s+=`<text x="12" y="${132+i*14}" font-family="Bitstream Charter, Georgia, serif" font-size="12" fill="${p[1]}">${esc(l)}</text>`;});
  return s+'</svg>';
}
function cover(opt){const c=node('div',undefined,'cover');if(opt){c.innerHTML=coverSVG(opt.id,opt.title);}else{c.classList.add('empty');c.textContent='No selection yet';c.setAttribute('aria-hidden','true');}return c;}
function avatar(owner){const a=node('span',owner==='You'?'Y':owner.charAt(0),'av');a.setAttribute('aria-hidden','true');if(owner!=='You')a.style.background='#8a6d4a';return a;}
function choices(view){
  const section=node('section',undefined,'receipt');
  if(view.submitted)section.id='receipt';
  const dl=node('dl');
  view.groups.forEach(g=>{
    const opt=g.options.find(o=>o.id===view.selected[g.id]);
    const row=node('div',undefined,'rrow');row.append(cover(opt));
    const body=node('div');
    body.append(node('dt',g.title+' · Assigned to '+g.owner));
    const dd=node('dd',opt?opt.title:'No selection');dd.dataset.slot=g.id;dd.dataset.selectionId=opt?opt.id:'';body.append(dd);
    if(opt)body.append(node('dd',opt.detail,'muted'));
    row.append(body);dl.append(row);
  });section.append(dl);return section;
}
function heading(eyebrow,title){const f=document.createDocumentFragment();f.append(node('div',eyebrow,'eyebrow'),node('h1',title));return f;}
function render(view){
  document.title=view.app+' · '+view.title;
  document.querySelector('#brand').textContent=view.app;document.querySelector('#subtitle').textContent=view.subtitle;
  document.querySelector('#progress').textContent=view.submitted?'Saved':view.stage_id==='review'?'Review':`${Object.values(view.selected).filter(Boolean).length} / ${view.groups.length} assigned`;
  workspace.replaceChildren();workspace.dataset.stage=view.stage_id;workspace.dataset.submitted=String(view.submitted);workspace.dataset.sessionId=view.session_id;workspace.dataset.revision=view.revision;
  const actions=node('div',undefined,'actions');
  if(view.submitted){
    workspace.append(heading('Shared draft','Assignments saved'));
    const d=node('div',undefined,'done');d.append(node('span','✓','ck'),node('span',view.receipt));workspace.append(d,choices(view));return;
  }
  if(view.stage_id==='review'){
    workspace.append(heading('Final check','Review every assignment'),node('p','These are the assignments that will be saved. You can return to the draft to change any entry.','lede'),choices(view));
    view.actions.forEach(a=>actions.append(button(a.id,a.label,a.id==='submit'?'primary':'')));
    workspace.append(actions);window.scrollTo(0,0);return;
  }
  if(view.package){
    const pack=view.package;
    workspace.append(node('div','Import preview','eyebrow'));
    const box=node('section',undefined,'imp');const hd=node('div',undefined,'imp-h');hd.append(node('h2',pack.title),node('p',pack.description));box.append(hd);
    const table=node('table');const thead=node('thead');const hr=node('tr');['Entry','Current','Replacement','Status',''].forEach(t=>hr.append(node('th',t)));thead.append(hr);table.append(thead);
    const tb=node('tbody');
    view.groups.filter(g=>Object.hasOwn(pack.selections,g.id)).forEach(g=>{
      const opt=g.options.find(o=>o.id===pack.selections[g.id]);const now=g.options.find(o=>o.id===view.selected[g.id]);const included=view.scope.includes(g.id);
      const tr=node('tr');tr.dataset.selected=String(included);
      const c1=node('td');const w=node('div');w.style.cssText='display:flex;gap:10px;align-items:center';const t=node('div');t.append(node('strong',g.title),node('div','Assigned to '+g.owner,'muted'));w.append(avatar(g.owner),t);c1.append(w);
      const c2=node('td',now?now.title:'No selection yet');
      const c3=node('td');c3.append(node('span','→ ','arrow'),node('span','Replace with '+opt.title));const dtl=node('div',opt.detail,'muted');dtl.style.fontSize='12.5px';dtl.style.marginTop='4px';c3.append(dtl);
      const c4=node('td');c4.append(node('span',included?'Included':'Excluded','state'));
      const c5=node('td');const a=actionFor(view,'scope:'+g.id);if(a){const b=button(a.id,a.label,'small');b.setAttribute('aria-pressed',String(included));c5.append(b);}
      tr.append(c1,c2,c3,c4,c5);tb.append(tr);
    });table.append(tb);box.append(table);workspace.append(box);
    view.actions.filter(a=>!a.id.startsWith('scope:')).forEach(a=>actions.append(button(a.id,a.label,a.id==='apply'?'primary':'')));
    workspace.append(actions);window.scrollTo(0,0);return;
  }
  if(view.active){
    const group=view.groups.find(g=>g.id===view.active);
    workspace.append(node('div','Shared draft  ›  '+group.title+'  ›  '+(view.detail?view.detail.title:'Catalog'),'crumbs'));
    if(view.detail){
      const panel=node('section',undefined,'detail');const opt=group.options.find(o=>o.id===view.detail.id)||view.detail;
      panel.append(cover(opt));
      const body=node('div');body.append(node('div','Editing '+group.title+' · Assigned to '+group.owner,'eyebrow'),node('h2',view.detail.title),node('p',view.detail.detail,'blurb'));
      const facts=node('div',undefined,'facts');(view.detail.summary||'').split(' · ').forEach((f,i)=>{const d=node('div');d.append(node('span',['Format','Length','Price'][i]||''),node('b',f));facts.append(d);});body.append(facts);
      view.actions.forEach(a=>actions.append(button(a.id,a.label,a.id.startsWith('pick:')?'primary':'')));
      body.append(actions);panel.append(body);workspace.append(panel);window.scrollTo(0,0);return;
    }
    workspace.append(heading('Editing '+group.title+' · Assigned to '+group.owner,'Choose a title'),node('p',group.brief,'lede'));
    const shelf=node('div',undefined,'shelf');
    group.options.forEach(opt=>{
      const on=view.selected[group.id]===opt.id;
      const b=node('article',undefined,'book');b.dataset.selected=String(on);
      b.append(cover(opt),node('div',on?'Current choice':'','cur'),node('div',opt.title,'bt'),node('div',opt.summary,'bs'));
      const a=actionFor(view,'open:'+opt.id);if(a)b.append(button(a.id,a.label,'small'));
      shelf.append(b);
    });workspace.append(shelf);
    const c=actionFor(view,'close');if(c)actions.append(button(c.id,c.label));
    workspace.append(actions);window.scrollTo(0,0);return;
  }
  workspace.append(heading('Shared draft',view.title),node('p',view.intro,'lede'));
  const n=node('div',undefined,'notice');n.append(node('span','i','ni'),node('span',view.notice));workspace.append(n);
  const board=node('div',undefined,'board');
  view.groups.forEach(g=>{
    const opt=g.options.find(o=>o.id===view.selected[g.id]);
    const card=node('section',undefined,'slot');card.dataset.selected=String(!!opt);
    const who=node('div',undefined,'who');const t=node('div');t.append(node('strong',g.title),node('small','Assigned to '+g.owner));who.append(avatar(g.owner),t);
    const pick=node('p',undefined,'pick');if(opt){pick.append(node('span','Selected: '));pick.append(node('b',opt.title));}else pick.textContent='No selection yet';
    card.append(who,node('p',g.brief,'brief'),cover(opt),pick);
    const a=actionFor(view,'edit:'+g.id);if(a)card.append(button(a.id,'Edit '+g.title));
    board.append(card);
  });workspace.append(board);
  view.actions.filter(a=>a.id.startsWith('import:')).forEach(a=>{
    const t=node('section',undefined,'templ');const st=node('div',undefined,'stack');['#6d7a8c','#b58a64','#8c7b9c'].forEach(c=>{const s=node('span');s.style.background=c;st.append(s);});
    const g=node('div',undefined,'grow');g.append(node('strong','Starter template available'),node('p','A catalog template was generated for this draft. Open its preview to see what it would change.'));
    t.append(st,g,button(a.id,a.label,'light'));workspace.append(t);
  });
  const tail=node('div',undefined,'tail');
  view.actions.filter(a=>!a.id.startsWith('edit:')&&!a.id.startsWith('import:')).forEach(a=>tail.append(button(a.id,a.label,a.id==='review'?'primary':'')));
  if(!view.actions.some(a=>a.id==='review'))tail.append(node('p','Assign each entry and open the incoming draft to enable final review.','muted'));
  workspace.append(tail);window.scrollTo(0,0);
}
fetch('/state').then(r=>r.json()).then(render).catch(()=>workspace.replaceChildren(node('p','The workspace could not be opened. Please reload the page.')));
