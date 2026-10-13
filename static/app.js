const DISCORD='https://discord.gg/hMPGynSq7';
const RC={Common:'#7b8190',Uncommon:'#2fa86b',Rare:'#3b82f6',Legendary:'#a855f7',Mythical:'#ef4444'};
let me=null,cat=null,tab='market',data={market:[],mine:[]},sig='',q='',sel={offer:[],want:[]},mode={offer:'Fruits',want:'Fruits'},chat=null,openRow=null,poller=null;
const $=s=>document.querySelector(s),APP=$('#app');
const e=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const o={credentials:'same-origin',headers:{'Content-Type':'application/json'}};if(body!==undefined){o.method='POST';o.body=JSON.stringify(body)}
  const r=await fetch('/api/'+path,o);let d={};try{d=await r.json()}catch(x){}if(!r.ok)throw new Error(d.error||'Error '+r.status);return d}
const base=f=>f.replace(/ Perm$/,''),fruits=()=>Object.values(cat.rarities).flat();
const rar=f=>Object.keys(cat.rarities).find(k=>cat.rarities[k].includes(base(f)));
const pills=a=>a.map(f=>`<span class="pill" style="background:${RC[rar(f)]||'#d4a017'}">${e(f)}</span>`).join('');
const swap=t=>`<div class="sw"><div class="side"><small>HAS</small><div>${pills(t.offer)}</div></div><div class="arrow">&#8644;</div><div class="side"><small>WANTS</small><div>${pills(t.want)}</div></div></div>`;

/* ---------- login ---------- */
function authScreen(reg){
  stopChat();clearInterval(poller);
  APP.innerHTML=`<div class="panel auth"><h1>Astro<span style="color:var(--ac)">Blox</span></h1><p class="mut">${reg?'Create your account':'Log in to trade'}</p>
  <label>Username</label><input id="u" maxlength="20" autocomplete="username">
  ${reg?'<label>Roblox username (optional, defaults to your username)</label><input id="r" maxlength="20">':''}
  <label>Password${reg?' (8+ characters)':''}</label><input id="p" type="password" maxlength="72" autocomplete="${reg?'new-password':'current-password'}">
  <div class="err" id="er"></div><button class="act" id="go" style="width:100%;margin-top:6px">${reg?'Sign up':'Log in'}</button>
  <p class="mut" style="text-align:center"><a href="#" id="sw" style="color:var(--ac)">${reg?'I already have an account':'Create an account'}</a></p></div>`;
  $('#sw').onclick=ev=>{ev.preventDefault();authScreen(!reg)};
  const submit=async()=>{$('#er').textContent='';try{const d=await api(reg?'register':'login',{username:$('#u').value,password:$('#p').value,roblox:reg?$('#r').value:undefined});me=d.user;shell()}catch(x){$('#er').textContent=x.message}};
  $('#go').onclick=submit;$('#p').onkeydown=ev=>{if(ev.key==='Enter')submit()};$('#u').focus()}

/* ---------- shell ---------- */
function shell(){
  APP.innerHTML=`<nav><span class="logo">Astro<i>Blox</i></span>${[['market','Trades'],['post','Post a trade'],['mine','My trades'],['chat','Chat'],['dm','Messages']].map(([k,l])=>`<button data-t="${k}" class="${k===tab?'on':''}">${l}</button>`).join('')}<a class="dc" href="${DISCORD}" target="_blank" rel="noopener noreferrer">Join Discord</a><span class="who">${e(me.username)}</span><button id="lo">Log out</button></nav>
  <div id="hero" class="hero"><h2>Trade Blox Fruits, no money needed</h2><p>Post what you have and what you want. Others can offer to trade. Then swap in-game.</p></div><main id="view"></main>`;
  APP.querySelectorAll('nav [data-t]').forEach(b=>b.onclick=()=>go(b.dataset.t));
  $('#lo').onclick=async()=>{await api('logout',{});me=null;authScreen(false)};
  clearInterval(poller);poller=setInterval(refresh,5000);refresh(true);
}
function go(t){stopChat();openRow=null;tab=t;document.querySelectorAll('nav [data-t]').forEach(x=>x.classList.toggle('on',x.dataset.t===t));$('#hero').style.display=t==='market'?'':'none';sig='';render()}
async function refresh(force){
  try{const d=await api('trades');const s=JSON.stringify(d);data=d;
    if(force||s!==sig){sig=s;const a=document.activeElement;
      if((tab==='market'||tab==='mine')&&!openRow&&!(a&&a.tagName==='INPUT'&&$('#view').contains(a)))render()}}
  catch(x){if(/log in/i.test(x.message)){me=null;authScreen(false)}}}

/* ---------- chat ---------- */
function stopChat(){if(chat){clearInterval(chat.t);chat=null}}
function startChat(scope,el){stopChat();
  el.innerHTML=`<div class="cm"></div><div class="cin"><input maxlength="300" placeholder="Type a message..."><button class="act">Send</button></div>`;
  const box=el.querySelector('.cm'),inp=el.querySelector('input');let last=0;
  const poll=async()=>{try{const d=await api('messages?scope='+encodeURIComponent(scope)+'&after='+last);
    d.messages.forEach(m=>{const div=document.createElement('div');div.className='m'+(m.mine?' me':'');const b=document.createElement('b');b.textContent=m.name;div.append(b,' '+m.text);box.append(div);last=m.id});
    if(d.messages.length)box.scrollTop=box.scrollHeight}catch(x){}};
  const send=async()=>{const t=inp.value.trim();if(!t)return;inp.value='';try{await api('messages',{scope,text:t});poll()}catch(x){alert(x.message)}};
  el.querySelector('button').onclick=send;inp.onkeydown=ev=>{if(ev.key==='Enter')send()};
  chat={t:setInterval(poll,2500)};poll()}
const dmScope=o=>'dm:'+Math.min(me.id,o)+'_'+Math.max(me.id,o);

/* ---------- views ---------- */
function row(t){
  const own=t.owner===me.id,o=own?{n:t.reqName,r:t.reqRb}:{n:t.ownerName,r:t.ownerRb};let a='';
  if(own&&t.status==='requested')a=`<button class="gh grn" data-do="accept" data-id="${t.id}">Accept</button> <button class="gh" data-do="decline" data-id="${t.id}">Decline</button>`;
  if(!own&&t.status==='requested')a=`<button class="gh" data-do="withdraw" data-id="${t.id}">Withdraw</button>`;
  if(t.status==='agreed')a=`<button class="gh grn" data-do="done" data-id="${t.id}">Trade completed</button>`;
  if(own&&t.status==='open')a=`<button class="gh" data-do="cancel" data-id="${t.id}">Remove</button>`;
  const info=t.status==='requested'?`<div class="mut">${own?`${e(o.n)} (Roblox: ${e(o.r)}) wants this trade.`:'Waiting for the owner to accept.'}</div>`:t.status==='agreed'?`<div class="mut">Agreed! Meet in Blox Fruits and trade with <b>${e(o.r)}</b> using the in-game trade window. Never trade outside the game.</div>`:'';
  const chatBtn=['requested','agreed'].includes(t.status)?` <button class="gh" data-do="tchat" data-id="${t.id}">Chat</button>`:'';
  return `<div class="row"><div style="flex:1;min-width:230px">${swap(t)}<span class="st ${t.status}">${t.status}</span>${info}<div id="c-${t.id}"></div></div><div>${a}${chatBtn}</div></div>`}
function picker(sd){const items=mode[sd]==='Perm'?fruits().map(f=>f+' Perm'):mode[sd]==='Gamepasses'?cat.gamepasses:fruits();
  return `<div class="chips">${['Fruits','Perm','Gamepasses'].map(m=>`<button type="button" class="chip ${mode[sd]===m?'on':''}" data-m="${m}">${m==='Perm'?'Perm fruits':m}</button>`).join('')}</div><div class="pick">${items.map(f=>`<button type="button" class="chip ${sel[sd].includes(f)?'on':''}" data-f="${e(f)}">${e(f)}</button>`).join('')}</div><div class="mut" style="margin-top:6px">Picked: ${pills(sel[sd])||'nothing yet'}</div>${sel[sd].some(f=>/ Perm$/.test(f)||cat.gamepasses.includes(f))?'<div class="tip" style="margin:8px 0 0">Perms and gamepasses are tied to a Roblox account. Never share your password or account to trade them.</div>':''}`}
async function render(){
  const V=$('#view');if(!V)return;
  if(tab==='market'){
    const a=data.market.filter(t=>!q||[...t.offer,...t.want].join(' ').toLowerCase().includes(q));
    V.innerHTML=`<div class="tip">Safety: only trade inside Blox Fruits using Roblox's trade window, never share your password, and record your trades as proof. Got scammed? Tell us in the <a href="${DISCORD}" target="_blank" rel="noopener noreferrer" style="color:var(--ac)">Discord</a>.</div><input id="s" placeholder="Search a fruit you want or have..." value="${e(q)}" style="margin-bottom:14px">`+(a.length?`<div class="grid">${a.map(t=>`<div class="card">${swap(t)}${t.note?`<div class="mut">&ldquo;${e(t.note)}&rdquo;</div>`:''}<div class="mut">by ${e(t.ownerName)} (Roblox: ${e(t.ownerRb)})</div>${t.owner===me.id?`<button class="gh" data-do="cancel" data-id="${t.id}">Remove my trade</button>`:`<button class="act" data-do="request" data-id="${t.id}">Offer this trade</button><button class="gh" data-do="msg" data-id="${t.owner}" data-n="${e(t.ownerName)}">Message ${e(t.ownerName)}</button>`}</div>`).join('')}</div>`:'<div class="empty">No trades yet. Post the first one!</div>');
    $('#s').oninput=ev=>{q=ev.target.value.toLowerCase();const p=ev.target.selectionStart;render();const n=$('#s');n.focus();n.setSelectionRange(p,p)};
  }else if(tab==='post'){
    V.innerHTML=`<div class="panel"><label>I have (pick up to 3)</label><div class="ps" data-ps="offer">${picker('offer')}</div><label>I want (pick up to 3)</label><div class="ps" data-ps="want">${picker('want')}</div><label>Note (optional)</label><input id="nt" maxlength="80" placeholder="e.g. can add small value"><div class="err" id="er"></div><button class="act" id="go" style="width:100%;margin-top:8px">Post trade</button></div>`;
    V.querySelectorAll('.ps').forEach(w=>w.onclick=ev=>{const sd=w.dataset.ps,m=ev.target.closest('[data-m]'),c=ev.target.closest('[data-f]');
      if(m)mode[sd]=m.dataset.m;else if(c){const k=sel[sd].indexOf(c.dataset.f);if(k>=0)sel[sd].splice(k,1);else if(sel[sd].length<3)sel[sd].push(c.dataset.f)}else return;
      const sc=(w.querySelector('.pick')||{}).scrollTop||0;w.innerHTML=picker(sd);const n=w.querySelector('.pick');if(n)n.scrollTop=sc});
    $('#go').onclick=async()=>{try{await api('trades',{offer:sel.offer,want:sel.want,note:$('#nt').value.trim()});sel={offer:[],want:[]};go('market');refresh(true)}catch(x){$('#er').textContent=x.message}};
  }else if(tab==='mine'){
    V.innerHTML=`<div class="tip">Your trades. Use Chat to talk with the other player about a trade.</div>`+(data.mine.map(row).join('')||'<div class="empty">No trades yet.</div>');
  }else if(tab==='chat'){
    V.innerHTML=`<div class="panel" style="max-width:700px"><h3 style="margin-top:0">Global chat</h3><div id="cx"></div><p class="mut">Want voice or more people? Join our <a href="${DISCORD}" target="_blank" rel="noopener noreferrer" style="color:var(--ac)">Discord</a>.</p></div>`;startChat('global',$('#cx'));
  }else{
    let list=[];try{list=(await api('dms')).dms}catch(x){}
    if(tab!=='dm')return;
    V.innerHTML=`<div class="panel" style="max-width:700px"><h3 style="margin-top:0">Messages</h3><p class="mut">Messages are only visible to the two of you, but never share passwords or account details.</p><div>${list.map(c=>`<button class="gh" style="display:block;width:100%;text-align:left;margin-bottom:6px" data-do="dm" data-scope="${e(c.scope)}"><b>${e(c.name)}</b> <span class="mut">${e(c.last)}</span></button>`).join('')||'<div class="mut">No conversations yet. Tap "Message" on a trade to start one.</div>'}</div><div id="c-dm" style="margin-top:10px"></div></div>`;
    if(window._dm){const s=window._dm;window._dm=null;startChat(s,$('#c-dm'))}
  }
}
document.addEventListener('click',async ev=>{
  const b=ev.target.closest('[data-do]');if(!b||!me)return;const id=+b.dataset.id,act=b.dataset.do;
  try{
    if(act==='msg'){window._dm=dmScope(id);go('dm');return}
    if(act==='dm'){startChat(b.dataset.scope,$('#c-dm'));return}
    if(act==='tchat'){const el=$('#c-'+id);if(openRow===id){stopChat();openRow=null;el.innerHTML='';return}document.querySelectorAll('[id^="c-"]').forEach(x=>{if(x.id!=='c-dm')x.innerHTML=''});openRow=id;startChat('trade:'+id,el);return}
    await api(`trades/${id}/${act}`,{});
    if(act==='request'){alert('Sent! The owner will accept or decline. Check "My trades".');go('mine')}
    refresh(true);
  }catch(x){alert(x.message);refresh(true)}
});
(async()=>{try{const d=await api('me');cat=d.catalog;me=d.user;me?shell():authScreen(false)}catch(x){APP.textContent='Could not reach the server.'}})();
