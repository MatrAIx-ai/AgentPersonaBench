"use strict";
const workspace=document.querySelector('#workspace');
let busy=false;
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined&&text!==null)el.textContent=text;if(cls)el.className=cls;return el;}
function button(action,label,kind){const el=node('button',label,kind||'');el.type='button';el.dataset.action=action;el.addEventListener('click',()=>act(action));return el;}
function initials(owner){return owner==='You'?'YO':owner.slice(0,2).toUpperCase();}
function avatar(owner){const a=node('span',initials(owner),'avatar'+(owner==='You'?' me-av':''));a.setAttribute('aria-hidden','true');return a;}
function letter(i){const b=node('span','ABCDEFG'[i]||'·','opt-letter');b.setAttribute('aria-hidden','true');return b;}
async function act(action){
  if(busy)return;busy=true;workspace.querySelectorAll('button').forEach(b=>b.disabled=true);
  const error=document.querySelector('#error');error.hidden=true;
  try{const response=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});const view=await response.json();if(!response.ok)throw new Error(view.error);render(view);}
  catch(e){error.textContent=e.message;error.hidden=false;workspace.querySelectorAll('button').forEach(b=>b.disabled=false);}
  finally{busy=false;}
}
function track(opt){
  const t=node('div',undefined,'track'+(opt?' filled':''));t.setAttribute('aria-hidden','true');
  const bar=node('span',opt?'09:00–17:00':'Unassigned','bar');t.append(bar);return t;
}
function choices(view){
  const section=node('section',undefined,'receipt');
  if(view.submitted)section.id='receipt';
  const dl=node('dl');
  view.groups.forEach(g=>{
    const opt=g.options.find(o=>o.id===view.selected[g.id]);
    const row=node('div',undefined,'rrow');
    const dt=node('dt');dt.append(avatar(g.owner),node('span',g.title+' · Assigned to '+g.owner));row.append(dt);
    const dd=node('dd',opt?opt.title:'No selection','rpick');dd.dataset.slot=g.id;dd.dataset.selectionId=opt?opt.id:'';row.append(dd);
    if(opt)row.append(node('dd',opt.detail,'muted rdetail'));
    dl.append(row);
  });section.append(dl);return section;
}
function setSteps(view){
  const done=Object.values(view.selected).filter(Boolean).length===view.groups.length;
  const state={assign:done?'done':'now',incoming:view.reviewed.length?'done':(view.package?'now':''),
    review:view.submitted?'done':view.stage_id==='review'?'now':'',saved:view.submitted?'done':''};
  document.querySelectorAll('#steps li').forEach(li=>{li.className=state[li.dataset.k]||'';});
}
function render(view){
  document.title=view.app+' · '+view.title;
  document.querySelector('#brand').textContent=view.app;document.querySelector('#subtitle').textContent=view.subtitle;
  document.querySelector('#progress').textContent=view.submitted?'Saved':view.stage_id==='review'?'Review':`${Object.values(view.selected).filter(Boolean).length} / ${view.groups.length} assigned`;
  setSteps(view);
  workspace.replaceChildren();workspace.dataset.stage=view.stage_id;workspace.dataset.submitted=String(view.submitted);workspace.dataset.sessionId=view.session_id;workspace.dataset.revision=view.revision;
  const head=node('div',undefined,'mhead');
  head.append(node('h1',view.submitted?'Assignments saved':view.stage_id==='review'?'Review every assignment':view.title));
  workspace.append(head);
  if(view.submitted){
    const ok=node('div',undefined,'banner ok');ok.append(node('strong','Roster saved'),node('span',view.receipt));workspace.append(ok,choices(view));return;
  }
  const actions=node('div',undefined,'actions');
  if(view.stage_id==='review'){
    workspace.append(node('p','These are the assignments that will be saved. You can return to the draft to change any entry.','lede'),choices(view));
    view.actions.forEach(a=>actions.append(button(a.id,a.label,a.id==='submit'?'primary':'ghost')));
  }else if(view.package){
    const pack=view.package;
    const msg=node('article',undefined,'message');
    const mh=node('div',undefined,'msg-head');
    const who=node('div',undefined,'msg-who');who.append(node('strong','Team coordinator'),node('span','Shared a draft with you','muted'));
    const av=node('span','TC','avatar coord');av.setAttribute('aria-hidden','true');mh.append(av,who);
    msg.append(mh,node('h2',pack.title),node('p',pack.description));workspace.append(msg);
    const list=node('ul',undefined,'diffs');
    view.groups.filter(g=>Object.hasOwn(pack.selections,g.id)).forEach(g=>{
      const opt=g.options.find(o=>o.id===pack.selections[g.id]);const included=view.scope.includes(g.id);
      const cur=g.options.find(o=>o.id===view.selected[g.id]);
      const row=node('li',undefined,'diff');row.dataset.selected=String(included);
      const left=node('div',undefined,'diff-who');left.append(avatar(g.owner),node('strong',g.title+' · '+g.owner));
      const change=node('div',undefined,'diff-change');
      const from=node('span',cur?cur.title:'No selection yet','from');
      const arrow=node('span','→','arrow');arrow.setAttribute('aria-hidden','true');
      change.append(node('span','Now','tag'),from,arrow,node('span','Replace with '+opt.title,'to'));
      const copy=node('div',undefined,'diff-copy');copy.append(left,change,node('p',opt.detail,'muted small'));
      const side=node('div',undefined,'diff-side');
      side.append(node('span',included?'Included':'Excluded','pill '+(included?'on':'off')));
      const a=view.actions.find(a=>a.id==='scope:'+g.id);const b=button(a.id,a.label,'toggle');b.setAttribute('aria-pressed',String(included));side.append(b);
      row.append(copy,side);list.append(row);
    });workspace.append(list);
    view.actions.filter(a=>!a.id.startsWith('scope:')).forEach(a=>actions.append(button(a.id,a.label,a.id==='apply'?'primary':'ghost')));
  }else if(view.active){
    const group=view.groups.find(g=>g.id===view.active);
    const ctx=node('div',undefined,'context');ctx.append(avatar(group.owner));
    const cc=node('div');cc.append(node('p','Editing '+group.title+' · Assigned to '+group.owner,'ctx-t'),node('p',group.brief,'muted'));ctx.append(cc);
    workspace.append(ctx);
    if(view.detail){
      const idx=group.options.findIndex(o=>o.id===view.detail.id);
      const panel=node('section',undefined,'detail');
      const top=node('div',undefined,'detail-top');top.append(letter(idx),node('h2',view.detail.title));
      panel.append(top,node('p',view.detail.summary,'meta'),node('p',view.detail.detail));workspace.append(panel);
      view.actions.forEach(a=>actions.append(button(a.id,a.label,a.id.startsWith('pick:')?'primary':'ghost')));
    }else{
      const list=node('ul',undefined,'tiles');
      group.options.forEach((opt,i)=>{
        const row=node('li',undefined,'tile');const cur=view.selected[group.id]===opt.id;row.dataset.selected=String(cur);
        const top=node('div',undefined,'tile-top');top.append(letter(i));if(cur)top.append(node('span','Current choice','pill on'));
        row.append(top,node('strong',opt.title,'tile-title'),node('span',opt.summary,'meta'));
        const a=view.actions.find(x=>x.id==='open:'+opt.id);row.append(button(a.id,a.label,'ghost'));list.append(row);
      });workspace.append(list);actions.append(button('close','Back to draft','ghost'));
    }
  }else{
    workspace.append(node('p',view.intro,'lede'));
    const note=node('div',undefined,'banner');note.append(node('strong','Notes for this week'),node('span',view.notice));workspace.append(note);
    const table=node('ul',undefined,'roster');
    const hdr=node('li',undefined,'roster-h');hdr.setAttribute('aria-hidden','true');
    ['Entry','Workspace','Hours',''].forEach(t=>hdr.append(node('span',t)));table.append(hdr);
    view.groups.forEach(g=>{
      const opt=g.options.find(o=>o.id===view.selected[g.id]);const row=node('li',undefined,'rrow-b');
      const who=node('div',undefined,'r-who');const wc=node('div');wc.append(node('strong',g.title+' · '+g.owner),node('span',g.brief,'muted small'));who.append(avatar(g.owner),wc);
      const sel=node('div',undefined,'r-sel');sel.append(node('p',opt?'Selected: '+opt.title:'No selection yet',opt?'sel':'sel none'));
      const a=view.actions.find(x=>x.id==='edit:'+g.id);
      row.append(who,sel,track(opt),button(a.id,a.label,'ghost'));table.append(row);
    });workspace.append(table);
    const inbox=view.actions.filter(a=>a.id.startsWith('import:'));
    if(inbox.length){
      const box=node('section',undefined,'inbox');
      const ih=node('div',undefined,'inbox-h');ih.append(node('strong','Inbox'),node('span',view.reviewed.length?'Opened':'1 new','pill '+(view.reviewed.length?'off':'new')));
      box.append(ih);
      inbox.forEach(a=>{const r=node('div',undefined,'inbox-row');const av=node('span','TC','avatar coord');av.setAttribute('aria-hidden','true');
        const c=node('div');c.append(node('strong','Team coordinator'),node('span','A starting draft for this week’s roster','muted small'));
        r.append(av,c,button(a.id,a.label,'ghost'));box.append(r);});
      workspace.append(box);
    }
    view.actions.filter(a=>!a.id.startsWith('edit:')&&!a.id.startsWith('import:')).forEach(a=>actions.append(button(a.id,a.label,a.id==='review'?'primary':'ghost')));
    if(!view.actions.some(a=>a.id==='review'))actions.append(node('p','Assign each entry and open the incoming draft to enable final review.','muted small'));
  }
  workspace.append(actions);window.scrollTo(0,0);
}
fetch('/state').then(r=>r.json()).then(render).catch(()=>workspace.replaceChildren(node('p','The workspace could not be opened. Please reload the page.')));
