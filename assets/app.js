// KeikoArts homepage script (moved out of index.html so the page shows sooner and the browser can cache it).
// The editable data (SERVICES, GALLERY, DETAILS, SLOTS, SEASON, PAYPAL, VTUBERS) stays in index.html and runs first.
// After editing this file run: python3 tools/build_pages.py (updates ?v= in index.html so browsers load the new version).

const $=q=>document.querySelector(q), $$=q=>[...document.querySelectorAll(q)];
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>'$'+(Math.round(n*100)/100).toLocaleString('en-US',{minimumFractionDigits:n%1?2:0,maximumFractionDigits:2});
document.getElementById('yr').textContent=new Date().getFullYear();




// reference attachments: each file starts uploading in small pieces as soon as it is added
const REF_MAX_FILES=8, REF_MAX_BYTES=60*1024*1024, REF_MAX_FILE=40*1024*1024, CHUNK=2*1024*1024;
let refFiles=[]; const upState=new Map();
const hex=n=>{const a=new Uint8Array(n/2);crypto.getRandomValues(a);return [...a].map(x=>x.toString(16).padStart(2,'0')).join('');};
let upToken=hex(32), pumping=false;
const CAN_UPLOAD=()=>/(^|\.)keikoartist\.com$/i.test(location.hostname)||/^(localhost|127\.0\.0\.1)$/.test(location.hostname);
function upBadge(f){const s=upState.get(f);if(!s||!CAN_UPLOAD())return '';
  if(s.status==='done')return '✓';if(s.status==='fail')return '!';if(s.status==='queued')return '…';
  return Math.min(99,Math.floor((s.sent||0)/Math.max(1,f.size)*100))+'%';}
function refProgress(f){const i=refFiles.indexOf(f),li=$('#refList').children[i];if(!li)return;const b=li.querySelector('.up');if(b){b.textContent=upBadge(f);b.className='up '+((upState.get(f)||{}).status||'');}refInfo();}
function refInfo(){
  const tot=refFiles.reduce((a,f)=>a+f.size,0);
  let info=$('#refInfo');if(!info){info=document.createElement('p');info.id='refInfo';info.className='ref-size';$('#refList').after(info);}
  const busy=refFiles.some(f=>{const s=upState.get(f);return s&&(s.status==='queued'||s.status==='up');}), bad=refFiles.filter(f=>(upState.get(f)||{}).status==='fail');
  info.textContent=refFiles.length?`${refFiles.length} file(s) · ${(tot/1048576).toFixed(1)} MB of 60 MB`+(CAN_UPLOAD()?(busy?' · uploading…':bad.length?` · ${bad.length} failed`:' · uploaded ✓'):''):'';
}
function renderRefs(){
  const ul=$('#refList');ul.innerHTML='';
  refFiles.forEach((f,i)=>{const li=document.createElement('li'),s=upState.get(f)||{};
    if(/^image\/(png|jpe?g|webp|gif|avif|bmp)$/i.test(f.type)&&(s.url||f instanceof Blob)){const im=document.createElement('img');im.src=s.url||(s.url=URL.createObjectURL(f));im.alt=f.name;li.appendChild(im);}else li.textContent=f.name;
    const x=document.createElement('button');x.type='button';x.textContent='✕';x.setAttribute('aria-label','Remove '+f.name);
    x.onclick=()=>{const st=upState.get(f);if(st&&st.url&&st.url.startsWith('blob:'))URL.revokeObjectURL(st.url);if(st&&st.status!=='queued'&&CAN_UPLOAD()){const fd=new FormData();fd.append('token',upToken);fd.append('fid',st.fid);xhr('order-api.php?a=unupload',fd,null,20000);}upState.delete(f);refFiles.splice(refFiles.indexOf(f),1);renderRefs();saveDraft();};li.appendChild(x);
    if(CAN_UPLOAD()){const b=document.createElement('span');b.className='up '+(s.status||'');b.textContent=upBadge(f);if(s.err)b.title=s.err;li.appendChild(b);}
    ul.appendChild(li);});
  refInfo();
}
function xhr(url,fd,onProgress,timeout){
  return new Promise(res=>{
    try{
      const x=new XMLHttpRequest();x.open('POST',url);x.timeout=timeout||300000;
      if(x.upload&&onProgress)x.upload.onprogress=e=>{if(e.lengthComputable)onProgress(e.loaded/e.total);};
      x.onload=()=>{let j=null;try{j=JSON.parse(String(x.responseText||'').replace(/^﻿/,'').trim());}catch(_){}res({status:x.status,j});};
      x.onerror=()=>res({status:0,j:null});x.ontimeout=()=>res({status:-1,j:null});
      x.send(fd);
    }catch(_){res({status:0,j:null});}
  });
}
async function uploadFile(f,s){
  if(!f.size){s.err='Empty file';return false;}
  let off=0, fails=0;
  while(off<f.size){
    if(upState.get(f)!==s)return false;          // removed by the client
    const blob=f.slice(off,Math.min(f.size,off+CHUNK)), fd=new FormData(), base=off;
    fd.append('token',upToken);fd.append('fid',s.fid);fd.append('name',f.name||'reference.jpg');fd.append('size',String(f.size));fd.append('offset',String(off));fd.append('chunk',blob,'chunk');
    const r=await xhr('order-api.php?a=upload',fd,p=>{s.sent=base+blob.size*p;refProgress(f);},120000);
    if(r.status===200&&r.j&&r.j.ok){off=+r.j.received||off+blob.size;s.sent=off;fails=0;refProgress(f);continue;}
    if(r.status===409&&r.j&&r.j.received!=null){off=+r.j.received;continue;}
    if(r.status===400&&r.j&&r.j.error){s.err=r.j.error;refMsg(`${f.name}: ${r.j.error}`);return false;}
    if(++fails>6){s.err='Upload failed (connection)';return false;}
    await new Promise(z=>setTimeout(z,Math.min(10000,1200*fails)));
  }
  return true;
}
async function pump(){
  if(pumping||!CAN_UPLOAD()||!location.protocol.startsWith('http'))return;pumping=true;
  try{for(;;){const f=refFiles.find(x=>(upState.get(x)||{}).status==='queued');if(!f)break;
    const s=upState.get(f);s.status='up';refProgress(f);
    const ok=await uploadFile(f,s);if(upState.get(f)===s){s.status=ok?'done':'fail';refProgress(f);if(ok){s.thumb=await makeThumb(f);saveDraft();}if(!ok){const li=$('#refList').children[refFiles.indexOf(f)];const b=li&&li.querySelector('.up');if(b&&s.err)b.title=s.err;}}}}
  finally{pumping=false;}
}
function refMsg(t,ok){const m=$('#refMsg');m.textContent=t||'';m.classList.toggle('show',!!t);m.classList.toggle('ok',!!ok);}
async function makeThumb(f){
  try{if(!(f instanceof Blob)||!/^image\/(png|jpe?g|webp|gif|bmp)$/i.test(f.type))return '';
    const bmp=await createImageBitmap(f),k=96/Math.max(bmp.width,bmp.height),c=document.createElement('canvas');
    c.width=Math.max(1,Math.round(bmp.width*k));c.height=Math.max(1,Math.round(bmp.height*k));c.getContext('2d').drawImage(bmp,0,0,c.width,c.height);
    return c.toDataURL('image/jpeg',.6);}catch(_){return '';}
}
const uploadsBusy=()=>refFiles.some(f=>{const s=upState.get(f);return s&&(s.status==='queued'||s.status==='up');});
async function shrink(f){
  // compress big images so they fit the 10 MB email limit
  if(!f.type.startsWith('image/')||f.type==='image/gif'||f.size<1.5*1024*1024)return f;
  try{
    const bmp=await createImageBitmap(f);const k=Math.min(1,2400/Math.max(bmp.width,bmp.height));
    const c=document.createElement('canvas');c.width=Math.round(bmp.width*k);c.height=Math.round(bmp.height*k);
    const x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(bmp,0,0,c.width,c.height);
    const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',.85));if(!blob||blob.size>=f.size)return f;
    return new File([blob],f.name.replace(/\.\w+$/,'')+'.jpg',{type:'image/jpeg'});
  }catch(_){return f;}
}
async function addRefs(list){
  refMsg('');const skipped=[];
  if(list.length)refMsg('Adding '+list.length+' file(s)…',true);
  for(const raw of list){
    if(refFiles.length>=REF_MAX_FILES){skipped.push(raw.name+' (max '+REF_MAX_FILES+' files)');continue;}
    const f=await shrink(raw);
    if(f.size>REF_MAX_FILE){skipped.push(`${raw.name} (${(f.size/1048576).toFixed(1)} MB, max 40 MB per file)`);continue;}
    const used=refFiles.reduce((a,x)=>a+x.size,0);
    if(used+f.size>REF_MAX_BYTES){skipped.push(`${raw.name} (over 60 MB in total)`);continue;}
    refFiles.push(f);upState.set(f,{fid:hex(16),status:'queued',sent:0});
  }
  renderRefs();pump();
  refMsg(skipped.length?'Not added: '+skipped.join(', ')+'. Please paste a Drive/Pinterest link for these instead.':'');
}
$('#refFiles').addEventListener('change',e=>{err('');addRefs([...e.target.files]);e.target.value='';});
const drop=$('#refDrop');
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over');}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('over');}));
drop.addEventListener('drop',e=>{err('');addRefs([...e.dataTransfer.files]);});
drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('#refFiles').click();}});
function attachRefsToForm(){
  const slots=$('#refSlots');slots.innerHTML='';
  refFiles.forEach((f,i)=>{const inp=document.createElement('input');inp.type='file';inp.name='attachment'+(i+1);
    const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;slots.appendChild(inp);});
}

// ===== order modal: service list (step 1) + one order page per service (step 2) =====
const modal=$('#orderModal'), form=$('#orderForm'); let step=1, svc=null, svcName='', cmOn=false, sheetStart=0;
let ORDER={lines:[],total:0,due:0,plan:'Full payment',custom:false};
// ===== cart: several services, one order and one invoice (kept on this device for 30 days) =====
const CART_KEY='ka_cart', CART_MAX=6, CART_SVC={packages:[['Cart',0,'']],addons:[],eta:'3 weeks at most',from:0};
let CART_MODE=false, EDIT_ID=null;
function readCart(){try{const c=JSON.parse(localStorage.getItem(CART_KEY)||'[]');return Array.isArray(c)?c.filter(x=>x&&SERVICES[x.svc]&&Array.isArray(x.lines)&&Date.now()-(x.t||0)<30*864e5).slice(0,CART_MAX):[];}catch(_){return [];}}
function writeCart(c){try{c.length?localStorage.setItem(CART_KEY,JSON.stringify(c)):localStorage.removeItem(CART_KEY);}catch(_){}cartUI();}
const SAVED_KEY='ka_saved';
function readSaved(){try{const c=JSON.parse(localStorage.getItem(SAVED_KEY)||'[]');return Array.isArray(c)?c.filter(x=>x&&SERVICES[x.svc]&&Array.isArray(x.lines)).slice(0,12):[];}catch(_){return [];}}
function writeSaved(c){try{c.length?localStorage.setItem(SAVED_KEY,JSON.stringify(c)):localStorage.removeItem(SAVED_KEY);}catch(_){}}
function cartSum(c){const sub=r2(c.reduce((a,x)=>a+(+x.sub||0),0)),tax=r2(sub*TAX);return {sub,tax,total:r2(sub+tax)};}
function cartUI(){
  const c=readCart(),n=c.length,sm=cartSum(c);
  $('#navCartN').hidden=!n;$('#navCartN').textContent=n;$('#navCart').setAttribute('aria-label',`Your cart, ${n} item${n===1?'':'s'}`);
  $('#cartMini').hidden=!n;$('#cmN').textContent=n+' service'+(n===1?'':'s');$('#cmT').textContent=money2(sm.total);
  if(step===3)renderCart();
}
function renderCart(){
  const c=readCart(),sm=cartSum(c);
  $('#cartEmpty').hidden=!!c.length;$('#cartFoot').hidden=!c.length;$('#cartSave').hidden=!c.length;$('#cartCheckout').hidden=!c.length;$('#cartClear').hidden=!c.length;$('#cartClear').classList.remove('sure');$('#cartClear span').textContent='Clear cart';
  $('#cartList').innerHTML=c.map(x=>{const opts=x.lines.map(l=>l[0].replace(/^\+ /,'')).join(' · ').replace(x.svc+' · ','');
    return `<li class="ci"><span class="ci-th" style="background-image:url('${svcThumb(x.svc)}')"></span><div class="ci-t"><b>${esc(x.svc)}</b><small>${esc(opts)}</small>${x.details?`<em>“${esc(x.details)}”</em>`:''}<button type="button" class="ci-save" data-sv="${esc(x.id)}">Save for later</button></div><b class="ci-p">${money2(x.sub)}</b><div class="ci-a"><button type="button" class="ci-x ci-ed" data-ed="${esc(x.id)}" aria-label="Edit ${esc(x.svc)}" title="Edit"><svg class="ic" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17v3Z"/><path d="m14.5 7.5 3 3"/></svg></button><button type="button" class="ci-x" data-rm="${esc(x.id)}" aria-label="Remove ${esc(x.svc)}" title="Remove">✕</button></div></li>`;}).join('');
  const sv=readSaved();$('#savedBox').hidden=!sv.length;
  $('#savedList').innerHTML=sv.map(x=>`<li class="ci"><span class="ci-th" style="background-image:url('${svcThumb(x.svc)}')"></span><div class="ci-t"><b>${esc(x.svc)}</b><small>${esc(x.lines.map(l=>l[0].replace(/^\+ /,'')).join(' · ').replace(x.svc+' · ',''))}</small><button type="button" class="ci-save" data-mv="${esc(x.id)}">Move to cart</button></div><b class="ci-p">${money2(x.sub)}</b><div class="ci-a"><button type="button" class="ci-x" data-srm="${esc(x.id)}" aria-label="Remove ${esc(x.svc)}" title="Remove">✕</button></div></li>`).join('');
  fxLine(sm.total,$('#cartFx'));
  $('#cartTot').innerHTML=`<dt>Subtotal</dt><dd>${money2(sm.sub)}</dd><dt>PayPal fee (13%)</dt><dd>${money2(sm.tax)}</dd><dt class="grand">Total (USD)</dt><dd class="grand">${money2(sm.total)}</dd>`;
}
function addToCart(){
  if(!svc||cmOn||CART_MODE)return;
  calc();
  const c=readCart(),ei=EDIT_ID?c.findIndex(x=>x.id===EDIT_ID):-1;if(ei<0&&c.length>=CART_MAX){err(`Your cart is full (${CART_MAX} services). Please check out first.`);return;}
  const ls=ORDER.lines.filter(l=>!/^(Tax|PayPal fee) \(13%\)/.test(l[0])).map((l,i)=>[i?'+ '+l[0]:l[0],l[1]]);
  const sel=[...$$('#sheet input[type=radio]:checked'),...$$('#sheet input[type=checkbox]:checked')].map(x=>x.id).filter(id=>id&&id!=='agree'&&!/^pp\d/.test(id)),aq={};$$('#addOpts .add-q').forEach(x=>aq[x.id]=x.value);
  const item={id:ei>=0?EDIT_ID:Date.now().toString(36)+Math.random().toString(36).slice(2,5),t:Date.now(),sel,aq,svc:svcName,pkg:$('#fPackage').value,qty:+$('#fQty').value||1,addons:$('#fAddons').value,lines:ls,sub:r2(ls.reduce((a,l)=>a+l[1],0)),details:$('#fDetails').value.split('\n').filter(l=>!/^\s*[^:\n]{1,60}:\s*$/.test(l)).join('\n').replace(/\n{3,}/g,'\n\n').trim().slice(0,1500)};
  if(ei>=0)c[ei]=item;else c.push(item);EDIT_ID=null;
  writeCart(c);
  $('#fDetails').value='';clearDraft();go(3);
}
function openCart(){openOrder();go(3);}
function editCartItem(id){
  const x=readCart().find(y=>y.id===id);if(!x)return;
  pickService(x.svc);
  (x.sel||[]).forEach(i=>{const el=document.getElementById(i);if(el&&!el.disabled)el.checked=true;});
  Object.entries(x.aq||{}).forEach(([i,v])=>{const el=document.getElementById(i);if(el)el.value=v;});
  if(x.qty&&svc.qty)$('#qty').value=x.qty;
  $('#fDetails').value=x.details||'';$('#draftNote').hidden=true;
  const r=$$('input[name=svc]').find(y=>y.value===x.svc);if(r)r.checked=true;
  EDIT_ID=id;go(2);calc();
}
function openCheckout(){
  const c=readCart();if(!c.length){go(3);return;}
  CART_MODE=true;svc=CART_SVC;svcName='Cart';cmOn=false;
  $('#shName').textContent='Your cart';$('#shMeta').textContent=`${c.length} service${c.length>1?'s':''} · + 13% PayPal fee · 3 weeks at most`;
  $('#shThumb').style.backgroundImage=`url("${svcThumb(c[0].svc)}")`;
  $('#shIntro').textContent='One order and one invoice for everything in your cart ♡';
  $('#secPkg').hidden=true;$('#secAdd').hidden=true;$('#secBudget').hidden=true;$('#useBox').hidden=true;$('#secPay').hidden=false;
  $$('input[name=Usage]').forEach(x=>x.disabled=true);$('#budget').required=false;$('#budget').value='';$('#rush').checked=false;
  if(!$('#fDetails').value.trim())$('#fDetails').value=c.filter(x=>x.details).map(x=>`[${x.svc}] ${x.details}`).join('\n\n');
  $('#fDetails').placeholder='Tell me about your character and anything I should know for each service ♡';
  $('#draftNote').hidden=true;go(2);
}
$('#svcOpts').innerHTML=Object.entries(SERVICES).map(([k,v],i)=>`<div class="opt"><input type="radio" name="svc" id="s${i}" value="${k}"><label for="s${i}">${k}<small>${v.quote?'Name your price':'From '+money(v.from)}</small></label></div>`).join('');
function openOrder(service){
  try{if(!sessionStorage.getItem('ka_oo')){sessionStorage.setItem('ka_oo','1');KA_STAT('order_open');}}catch(_){KA_STAT('order_open');}   // once per visit
  modal.classList.add('show'); modal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden';
  if(service&&SERVICES[service]){const r=$$('input[name=svc]').find(x=>x.value===service); r.checked=true; pickService(service); go(2);} else go(1);
}
function closeOrder(){modal.classList.remove('show');modal.setAttribute('aria-hidden','true');document.body.style.overflow='';try{sessionStorage.removeItem('ka_open');sessionStorage.removeItem('ka_open_y');}catch(_){}}
{let yT=0;modal.addEventListener('scroll',()=>{clearTimeout(yT);yT=setTimeout(()=>{try{if(modal.classList.contains('show'))sessionStorage.setItem('ka_open_y',String(Math.round(modal.scrollTop)));}catch(_){}},200);},{passive:true});}
document.addEventListener('click',e=>{
  const o=e.target.closest('[data-order]'); if(o){e.preventDefault(); openOrder(o.dataset.order);}
  if(e.target===modal||e.target.closest('[data-close]')) closeOrder();
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeOrder()});

const DETAILS_PH={
  "VTuber":"Tell me about your character: personality, colors, outfit, and must-have details ♡",
  "VTuber Packages":"Tell me about your character and your debut plans: personality, colors, theme ♡",
  "Background":"Describe the scene: place, mood, time of day, colors ♡",
  "Stream Overlay":"Your stream theme, colors, and the text you want on each screen ♡",
  "Custom PFP":"Who is in it, pose or expression, colors, and the vibe you want ♡",
  "Banner":"Your character, colors, and where you'll use the banner ♡",
  "VTuber Logo":"The name or text for your logo, style, colors, and any icon idea ♡",
  "PNGTuber":"Your character and the expressions you want ♡",
  "Emotes":"Which emotes? e.g. love, cry, hype, sleepy. Plus your character references ♡",
  "VTuber Pet":"What kind of pet, colors, personality, and accessories ♡",
  "Chibi VTuber":"Your character, outfit, and the expressions you want ♡",
};
const svcThumb=k=>{const g=(typeof GALLERY!=='undefined'&&GALLERY[k])||[];return g.length?`images/${g[0]}.webp`:'images/keikoarts-logo.webp';};
const sizeName=c=>c==='Half'?'Half body':c==='Full'?'Full body':c;

// real savings of the debut packages vs buying the same things one by one (cheapest single items; expressions not counted, so it never overstates)
// Christmas wheel code: "10% off" codes take the discount off the total (the server checks and recomputes it)
let COUPON=null;
function withCoupon(o){
  if(!COUPON||!COUPON.percent||o.custom||!(o.total>0))return o;
  const fi=o.lines.findIndex(l=>/^PayPal fee/.test(l[0]));if(fi<0)return o;
  const sub=r2(o.lines.reduce((a,l,i)=>i===fi?a:a+l[1],0)),disc=r2(sub*COUPON.percent/100),fee=r2((sub-disc)*TAX),total=r2(sub-disc+fee);
  const lines=o.lines.slice();lines.splice(fi,0,[`Christmas code ${COUPON.code} (${COUPON.percent}% off)`,-disc]);lines[fi+1]=[lines[fi+1][0],fee];
  return Object.assign({},o,{lines,total,due:dueNow(total,o.plan)});
}
function pkgSaving(i){
  const g=(k,n)=>{const s=SERVICES[k];if(!s)return NaN;const p=s.packages.find(x=>x[0]===n);return p?p[1]:NaN;};
  const parts=[[g('VTuber','Bust · Art + Rig')],
    [g('VTuber','Half body · Art + Rig'),6*g('Emotes','Static emote'),g('Background','Static'),g('Stream Overlay','Screens set')],
    [g('VTuber','Full body · Art + Rig'),6*g('Emotes','Static emote'),g('Background','Static'),g('Stream Overlay','Screens set'),g('Custom PFP','Headshot'),g('VTuber Logo','Custom logo')]][i];
  const pk=(SERVICES['VTuber Packages']||{packages:[]}).packages[i];if(!parts||!pk)return 0;
  const sep=parts.reduce((a,b)=>a+b,0);return isFinite(sep)&&sep>pk[1]?Math.round(sep-pk[1]):0;
}
function pickService(k){
  CART_MODE=false;EDIT_ID=null;svc=SERVICES[k]; svcName=k; cmOn=!!svc.quote;
  $('#shName').textContent=k;
  {const st=slotTxt(k);$('#shMeta').textContent=(cmOn?'You name the price · 13% PayPal fee added':`From ${money(svc.from)} + 13% PayPal fee · done within 3 weeks`)+(st?' · '+st:'');}
  $('#shThumb').style.backgroundImage=`url("${svcThumb(k)}")`;
  $('#shIntro').textContent=cmOn?'Tell me your idea and name your price ♡':/VTuber|PNGTuber|Chibi|Pet/.test(k)?'Choose your options and tell me your idea ♡ No design yet? Describe your character and I design it with you.':'Choose your options and tell me your idea ♡';
  {const inc=(typeof DETAILS!=='undefined'&&DETAILS[k]&&DETAILS[k].includes)||[];$('#wygList').innerHTML=inc.map(x=>`<li>${esc(x)}</li>`).join('');$('#wyg').hidden=!inc.length;$('#wyg').open=false;}
  const mx=!!svc.table; $('#mx').hidden=!mx; $('#pkgOpts').hidden=mx;
  $('#pkgOpts').innerHTML=svc.packages.map(([n,p,d],i)=>{const sv=k==='VTuber Packages'?pkgSaving(i):0;d=sv?d+' · Save $'+sv+' vs buying separately':d;return `<div class="opt"><input type="radio" name="pkg" id="p${i}" value="${i}" ${i===0?'checked':''}><label for="p${i}">${esc(n)} <em>${cmOn?'':money(p)+(svc.qty?' each':'')}</em><small>${esc(d)}</small></label></div>`;}).join('');
  if(mx){
    const mt0=Math.max(0,svc.table.rows.findIndex(([r])=>r==='Art + Rig'));   // most VTubers want a moving model (owner, Nov 2026)
    $('#mxType').innerHTML=svc.table.rows.map(([r,ix],i)=>`<input type="radio" name="mxType" id="mt${i}" value="${i}" ${i===mt0?'checked':''}><label for="mt${i}">${esc(r)}<small>from ${money(Math.min(...ix.map(j=>svc.packages[j][1])))}</small></label>`).join('');
    $('#mxSize').innerHTML=svc.table.cols.map((c,i)=>`<input type="radio" name="mxSize" id="ms${i}" value="${i}" ${i===0?'checked':''}><label for="ms${i}">${esc(sizeName(c))}<small></small></label>`).join('');
  }else{$('#mxType').innerHTML='';$('#mxSize').innerHTML='';}
  $('#addOpts').innerHTML=svc.addons.map(([n,p],i)=>{const each=/toggle/i.test(n);return `<span class="add-w"><input type="checkbox" name="add" id="a${i}" value="${i}"><label for="a${i}">${esc(n)} <em>${p?'+'+money(p)+(each?' each':''):'Free'}</em>${/commercial/i.test(n)?'<small class="add-note">Streaming and monetized videos are always included; this is for merch</small>':''}</label>${each?`<input type="number" class="add-q" id="aq${i}" min="1" max="20" value="1" inputmode="numeric" aria-label="How many ${esc(n).toLowerCase()}s">`:''}</span>`;}).join('');
  $('#qtyWrap').hidden=!svc.qty; $('#qty').value=1;
  $('#secPkg').hidden=cmOn; $('#secAdd').hidden=cmOn; $('#secPay').hidden=cmOn; $('#secBudget').hidden=!cmOn; $('#useBox').hidden=!cmOn;
  $$('input[name=Usage]').forEach(x=>x.disabled=!cmOn);
  $('#budget').required=cmOn; $('#budget').value=''; $('#rush').checked=false; $('#pp1').checked=true;
  $('#fDetails').placeholder=cmOn?"What would you like? Character(s), pose, mood, colors, where you'll use it…":(DETAILS_PH[k]||"Tell me your idea: character, colors, vibe, and anything I should know ♡");
  {const msg=restoreDraft(k);$('#draftNote').hidden=!msg;if(msg)$('#draftNote span').textContent=msg;}
  calc();
}
['click','change'].forEach(ev=>$('#svcOpts').addEventListener(ev,e=>{if(e.target.name==='svc'&&e.target.checked){if(step===2&&svcName===e.target.value)return;pickService(e.target.value);go(2);}}));
$('#shChange').onclick=()=>go(1);
$('#qtyMinus').onclick=()=>{$('#qty').value=Math.max(1,(parseInt($('#qty').value,10)||1)-1);calc();};
$('#qtyPlus').onclick=()=>{$('#qty').value=Math.min(50,(parseInt($('#qty').value,10)||1)+1);calc();};
form.addEventListener('input',()=>{if(svc)calc();if(step===2)err('');});
form.addEventListener('change',()=>{if(svc)calc();});

// ===== draft autosave (so a slow or interrupted client doesn't lose what they typed) =====
if(matchMedia('(hover:none)').matches){const dh=document.getElementById('dropHint');if(dh)dh.textContent='Tap to choose images · up to 8 files, 60 MB total';}
const DRAFT_KEY='ka_draft', DRAFT_IDS=['fDetails','fName','fEmail','fDiscord','fDeadline','budget'];
let draftTimer=0;
function saveDraft(){
  if(step!==2||!svc||CART_MODE)return;
  try{const old=readDraft(),d={t:Date.now(),start:(old&&old.start)||sheetStart||Date.now(),svc:svcName,v:{},sel:[],qty:$('#qty').value,links:form['Reference links'].value};
    const done=refFiles.filter(f=>(upState.get(f)||{}).status==='done');
    d.up={token:upToken,at:Date.now(),total:refFiles.length,files:done.map(f=>{const st=upState.get(f);return {fid:st.fid,name:f.name,size:f.size,type:f.type,thumb:st.thumb||''};})};
    DRAFT_IDS.forEach(id=>d.v[id]=$('#'+id).value);
    d.sel=[...$$('#sheet input[type=radio]:checked'),...$$('#sheet input[type=checkbox]:checked')].map(x=>x.id).filter(id=>id&&id!=='agree');
    if(Object.values(d.v).some(Boolean)||d.links||d.up.total)localStorage.setItem(DRAFT_KEY,JSON.stringify(d));}catch(_){}
}
function readDraft(){try{const d=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null');return d&&Date.now()-d.t<3*864e5&&SERVICES[d.svc]?d:null;}catch(_){return null;}}
function clearDraft(){try{localStorage.removeItem(DRAFT_KEY);}catch(_){}}
function restoreDraft(k){
  const d=readDraft();if(!d||d.svc!==k)return false;
  DRAFT_IDS.forEach(id=>{if(d.v[id])$('#'+id).value=d.v[id];});
  if(d.links)form['Reference links'].value=d.links;
  (d.sel||[]).forEach(id=>{const el=document.getElementById(id);if(el&&!el.disabled)el.checked=true;});
  if(d.qty)$('#qty').value=d.qty;
  if(d.start&&(!sheetStart||d.start<sheetStart))sheetStart=d.start;
  let kept=0;const lost=d.up?Math.max(0,(d.up.total||0)-(d.up.files||[]).length):0;
  if(d.up&&(d.up.files||[]).length&&!refFiles.length&&Date.now()-d.up.at<20*3600e3&&CAN_UPLOAD()){   // uploaded references stay on the server for a day
    upToken=d.up.token;
    d.up.files.forEach(x=>{const f={name:x.name,size:x.size,type:x.type,restored:true};refFiles.push(f);upState.set(f,{fid:x.fid,status:'done',sent:x.size,url:x.thumb||'',thumb:x.thumb||''});kept++;});
    renderRefs();}
  if(!(d.v.fDetails||d.v.fName||d.links||kept))return '';
  return kept&&!lost?'✓ Your details and reference images were restored.'
    :lost?`✓ Your details were restored. Please re-attach ${lost} reference image(s) that hadn't finished uploading.`
    :'✓ Your details were restored.';
}
form.addEventListener('input',()=>{clearTimeout(draftTimer);draftTimer=setTimeout(saveDraft,400);});
form.addEventListener('change',()=>{clearTimeout(draftTimer);draftTimer=setTimeout(saveDraft,400);});
$('#draftClear').onclick=()=>{clearDraft();['fDetails','fDeadline','budget'].forEach(id=>$('#'+id).value='');form['Reference links'].value='';$('#draftNote').hidden=true;pickService(svcName);};
addEventListener('pagehide',saveDraft);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')saveDraft();});

function budget(){if(!svc||!svc.quote)return 0;const v=parseFloat($('#budget').value);return v>=5&&v<=10000?Math.round(v*100)/100:0;}
const radioVal=n=>+(($(`input[name="${n}"]:checked`)||{}).value||0);
function selIndex(){return svc.table?svc.table.rows[radioVal('mxType')][1][radioVal('mxSize')]:radioVal('pkg');}
function calc(){
  if(!svc)return 0;
  if(CART_MODE){
    const c=readCart(),sm=cartSum(c),p3=$('#pp3');p3.disabled=sm.sub<150;if(p3.disabled&&p3.checked)$('#pp1').checked=true;
    const plan=$('input[name="Payment plan"]:checked').value,due=dueNow(sm.total,plan);
    $('#fService').value=c.map(x=>x.svc).join(' + ');$('#fPackage').value=c.map(x=>x.pkg+(x.qty>1?' × '+x.qty:'')).join('; ');$('#fQty').value=c.length;
    $('#fAddons').value=c.map(x=>x.addons&&x.addons!=='-'?x.svc+': '+x.addons:'').filter(Boolean).join('; ')||'-';
    $('#fTotal').value=money2(sm.total)+' (incl. 13% PayPal fee)';$('#fSubject').value=`New cart order: ${$('#fService').value} — ${money2(sm.total)}`;
    ORDER=withCoupon({lines:[...c.flatMap(x=>x.lines),['PayPal fee (13%)',sm.tax]],total:sm.total,due,plan,custom:false,rush:false});
    renderInv();return ORDER.total;
  }
  if(cmOn){
    const iv=invoice(), bud=iv.sub;
    $('#fService').value=svcName;$('#fPackage').value=svc.packages[0][0];$('#fQty').value=1;$('#fAddons').value='-';
    $('#fTotal').value=bud?`${money2(iv.total)} (client's price ${money2(bud)}${iv.com?' + commercial rights '+money2(iv.com):''} + 13% PayPal fee ${money2(iv.tax)})`:'-';
    $('#fSubject').value=`New custom order — ${bud?money2(iv.total)+' incl. PayPal fee':'no price'}`;
    ORDER={lines:[[`Custom commission (${usageVal()} use)`,bud],...(iv.com?[['Commercial / merch rights',iv.com]]:[]),['PayPal fee (13%)',iv.tax]],total:iv.total,due:iv.total,plan:'Full payment',custom:true};
    renderInv();return bud;
  }
  const pk=svc.packages[selIndex()], qty=svc.qty?Math.min(50,Math.max(1,parseInt($('#qty').value,10)||1)):1;
  const adds=$$('input[name=add]:checked').map(x=>{const a=svc.addons[+x.value],qi=$('#aq'+x.value),q=qi?Math.min(20,Math.max(1,parseInt(qi.value,10)||1)):1;return [q>1?a[0]+' × '+q:a[0],r2(a[1]*q)];});
  const base=r2(pk[1]*qty), sub=r2(base+adds.reduce((a,x)=>a+x[1],0)), rush=$('#rush').checked, rushAmt=rush?r2(sub*.25):0, pre=r2(sub+rushAmt), taxAmt=r2(pre*TAX), t=r2(pre+taxAmt);
  if(svc.table){const r=radioVal('mxType');
    $$('#mxSize label').forEach((l,i)=>{const sm=l.querySelector('small');if(sm)sm.textContent=money(svc.packages[svc.table.rows[r][1][i]][1]);});
    $('#mxPick').innerHTML=`You picked <b>${esc(pk[0])}</b> · ${money(pk[1])} · ${esc(pk[2])}`;}
  const p3=$('#pp3'); p3.disabled=pre<150; if(p3.disabled&&p3.checked)$('#pp1').checked=true;
  const plan=$('input[name="Payment plan"]:checked').value, due=dueNow(t,plan);
  $('#fService').value=svcName;$('#fPackage').value=pk[0];$('#fQty').value=qty;
  $('#fAddons').value=[...adds.map(a=>a[0]),rush?'Rush delivery (+25%)':''].filter(Boolean).join(', ')||'-';
  $('#fTotal').value=money2(t)+' (incl. 13% PayPal fee)';$('#fSubject').value=`New request: ${svcName} (${pk[0]}${svc.qty?' × '+qty:''}) — ${money2(t)}`;
  ORDER=withCoupon({lines:[[`${svcName} · ${pk[0]}${svc.qty?' × '+qty:''}`,base],...adds.map(a=>[a[0],a[1]]),...(rush?[['Rush delivery (+25%)',rushAmt]]:[]),['PayPal fee (13%)',taxAmt]],total:t,due,plan,custom:false,rush});
  renderInv();return ORDER.total;
}
const readyBy=rush=>new Date(Date.now()+(rush?11:21)*864e5).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});   // every commission: 3 weeks at most
// approximate price in the visitor's own currency (rates fetched and cached by fx-api.php; the invoice is always in USD)
const FX_CUR=(()=>{const r=((navigator.language||'').split('-')[1]||'').toUpperCase(),EU='AT BE CY DE EE ES FI FR GR HR IE IT LT LU LV MT NL PT SI SK'.split(' ');
  const m={ID:'IDR',GB:'GBP',JP:'JPY',PH:'PHP',MY:'MYR',SG:'SGD',AU:'AUD',CA:'CAD',BR:'BRL',MX:'MXN',KR:'KRW',IN:'INR',TH:'THB',NZ:'NZD',CH:'CHF',SE:'SEK',NO:'NOK',DK:'DKK',PL:'PLN',CZ:'CZK',HU:'HUF',TR:'TRY',ZA:'ZAR',HK:'HKD',CN:'CNY'};
  return EU.includes(r)?'EUR':(m[r]||'');})();
let FX=null,fxBusy=false;
function fxLoad(cb){if(!FX_CUR)return;if(FX)return cb();try{const c=JSON.parse(sessionStorage.getItem('ka_fx')||'null');if(c&&c.cur===FX_CUR&&Date.now()-c.t<864e5){FX=c;return cb();}}catch(_){}
  if(fxBusy)return;fxBusy=true;fetch('fx-api.php?c='+FX_CUR).then(r=>r.json()).then(j=>{const v=j&&j.ok&&j.rate;if(v>0){FX={cur:FX_CUR,rate:v,t:Date.now()};try{sessionStorage.setItem('ka_fx',JSON.stringify(FX));}catch(_){}cb();}}).catch(()=>{}).finally(()=>{fxBusy=false;});}
function fxText(usd){if(!FX||!(usd>0))return '';try{return '≈ '+new Intl.NumberFormat(undefined,{style:'currency',currency:FX.cur,maximumFractionDigits:FX.rate>50?0:2}).format(usd*FX.rate)+' (approx., you pay in USD)';}catch(_){return '';}}
function fxLine(usd,el){el=el||$('#invFx');if(!el)return;const t=fxText(usd);el.textContent=t;el.hidden=!t;if(!FX&&usd>0)fxLoad(()=>fxLine(usd,el));}
function renderInv(){
  const o=ORDER, empty=o.custom&&!o.total, partial=!o.custom&&o.due<o.total;
  $('#invLines').innerHTML=o.lines.map(([l,a])=>`<dt>${esc(l)}</dt><dd>${empty?'—':a<0?'−'+money2(-a):a?money2(a):'Free'}</dd>`).join('')
    +`<dt class="grand">Total</dt><dd class="grand">${empty?'—':money2(o.total)}</dd>`
    +(partial?`<dt class="now">First payment · ${esc(planLabel(o.plan))}</dt><dd class="now">${money2(o.due)}</dd>`:'');
  $('#invEta').textContent=`USD · ready by ${readyBy(o.rush)}`;
  $('#invHead').textContent=o.custom?'Your suggested price':'Price estimate';{const sl=$('#sendBtn .so-l');if(sl&&!$('#sendBtn').dataset.busy)sl.textContent=o.custom?' Request':' Order';}   // a Custom Inquiry is paid only after Keiko agrees the price
  $('#invNote').textContent=o.custom?"I check your idea and price first (within 6 hours, WIB). Once we agree, I email your invoice with a one-click PayPal link. Nothing is charged now.":"Instant order: pay with PayPal right after sending to secure your slot. Full refund if I can't take your order.";fxLine(o.custom&&!o.total?0:o.total);
  $('#navLbl').textContent=partial?'1st payment (incl. fee)':'Total (incl. fee)';
  $('#navTotal').textContent=empty?'—':money2(partial?o.due:o.total);
}

// ===== PayPal =====
function dueNow(total,plan){if(!(total>0))return 0;const k=/50\/50/.test(plan)?.5:/3x|3×/i.test(plan)?1/3:1;return Math.ceil(+(total*k*100).toFixed(6))/100;}
function planLabel(plan){return /50\/50/.test(plan)?'50% deposit':/3x|3×/i.test(plan)?'1st of 3 installments':'full payment';}
function paypalLink(amount,id,label){
  if(!(amount>0))return '';
  const cur=PAYPAL.currency||'USD', amt=amount.toFixed(2), back=location.protocol.startsWith('http')?location.origin+'/':'https://keikoartist.com/';
  if(PAYPAL.email&&/@/.test(PAYPAL.email)){
    const q=new URLSearchParams({cmd:'_xclick',business:PAYPAL.email,item_name:`KeikoArts commission – ${label} [${id}]`.slice(0,127),item_number:id,amount:amt,currency_code:cur,no_shipping:'1',rm:'1',return:back+'?paid=1&rid='+encodeURIComponent(id),cancel_return:back,notify_url:'https://keikoartist.com/order-api.php?a=ipn'});
    return 'https://www.paypal.com/cgi-bin/webscr?'+q.toString();
  }
  if(PAYPAL.me)return `https://www.paypal.com/paypalme/${encodeURIComponent(PAYPAL.me)}/${amt}${cur}`;
  return '';
}
const PAY_ON=()=>!!((PAYPAL.email&&/@/.test(PAYPAL.email))||PAYPAL.me);
// ===== invoice helpers =====
const TAX=0.13, r2=n=>Math.round(n*100)/100;
const money2=n=>'$'+(+n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const COMMERCIAL_FEE=30;
function invoice(){const sub=budget(),com=sub&&usageVal()==='Commercial'?COMMERCIAL_FEE:0,tax=r2((sub+com)*TAX);return {sub,com,tax,total:r2(sub+com+tax)};}
const usageVal=()=>($('input[name=Usage]:checked')||{value:'Personal'}).value;
function orderRows(){
  const refs=(refFiles.length?refFiles.length+' file(s)':'')+(form['Reference links'].value?(refFiles.length?' + links':'Links'):'')||'-';
  return [['Service',CART_MODE?$('#fService').value:svcName],...(cmOn?[['Usage',usageVal()+' use']]:[['Package',$('#fPackage').value],['Add-ons',$('#fAddons').value],['Payment plan',$('input[name="Payment plan"]:checked').value]]),
    ['Deadline',$('#fDeadline').value||'-'],['Name',$('#fName').value],['Email',$('#fEmail').value||'-'],['Discord',$('#fDiscord').value||'-'],['References',refs],
    ['Total',ORDER.total?money2(ORDER.total)+' incl. 13% PayPal fee':'-']];
}
function err(m){const e=$('#err');e.textContent=m;e.style.display=m?'block':'none';}
function valid(n){
  if(n===1&&!$('input[name=svc]:checked'))return err('Please choose a service.'),false;
  if(n===2){
    const list=[$('#fDetails'),...(cmOn?[$('#budget')]:[]),$('#fDeadline'),$('#fName'),$('#fEmail'),$('#fDiscord')];
    for(const f of list)if(!f.checkValidity()){f.reportValidity();f.focus();return err(f.id==='budget'?'Please enter your price ($5 – $10,000).':f.id==='fDeadline'?'Please pick a deadline that is today or later.':f.id==='fEmail'?'Please enter your email, so I can send you your invoice.':f.id==='fDetails'?'Please tell me about your idea (character, colors, what you need), so I know what to make.':f.id==='fName'?'Please enter your name or VTuber name.':'Please fill in the highlighted field.'),false;}
    if(cmOn&&!budget())return $('#budget').focus(),err('Please enter your price ($5 – $10,000).'),false;
    if(!cmOn&&$('#pp3').checked&&calc()/(1+TAX)<149.99)return err('3 payments are available for orders above $150.'),false;
  }
  err('');return true;
}
function go(n){
  step=n; $$('.ostep').forEach(s=>s.classList.toggle('on',+s.dataset.s===n));
  $('#mnav').hidden=n!==2;
  $('#mTitle').textContent=n===1?'Start an Order':n===3?'Your Cart':CART_MODE?'Checkout':EDIT_ID?'Edit cart item':cmOn?'Custom Order':'Order Form';
  $('#addCartBtn').hidden=cmOn||CART_MODE;$('#sendBtn').hidden=n===2&&!!EDIT_ID;$('#addCartBtn .acl').textContent=EDIT_ID?'Update cart':'Add to cart';if(n===3)renderCart();
  if(n===2){calc();if(!sheetStart)sheetStart=Date.now();}
  err('');try{modal.scrollTop=0;sessionStorage.setItem('ka_open',n===2&&!CART_MODE?svcName:'__list');sessionStorage.removeItem('ka_open_y');}catch(_){}
}
$('#prevBtn').onclick=()=>{const back=CART_MODE||EDIT_ID?3:1;EDIT_ID=null;go(back);};
$('#addCartBtn').onclick=addToCart;$('#navCart').onclick=openCart;$('#cmGo').onclick=()=>go(3);
$('#cartMore').onclick=()=>go(1);
$('#cpApply').onclick=async()=>{const v=$('#fCoupon').value.trim().toUpperCase(),m=$('#cpMsg');$('#fCoupon').value=v;m.className='';
  if(!v){COUPON=null;calc();m.textContent='Please type your code.';return;}
  if(!location.protocol.startsWith('http')){m.textContent='Codes can be checked on keikoartist.com.';return;}
  try{const r=await fetch('order-api.php?a=coupon&code='+encodeURIComponent(v));const j=await r.json();
    if(j&&j.valid){COUPON={code:j.code,percent:j.percent||0,prize:j.prize};m.className='ok';m.textContent='✓ '+j.message;}
    else{COUPON=null;m.className='bad';m.textContent=(j&&j.message)||'This code was not found.';}}
  catch(_){m.className='bad';m.textContent='Could not check the code right now. You can still send it with your order.';}
  calc();};
$('#fCoupon').addEventListener('input',()=>{if(COUPON&&$('#fCoupon').value.trim().toUpperCase()!==COUPON.code){COUPON=null;$('#cpMsg').className='';$('#cpMsg').textContent='Press Apply to check your code.';calc();}});
// "Email me my cart": the cart by email now + one reminder tomorrow (order-api.php cartsave)
$('#cartMail').onclick=async()=>{
  const em=$('#cartEmail').value.trim(),msg=$('#cartMailMsg'),b=$('#cartMail');
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)){msg.textContent='Please check your email address.';$('#cartEmail').focus();return;}
  if(/[?&]dryrun=1/.test(location.search)||!LIVE_SITE){msg.textContent='Test mode: nothing was sent.';return;}
  b.disabled=true;b.textContent='Sending…';
  try{const r=await fetch('order-api.php?a=cartsave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:em,items:readCart()})});const j=await r.json().catch(()=>({}));
    msg.textContent=r.ok&&j.ok?'Sent! Check your inbox (and Spam). Your cart also stays on this device.':(j.error||'Sorry, that did not work. Please try again.');}
  catch(_){msg.textContent='Sorry, that did not work. Please try again.';}
  b.disabled=false;b.textContent='Email me my cart';
};
// "Open my cart" link from the email: put the saved cart back on this device
(function(){const t=(location.search.match(/[?&]cart=([a-f0-9]{24})/)||[])[1];if(!t)return;
  const q=new URLSearchParams(location.search);q.delete('cart');history.replaceState(null,'',location.pathname+(q.toString()?'?'+q:'')+location.hash);
  fetch('order-api.php?a=cartget&t='+t).then(r=>r.json()).then(j=>{if(!j||!j.ok||!Array.isArray(j.items))return;
    const have=readCart(),ids=new Set(have.map(x=>x.svc+'|'+JSON.stringify(x.lines)));
    const add=j.items.filter(x=>SERVICES[x.svc]&&!ids.has(x.svc+'|'+JSON.stringify(x.lines))).map(x=>Object.assign({},x,{id:Date.now().toString(36)+Math.random().toString(36).slice(2,5),t:Date.now()}));
    writeCart([...have,...add].slice(0,CART_MAX));openCart();}).catch(()=>{});})();
$('#cartClear').onclick=()=>{const b=$('#cartClear');if(!b.classList.contains('sure')){b.classList.add('sure');b.querySelector('span').textContent='Tap again to remove all';setTimeout(()=>{if(b.classList.contains('sure')){b.classList.remove('sure');b.querySelector('span').textContent='Clear cart';}},4000);return;}writeCart([]);renderCart();};$('#cartCheckout').onclick=openCheckout;
$('#cartView').addEventListener('click',e=>{
  const sv=e.target.closest('[data-sv]'),mv=e.target.closest('[data-mv]'),sr=e.target.closest('[data-srm]');
  if(sv){const c=readCart(),x=c.find(y=>y.id===sv.dataset.sv);if(x){writeSaved([x,...readSaved().filter(y=>y.id!==x.id)]);writeCart(c.filter(y=>y.id!==x.id));renderCart();}}
  else if(mv){const s2=readSaved(),x=s2.find(y=>y.id===mv.dataset.mv),c=readCart();if(x){if(c.length>=CART_MAX){err(`Your cart is full (${CART_MAX} services).`);return;}x.t=Date.now();writeCart([...c,x]);writeSaved(s2.filter(y=>y.id!==x.id));renderCart();}}
  else if(sr){writeSaved(readSaved().filter(y=>y.id!==sr.dataset.srm));renderCart();}
});
$('#cartList').addEventListener('click',e=>{const ed=e.target.closest('[data-ed]');if(ed){editCartItem(ed.dataset.ed);return;}const b=e.target.closest('[data-rm]');if(!b)return;writeCart(readCart().filter(x=>x.id!==b.dataset.rm));renderCart();});
addEventListener('storage',e=>{if(e.key===CART_KEY)cartUI();});
cartUI();
form.setAttribute('novalidate','');
// ===== the client's latest invoice is kept on their device until it is paid =====
const INV_KEY='ka_inv';
function saveInvoice(last){try{if(last&&last.id&&last.payUrl&&!/PREVIEW|0000-0000/.test(last.id))localStorage.setItem(INV_KEY,JSON.stringify(Object.assign({savedAt:Date.now()},last)));}catch(_){}}
function readInvoice(){try{const v=JSON.parse(localStorage.getItem(INV_KEY)||'null');return v&&v.id&&Date.now()-v.savedAt<45*864e5?v:null;}catch(_){return null;}}
function dropInvoice(id){try{const v=readInvoice();if(!v||!id||v.id===id)localStorage.removeItem(INV_KEY);}catch(_){}}
function setBusy(on,label){const sb=$('#sendBtn');if(on){sb.dataset.busy='1';sb.textContent=label;sb.style.opacity='.75';$('#prevBtn').style.visibility='hidden';}
  else{delete sb.dataset.busy;sb.innerHTML='Send<span class="so-l"> '+(cmOn&&!CART_MODE?'Request':'Order')+'</span> <svg class="ic" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" fill="none" stroke="currentColor" stroke-width="2"/></svg>';sb.style.opacity='';$('#prevBtn').style.visibility='visible';}}
function resetOrderForm(){form.reset();$('#fEmail').disabled=false;$('#fAuto').disabled=false;upState.forEach(s=>{if(s.url&&s.url.startsWith('blob:'))URL.revokeObjectURL(s.url);});upState.clear();upToken=hex(32);refFiles=[];renderRefs();clearDraft();$('#draftNote').hidden=true;sheetStart=0;$('#refSlots').innerHTML='';const m=$('#refMsg');if(m)m.textContent='';setBusy(false);err('');}
const LIVE_SITE=/(^|\.)keikoartist\.com$/i.test(location.hostname)||/^(localhost|127\.0\.0\.1)$/.test(location.hostname);
function postOrder(fd,onProgress){
  return new Promise(res=>{
    try{
      const x=new XMLHttpRequest();x.open('POST','order-api.php?a=submit');x.timeout=300000;
      if(x.upload&&onProgress)x.upload.onprogress=e=>{if(e.lengthComputable)onProgress(e.loaded/e.total);};
      x.onload=()=>{let j=null;try{j=JSON.parse(String(x.responseText||'').replace(/^﻿/,'').trim());}catch(_){}res({status:x.status,j});};
      x.onerror=()=>res({status:0,j:null});x.ontimeout=()=>res({status:-1,j:null});
      x.send(fd);
    }catch(_){res({status:0,j:null});}
  });
}
function errHtml(h){const e=$('#err');e.innerHTML=h;e.style.display='block';}
form.addEventListener('submit',async e=>{
  e.preventDefault();
  if(step!==2||!svc)return;
  $('#fAuto').disabled=false;$('#fEmail').disabled=false;
  if(!valid(2))return;
  if(!$('#agree').checked){err('Please agree to the Terms of Service first.');$('#agree').focus();return;}
  const bad=[...form.elements].find(el=>el.willValidate&&!el.checkValidity());
  if(bad){setTimeout(()=>{bad.reportValidity();bad.focus();},50);err(bad.id==='fDeadline'?'Please pick a deadline that is today or later.':'Please check the highlighted field.');return;}
  if($('#sendBtn').dataset.busy)return;
  err('');setBusy(true,refFiles.length?'Uploading references…':'Sending…');
  const slow=setTimeout(()=>{if($('#sendBtn').dataset.busy)err('Still sending… slow connection or large files. Please wait, do not close this page.');},15000);
  $('#fEmail').value=$('#fEmail').value.trim();
  if(refFiles.length&&CAN_UPLOAD()&&location.protocol.startsWith('http')){   // let the background uploads finish first
    pump();
    while(uploadsBusy()){
      const tot=refFiles.reduce((a,f)=>a+f.size,0)||1, sent=refFiles.reduce((a,f)=>{const st=upState.get(f)||{};return a+(st.status==='done'?f.size:Math.min(f.size,st.sent||0));},0);
      $('#sendBtn').textContent=`Uploading references… ${Math.min(99,Math.round(sent/tot*100))}%`;
      await new Promise(z=>setTimeout(z,300));
    }
    $('#sendBtn').textContent='Sending…';
  }
  const upOk=refFiles.filter(f=>(upState.get(f)||{}).status==='done'), upBad=refFiles.filter(f=>(upState.get(f)||{}).status!=='done');
  const totalNum=calc(), plan=cmOn?'Full payment':$('input[name="Payment plan"]:checked').value, iv=cmOn?invoice():null, due=cmOn?iv.total:dueNow(totalNum,plan);
  const lines=ORDER.lines.map(x=>x.slice()), invTotal=cmOn?iv.total:totalNum;
  const name=$('#fName').value.trim(), total=$('#fTotal').value;
  const label=cmOn?`Custom commission, ${usageVal()} use, incl. 13% PayPal fee`:`${svcName} (${$('#fPackage').value})`;
  const rows=orderRows();
  const ctx={name,usage:usageVal(),deadline:$('#fDeadline').value,brief:$('#fDetails').value.trim().slice(0,140),contact:$('#fEmail').value+($('#fDiscord').value?' · Discord '+$('#fDiscord').value:'')};
  const mkInv=(dateStr,emailed,tot,dueAmt)=>({date:dateStr,name,contact:ctx.contact,deadline:ctx.deadline,brief:ctx.brief,usage:cmOn?ctx.usage:'',custom:cmOn,service:svcName,lines,total:tot,due:dueAmt,plan,emailed});
  const done=last=>{clearTimeout(slow);KA_STAT('order_sent');if(CART_MODE){writeCart([]);CART_MODE=false;}try{sessionStorage.setItem('ka_last',JSON.stringify(last));}catch(_){}resetOrderForm();closeOrder();showThanks(last);};
  const restore=()=>{clearTimeout(slow);$('#fEmail').disabled=false;$('#fAuto').disabled=false;setBusy(false);};
  const stamp=()=>{const d=new Date(),pad=n=>String(n).padStart(2,'0');return {md:pad(d.getMonth()+1)+pad(d.getDate()),date:d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})};};
  // email copy through FormSubmit (used when the hosting can't send email, and as the backup path)
  const buildCopy=(id,payUrl,dateStr,filesNote)=>{
    $('#fReq').value=id;
    $('#fSubject').value=$('#fSubject').value.replace(/ \[(INV|REQ)-[\w-]+\]$/,'')+' ['+id+']';
    $('#fDue').value=cmOn?`${money2(due)} — full payment incl. 13% PayPal fee (invoice PDF: Discord / admin)`
      :due?money2(due)+' — '+planLabel(plan)+' (invoice PDF: Discord / admin)':'-';
    const lineTxt=lines.map(([l,a])=>`${l}: ${a?money2(a):'Free'}`).join('\n');
    $('#fAuto').value=`Hi ${name}, thank you for your order at KeikoArts! ♡

ORDER ${id} · ${dateStr}
${lineTxt}
TOTAL: ${money2(invTotal)} USD (incl. 13% PayPal fee)

${payUrl?`Pay ${money2(due)} now with PayPal (one click, the amount is already filled in):
${payUrl}
Full refund if I can't take your order.`:'I review your order and email you your invoice (PDF) within 6 hours, with a one-click PayPal link.'}
Want to chat on Discord? Join my server and message me with your order ID:
https://discord.gg/FbgWxMPjf

— Keiko, KeikoArts`;
    const data={};
    new FormData(form).forEach((v,k)=>{if(typeof v==='string'&&!['svc','pkg','add','mxType','mxSize','_next','_honey','_dryrun','_price','_total'].includes(k))data[k]=v;});
    data._captcha='false';data._template='table';
    if(filesNote)data['Reference files']=filesNote;
    return data;
  };
  const sendOnce=async data=>{try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),20000);
    const r=await fetch('https://formsubmit.co/ajax/keikoarts22@gmail.com',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(data),signal:ctl.signal});clearTimeout(to);
    const jj=await r.json().catch(()=>null);return !!(r.ok&&jj&&String(jj.success)==='true');}catch(_){return false;}};
  const sendCopy=async data=>(await sendOnce(data))||(await new Promise(z=>setTimeout(z,2000)),await sendOnce(data));
  if(!LIVE_SITE){   // preview copy (not on keikoartist.com): show the invoice, nothing is sent
    const t=stamp(), id=(cmOn?'INV-':'REQ-')+t.md+'-PREVIEW';
    done({id,due,plan,payUrl:'',rows,emailed:false,warn:'PREVIEW ONLY: this order was not sent. Real orders work on keikoartist.com.'});
    return;}
  // 1) KeikoArts server: saves the order + files, returns the invoice
  if(location.protocol.startsWith('http')){
    const fd=new FormData(form);
    ['_next','_autoresponse','_subject','_captcha','_template','mxType','mxSize'].forEach(k=>fd.delete(k));
    [...fd.keys()].filter(k=>/^attachment\d+$/.test(k)).forEach(k=>fd.delete(k));
    fd.set('_up_token',upToken);fd.set('_up_files',upOk.map(f=>upState.get(f).fid).join(','));
    fd.set('_lines',JSON.stringify(lines));fd.set('_taxed','1');fd.set('_price',cmOn?String(iv.sub):'0');fd.set('_total',String(totalNum||0));fd.set('_t',String(Math.max(0,Math.round((Date.now()-(sheetStart||Date.now()))/1000))));
    if(/[?&]dryrun=1/.test(location.search))fd.set('_dryrun','1');
    const prog=p=>{if(refFiles.length&&$('#sendBtn').dataset.busy)$('#sendBtn').textContent=p<.995?`Uploading… ${Math.round(p*100)}%`:'Sending…';};
    let res=await postOrder(fd,prog);
    if(res.status<=0||(res.status>=500&&!res.j)){await new Promise(r=>setTimeout(r,1500));res=await postOrder(fd,prog);}
    const j=res.j;
    if(res.status===200&&j&&j.ok&&j.id){
      const missing=[...upBad.map(f=>f.name),...(j.skipped_names||[])];
      const warn=[j.dry_run?'TEST MODE: nothing was saved or sent.':'',
        missing.length?`${missing.length} reference file(s) couldn't be uploaded (${missing.join(', ')}). Please email them to keikoarts22@gmail.com.`:''].filter(Boolean).join(' ');
      const copy=(!j.dry_run&&!j.notified)?buildCopy(j.id,j.pay_url||'',j.date,j.files?j.files+' file(s) uploaded: see admin → Orders':''):null;
      if(copy&&j.pdf_url)copy['Invoice PDF (send to client)']=j.pdf_url;
      if(copy&&j.emailed)delete copy._autoresponse;
      const lastInv={id:j.id,due:j.due,plan:j.plan,payUrl:j.pay_url||'',rows,emailed:!!j.emailed,warn,key:j.key||'',track:j.dry_run?'':(j.track_url||'')};
      if(copy){$('#sendBtn').textContent='Almost done…';await Promise.race([sendCopy(copy),new Promise(z=>setTimeout(z,9000))]);}   // the email to Keiko goes out before the page can be closed
      done(lastInv);
      return;}
    if(j&&j.ok===false&&j.error&&![404,405].includes(res.status)&&res.status<500){restore();err(j.error);return;}
  }
  // 2) backup: FormSubmit via AJAX (stays on this page). Only used if the KeikoArts server can't be reached.
  const t=stamp(), id=(cmOn?'INV-':'REQ-')+t.md+'-'+Math.floor(1000+Math.random()*9000);
  const payUrl=PAY_ON()?paypalLink(due,id,label):'';
  const ok=await sendCopy(buildCopy(id,payUrl,t.date,refFiles.length?refFiles.length+' file(s) could not be uploaded: ask the client to send them on Discord':''));
  if(ok){
    if(location.protocol.startsWith('http')){try{fetch('notify-discord.php',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({id,due:$('#fDue').value,service:$('#fService').value,package:$('#fPackage').value,addons:$('#fAddons').value,total,plan,name,email:$('#fEmail').value,discord:$('#fDiscord').value,deadline:$('#fDeadline').value,refs:[refFiles.length?refFiles.length+' file(s) attached (see email)':'',form['Reference links'].value].filter(Boolean).join(' · '),details:(cmOn?`[${usageVal()} use] `:'')+$('#fDetails').value,_honey:form._honey.value})}).catch(()=>{});}catch(_){}}
    const lastInv={id,due,plan,payUrl:'',rows,emailed:!!$('#fEmail').value,warn:refFiles.length?'Please email your reference images to keikoarts22@gmail.com (they could not be uploaded).':''};
    saveInvoice(Object.assign({},lastInv,{warn:''}));
    done(lastInv);
    return;}
  restore();$('#fSubject').value=$('#fSubject').value.replace(/ \[(INV|REQ)-[\w-]+\]$/,'');
  errHtml(`Sorry, your order couldn't be sent right now. Please check your internet and try again in a minute, or <a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener" style="color:inherit;font-weight:600;text-decoration:underline">message me on Discord</a> ♡`);
});



// price breakdown on service cards
$$('.card').forEach(card=>{
  const name=card.querySelector('h3')?.textContent.trim(), sv=SERVICES[name]; if(!sv||sv.quote)return;
  const box=document.createElement('div'); box.className='tiers';
  if(sv.table){
    box.innerHTML=`<table><thead><tr><th></th>${sv.table.cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>${sv.table.rows.map(([r,ix])=>`<tr><th>${r}</th>${ix.map(i=>`<td>${money(sv.packages[i][1])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }else{
    box.innerHTML='<ul>'+sv.packages.map(([n,pr])=>`<li><span>${n}</span><b>${money(pr)}${sv.qty?'<small>/ea</small>':''}</b></li>`).join('')+'</ul>';
  }
  const ad=sv.addons.filter(a=>a[1]>0);
  if(ad.length)box.innerHTML+=`<details class="addons"><summary>Add-ons</summary><ul>${ad.map(([n,pr])=>`<li><span>${n}</span><b>+${money(pr)}</b></li>`).join('')}</ul></details>`;
  card.querySelector('.price').before(box);
});

// service galleries (swipe / arrows / dots)
const SMALLCARD=Math.min(innerWidth/2,400)*(window.devicePixelRatio||1)<=380;   // phones: 360px card images (images/s/)
const NOTHUMB=["animated-vtuber-banner-eyes-silver"];   // animated images have no small version
$$('.card').forEach(card=>{
  const name=card.querySelector('h3')?.textContent.trim(), list=GALLERY[name]; if(!list||!list.length)return;
  const old=card.querySelector('.img');
  const g=document.createElement('div'); g.className='gal';
  g.innerHTML=`<div class="gal-track">${list.map(f=>`<div class="gal-slide${WIDE.includes(f)?' wide':''}${CONTAIN.includes(f)?' contain':''}" data-bg="images/${NOTHUMB.includes(f)?'':(SMALLCARD&&!/animated/.test(f)?'s/':'t/')}${f}.webp" role="img" aria-label="${name} example"></div>`).join('')}</div>`+
    (list.length>1?`<button class="gal-btn prev" type="button" aria-label="Previous">‹</button><button class="gal-btn next" type="button" aria-label="Next">›</button><div class="gal-dots">${list.map((_,i)=>`<i class="${i?'':'on'}"></i>`).join('')}</div>`:'');
  old.replaceWith(g);
  if(list.length<2)return;
  const tr=g.querySelector('.gal-track'),dots=[...g.querySelectorAll('.gal-dots i')];
  const go=d=>{const w=tr.clientWidth,i=Math.round(tr.scrollLeft/w);let n=i+d;if(n<0)n=list.length-1;if(n>=list.length)n=0;tr.scrollTo({left:n*w,behavior:'smooth'});};
  g.querySelector('.prev').onclick=()=>go(-1); g.querySelector('.next').onclick=()=>go(1);
  tr.addEventListener('scroll',()=>{const i=Math.round(tr.scrollLeft/tr.clientWidth);dots.forEach((d,k)=>d.classList.toggle('on',k===i));},{passive:true});
});

// service cards: price and button share one footer row
if(innerWidth<600){const si=$('#svcSearch');if(si)si.placeholder='Search: emotes, logo, rig…';}
$$('.services .card').forEach(c=>{const p=c.querySelector(':scope>.price'),b=c.querySelector(':scope>.req');if(!p||!b)return;const f=document.createElement('div');f.className='card-foot';p.before(f);f.append(p,b);});
// lightbox
(function(){
  const lb=$('#lb'),img=$('#lbImg');let list=[],i=0,svc=null,lastFocus=null;
  const show=()=>{const it=list[i];img.src=it.src;img.alt=it.cap;$('#lbCap').textContent=it.cap;$('#lbCount').textContent=list.length>1?`${i+1} / ${list.length}`:'';};
  const open=window.openLB=(items,idx,service)=>{list=items;i=idx||0;svc=service;lastFocus=document.activeElement;lb.classList.toggle('single',list.length<2);show();lb.classList.add('show');lb.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';$('.lb-x').focus();};
  const close=()=>{lb.classList.remove('show');lb.setAttribute('aria-hidden','true');document.body.style.overflow='';img.removeAttribute('src');lastFocus&&lastFocus.focus();};
  const step=d=>{if(list.length<2)return;i=(i+d+list.length)%list.length;show();};
  $('.lb-prev').onclick=()=>step(-1);$('.lb-next').onclick=()=>step(1);$('.lb-x').onclick=close;
  lb.addEventListener('click',e=>{if(e.target===lb)close();});
  document.addEventListener('keydown',e=>{if(!lb.classList.contains('show'))return;if(e.key==='Escape'){e.stopImmediatePropagation();close();}if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1);});
  let x0=null;lb.addEventListener('touchstart',e=>{x0=e.touches[0].clientX},{passive:true});
  lb.addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40)step(dx<0?1:-1);x0=null;},{passive:true});
  $('#lbOrder').onclick=()=>{close();openOrder(svc||undefined);};
  const urlOf=el=>{const h=el.getAttribute&&el.getAttribute('href');if(h&&/\.(webp|png|jpe?g|gif)$/i.test(h))return h;const i=el.querySelector('img');return i?(i.currentSrc||i.src):(getComputedStyle(el).backgroundImage.match(/url\(["']?([^"')]+)["']?\)/)||[])[1];};
  // service galleries
  $$('.card').forEach(card=>{
    const name=card.querySelector('h3')?.textContent.trim();
    const slides=[...card.querySelectorAll('.gal-slide')];if(!slides.length)return;
    // slides open the service detail (handled by card click)
  });
  // featured works
  const works=[...$$('.works .work:not(.rig)')];
  works.forEach((w,k)=>w.addEventListener('click',e=>{e.preventDefault();open(works.map(x=>({src:urlOf(x),cap:x.querySelector('.tag')?.textContent||''})),k,null);}));
})();

// three books on one shelf (screens 760px+; phones keep the normal sections): Portfolio, How to Order, TOS & FAQ.
// The work items, FAQ answers and terms are taken from the page itself, so the text stays the same in both places.
(function(){
  const grid=$('.works.fw'),stage=$('#bookStage'),shelf=$('#bkShelf');if(!grid||!stage||!shelf||innerWidth<760)return;
  const prev=$('#bkPrev'),next=$('#bkNext'),count=$('#bkCount');
  const moon='<svg class="cv-moon" viewBox="0 0 64 64" aria-hidden="true"><defs><radialGradient id="cvg" cx=".35" cy=".3"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#ffd1e6"/><stop offset="1" stop-color="#f2628f"/></radialGradient></defs><path d="M40 6a26 26 0 1 0 18 44A22 22 0 0 1 40 6Z" fill="url(#cvg)"/><path d="M50 10l1.6 3.6L55 15l-3.4 1.4L50 20l-1.6-3.6L45 15l3.4-1.4z" fill="#fff"/></svg>';
  const cover=(t,sub)=>'<div class="face-in cover-in">'+moon+'<h3>'+t+'</h3><p>'+sub+'</p><span class="cv-hint">Open the book ›</span></div>';
  const endpg='<div class="face-in"><h3>Your character next?</h3><p>Pick your options in the order form, see your total and order instantly.</p><a href="#order" data-order class="btn btn-pink arrow">Start a Project</a></div>';
  const txt=(items)=>({text:items.map(([h,body])=>'<h4>'+h+'</h4>'+body).join('')});
  // book 1: portfolio
  const works=[...grid.children];
  const f1=[cover('Featured Works','KeikoArts · spellbook')];
  works.forEach((w,i)=>f1.push({el:(c=>{c.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));c.classList.add('in-book');const v=c.querySelector('video');if(v){v.controls=true;v.removeAttribute('autoplay');}return c})(w.cloneNode(true)),cap:(w.querySelector('.tag')||{}).textContent||'',n:i+1,of:works.length}));
  f1.push('<div class="face-in"><h3>Your character next?</h3><p>Every piece here was drawn from scratch. Pick your options, see your total and order instantly.</p><a href="#order" data-order class="btn btn-pink arrow">Start a Project</a><a href="/vtuber-portfolio/" class="btn btn-ghost">Full portfolio</a></div>');
  // book 2: how to order (same facts as the order form, TOS and FAQ)
  const f2=[cover('How to Order','Five steps · no account needed'),
    txt([['1 · Pick a service','<p>Choose a service in <a href="#services">Our Services</a> and press Order now. The form shows every option and your total before you send it.</p>'],['2 · Send the form','<p>Tell me about your character: a description, a character sheet or a few references. Your name and email are needed to send your invoice and updates.</p>']]),
    txt([['3 · Order instantly','<p>Your total, incl. 13% PayPal fee, is shown before you send. Custom Inquiry: I agree the price with you first and email your invoice (within 6 hours, WIB).</p>'],['4 · Pay with PayPal','<p>Card or PayPal balance, in USD, right after sending. Pay in full, 50/50, or in 3 parts for orders above $150. Your slot is secured once payment is received.</p>']]),
    txt([['5 · I make your art','<p>Sketch → lineart → coloring → (rigging). You get progress updates at every stage. Every commission takes 3 weeks at most.</p>'],['6 · Delivery','<p>Your final files come by email, ready to stream. Questions any time on <a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener">Discord</a>.</p>']]),
    endpg];
  // book 3: FAQ + terms
  const faq=[...document.querySelectorAll('#faq .faq-grid details')].map(d=>[esc(d.querySelector('summary').textContent),d.querySelector('p').outerHTML]);
  const tos=[...document.querySelectorAll('#tos .tos>div')].map(d=>[esc(d.querySelector('h3').textContent),[...d.children].slice(1).map(x=>x.outerHTML).join('')]);
  const f3=[cover('TOS &amp; FAQ','Questions · terms · privacy')];
  for(let i=0;i<faq.length;i+=2)f3.push(txt(faq.slice(i,i+2)));
  for(let i=0;i<tos.length;i+=2)f3.push(txt(tos.slice(i,i+2)));
  f3.push(endpg);
  const defs=[['works','Featured Works',f1],['order','How to Order',f2],['terms','TOS & FAQ',f3]];
  const books=defs.map(([id,title,faces])=>{
    if(faces.length%2)faces.push('<div class="face-in">'+moon+'</div>');
    const el=document.createElement('div');el.className='book at-start';el.dataset.book=id;el.hidden=true;stage.appendChild(el);
    const leaves=[];
    for(let i=0;i<faces.length;i+=2){
      const leaf=document.createElement('div');leaf.className='leaf';
      [faces[i],faces[i+1]].forEach((f,k)=>{const d=document.createElement('div');d.className='face '+(k?'back':'front');
        if(typeof f==='string'){d.innerHTML=f;d.classList.add(i===0&&!k||i+k===faces.length-1?'cover':'endpage');}
        else if(f.text){d.classList.add('textpage');d.innerHTML='<div class="tp">'+f.text+'</div><p class="pg-num">'+(i+k)+' / '+(faces.length-2)+'</p>';}
        else{const a=document.createElement('div');a.className='pg-art';a.appendChild(f.el);d.appendChild(a);d.insertAdjacentHTML('beforeend','<p class="pg-cap">'+esc(f.cap)+'</p><p class="pg-num">'+f.n+' / '+f.of+'</p>');}
        leaf.appendChild(d);});
      el.appendChild(leaf);leaves.push(leaf);
    }
    el.querySelectorAll('a,img').forEach(x=>x.draggable=false);
    return {id,title,el,leaves,n:leaves.length,cur:0,pages:faces.length};
  });
  let B=books[0];
  const draw=()=>{const {leaves,n,cur,el}=B;leaves.forEach((l,i)=>{const f=i<cur;l.classList.toggle('flipped',f);l.classList.toggle('next-up',i===cur);l.classList.toggle('prev-up',i===cur-1);l.style.zIndex=f?i+1:n-i;});
    el.classList.toggle('at-start',cur===0);el.classList.toggle('at-end',cur===n);
    prev.disabled=cur===0;next.disabled=cur===n;
    count.textContent=cur===0?B.title:cur===n?'The end':'Pages '+(cur*2-1)+'–'+Math.min(cur*2,B.pages-1);};
  const turn=l=>{if(!l)return;l.classList.remove('turning');void l.offsetWidth;l.classList.add('turning');setTimeout(()=>l.classList.remove('turning'),1000);};
  const go=d=>{const t=Math.max(0,Math.min(B.n,B.cur+d));if(t===B.cur)return;turn(B.leaves[d>0?B.cur:t]);B.cur=t;draw();};
  const tabs=[...shelf.querySelectorAll('[data-open]')];
  const show=(id,page)=>{const nb=books.find(x=>x.id===id)||books[0];
    if(nb!==B){B.el.hidden=true;B=nb;}B.el.hidden=false;
    tabs.forEach(t=>{const on=t.dataset.open===B.id;t.classList.toggle('on',on);t.setAttribute('aria-pressed',on);});
    $('#bookWrap').dataset.book=B.id;
    if(page!=null){B.cur=Math.max(0,Math.min(B.n,page));}draw();};
  tabs.forEach(t=>t.addEventListener('click',()=>{stop();const was=B.id===t.dataset.open;show(t.dataset.open);if(!was&&B.cur===0)setTimeout(()=>go(1),350);}));
  prev.onclick=()=>{stop();go(-1);};next.onclick=()=>{stop();go(1);};
  let dragged=false,drag=null;
  books.forEach(bk=>{
    bk.leaves.forEach((l,i)=>l.addEventListener('click',e=>{if(dragged){e.preventDefault();e.stopPropagation();dragged=false;return;}if(e.target.closest('a,button,video,.tp'))return;stop();go(i<B.cur?-1:1);},true));
    bk.el.addEventListener('pointerdown',e=>{if(e.button||e.target.closest('.tp a'))return;const leaf=e.target.closest('.leaf');if(!leaf)return;const i=B.leaves.indexOf(leaf);
      if(i!==B.cur&&i!==B.cur-1)return;if(!e.target.closest('video,.tp'))e.preventDefault();drag={leaf,i,x:e.clientX,w:B.el.getBoundingClientRect().width/2,on:false,a:0};});
  });
  addEventListener('pointercancel',()=>{if(drag){drag.leaf.classList.remove('dragging');drag.leaf.style.transform='';drag=null;draw();}});
  addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x;if(!drag.on){if(Math.abs(dx)<8)return;drag.on=true;stop();drag.leaf.classList.add('dragging');drag.leaf.style.zIndex=B.n+5;}
    const r=Math.max(0,Math.min(1,(drag.i===B.cur?-dx:dx)/(drag.w*1.1)));drag.a=r;
    drag.leaf.style.transform='rotateY('+(drag.i===B.cur?-180*r:-180+180*r)+'deg)';drag.leaf.style.setProperty('--sh',(Math.sin(r*Math.PI)*.45).toFixed(3));});
  addEventListener('pointerup',()=>{if(!drag)return;const d=drag;drag=null;if(!d.on)return;dragged=true;setTimeout(()=>dragged=false,50);
    d.leaf.classList.remove('dragging');d.leaf.style.transform='';d.leaf.style.removeProperty('--sh');
    if(d.a>.35){B.cur=d.i===B.cur?B.cur+1:B.cur-1;}draw();});
  stage.addEventListener('keydown',e=>{if(e.key==='ArrowRight'){stop();go(1);}if(e.key==='ArrowLeft'){stop();go(-1);}});stage.tabIndex=0;
  document.documentElement.classList.add('has-book');show('works');
  // the grid of works stays on the page; the shelf opens as a pop-up from the "Open the spellbook" button (UX review, Nov 2026)
  const wrap=$('#bookWrap'),root=document.documentElement;let lastFocus=null;
  const x=document.createElement('button');x.type='button';x.className='bk-close';x.setAttribute('aria-label','Close the book');x.textContent='✕';wrap.prepend(x);
  wrap.setAttribute('role','dialog');wrap.setAttribute('aria-modal','true');
  const openBook=(id,page)=>{stage.querySelectorAll('video[data-poster]').forEach(v=>{v.poster=v.dataset.poster;v.removeAttribute('data-poster');});lastFocus=document.activeElement;root.classList.add('book-open');document.body.style.overflow='hidden';show(id||'works',page==null?(id&&id!=='works'?1:0):page);if((id||'works')==='works'&&B.cur===0)setTimeout(()=>go(1),450);setTimeout(()=>x.focus(),50);};
  const closeBook=()=>{root.classList.remove('book-open');document.body.style.overflow='';stop();lastFocus&&lastFocus.focus();};
  x.onclick=closeBook;wrap.addEventListener('click',e=>{if(e.target===wrap)closeBook();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&root.classList.contains('book-open'))closeBook();});
  const more=$('#portfolio .sec-more');if(more){const ob=document.createElement('button');ob.type='button';ob.className='btn btn-pink bk-open';ob.innerHTML='✦ Open the spellbook <small style="font-weight:400;opacity:.85">· portfolio, how to order, FAQ</small>';ob.onclick=()=>openBook('works');more.prepend(ob);}
  // works inside the book open full size like the grid
  stage.addEventListener('click',e=>{const w=e.target.closest('.work.in-book:not(.rig)');if(!w||dragged)return;e.preventDefault();const all=[...stage.querySelectorAll('.work.in-book:not(.rig)')];
    if(window.openLB)openLB(all.map(z=>({src:z.getAttribute('href'),cap:(z.querySelector('.tag')||{}).textContent||''})),all.indexOf(w),null);});
  false&&[...document.querySelectorAll('.bk-mini')].forEach((m,k,all)=>m.addEventListener('click',e=>{e.preventDefault();if(window.openLB)openLB(all.map(x=>({src:x.getAttribute('href'),cap:x.querySelector('span').textContent})),k,null);}));
  // the portfolio book turns its own pages while it is on screen; stops for good once the visitor uses any book
  let vis=false,manual=false,timer=0;
  const tick=()=>{clearTimeout(timer);if(manual||!vis||document.hidden||B.id!=='works')return;timer=setTimeout(()=>{if(!manual&&vis&&!drag&&B.id==='works'){if(B.cur>=B.n-1){B.cur=0;draw();setTimeout(()=>go(1),900);}else go(1);}tick();},B.cur===0?600:3200);};
  function stop(){manual=true;clearTimeout(timer);}
  document.addEventListener('visibilitychange',tick);
  if('IntersectionObserver' in window&&!navigator.webdriver&&!matchMedia('(prefers-reduced-motion:reduce)').matches){new IntersectionObserver(es=>{vis=es[0].isIntersecting;tick();},{threshold:.5}).observe(stage);}
})();
// phones: the floating Order button steps aside over the service cards (they have their own buttons);
// a field the form asks for scrolls into view above the sticky Total bar
(function(){const sv=document.getElementById('services');if(sv&&'IntersectionObserver' in window)new IntersectionObserver(es=>es.forEach(e=>document.body.classList.toggle('in-services',e.isIntersecting)),{rootMargin:'-20% 0px -20% 0px'}).observe(sv);
  const f=document.getElementById('orderForm');if(f)f.addEventListener('invalid',e=>{const el=e.target;setTimeout(()=>{try{el.scrollIntoView({block:'center',behavior:'smooth'})}catch(_){el.scrollIntoView()}},0);},true);})();
// debut planner + character brief (same facts as the TOS: every commission within 3 weeks; rush about half the usual time)
(function(){const d=$('#dbDate'),o=$('#dbOut');if(!d||!o)return;
  const day=864e5,today=new Date();today.setHours(0,0,0,0);d.min=new Date(today-today.getTimezoneOffset()*6e4).toISOString().slice(0,10);
  const fmt=t=>t.toLocaleDateString('en-GB',{day:'numeric',month:'long'});
  d.addEventListener('change',()=>{if(!d.value){o.textContent='Choose a date to check.';o.className='db-out';return;}
    const t=new Date(d.value+'T00:00:00'),left=Math.round((t-today)/day),by=new Date(t-21*day);
    if(left>=21){o.innerHTML='You have time. Order by <b>'+fmt(by)+'</b> to be ready for your debut on '+fmt(t)+'.';o.className='db-out ok';}
    else if(left>=11){o.innerHTML='It\'s tight. Rush delivery (+25%) takes about half the usual time, so <a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener">message me first</a> and I\'ll tell you if I can make it.';o.className='db-out warn';}
    else{o.innerHTML='That\'s very soon. <a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener">Message me on Discord</a> and we\'ll see what\'s possible, for example a PNGTuber first.';o.className='db-out no';}});
  const BRIEF='Name:\nPersonality and vibe:\nColors (hair, eyes, outfit):\nOutfit and accessories:\nMust-have details:\nExpressions I want:\nReferences (links):\nDebut date:'+'';
  const b=$('#dbBrief');if(b)b.onclick=()=>{openOrder('VTuber');setTimeout(()=>{const f=$('#fDetails');if(f&&!f.value.trim()){f.value=BRIEF+(d.value?' '+d.value:'');f.dispatchEvent(new Event('input',{bubbles:true}));}if(f)f.scrollIntoView({block:'center'});},350);};
})();
// service detail modal
(function(){
  const sd=$('#sd');let cur=null,last=null;
  const close=()=>{sd.classList.remove('show');sd.setAttribute('aria-hidden','true');document.body.style.overflow='';last&&last.focus();};
  const openSD=name=>{
    const card=[...$$('.card')].find(c=>c.querySelector('h3')?.textContent.trim()===name);if(!card)return;
    cur=name;last=document.activeElement;const d=DETAILS[name]||{},sv=SERVICES[name];
    const imgs=(GALLERY[name]||[]).map(f=>`images/${f}.webp`);
    $('#sdTrack').innerHTML=imgs.map((u,i)=>`<div style="background-image:url(${u})" data-i="${i}" role="img" aria-label="${esc(name)} example ${i+1}"></div>`).join('');
    $('#sdDots').innerHTML=imgs.length>1?imgs.map((_,i)=>`<i class="${i?'':'on'}"></i>`).join(''):'';
    $$('.sd-prev,.sd-next').forEach(b=>b.style.display=imgs.length>1?'':'none');
    $('#sdTitle').textContent=name;
    $('#sdAbout').textContent=d.about||card.querySelector('p')?.textContent||'';
    const t=card.querySelector('.tiers');
    $('#sdPrice').innerHTML=t?t.outerHTML.replace('<details class="addons">','<details class="addons" open>'):`<div class="sd-big">${card.querySelector('.price b').textContent}</div>`;
    $('#sdInc').innerHTML=(d.includes||[]).map(x=>`<li>${esc(x)}</li>`).join('');
    $('#sdNote').textContent=d.notes||'';$('#sdNote').hidden=!d.notes;
    $('#sdMeta').innerHTML=`<span>Price: <b>${card.querySelector('.price b').textContent}</b></span>${sv&&sv.eta?`<span>Estimated time: <b>${sv.eta}</b></span>`:''}`;
    $('#sdOrder').textContent=name==='Custom Inquiry'?'Send inquiry':'Order now';
    sd.classList.add('show');sd.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
    $('#sdTrack').scrollLeft=0;$('.sd-x').focus();
  };
  window.openSD=openSD;
  $('.sd-x').onclick=close;sd.addEventListener('click',e=>{if(e.target===sd)close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&sd.classList.contains('show')&&!$('#lb').classList.contains('show'))close();});
  const tr=$('#sdTrack');
  const go=d=>{const n=tr.children.length;if(n<2)return;let i=Math.round(tr.scrollLeft/tr.clientWidth)+d;i=(i+n)%n;tr.scrollTo({left:i*tr.clientWidth,behavior:'smooth'});};
  $('.sd-prev').onclick=()=>go(-1);$('.sd-next').onclick=()=>go(1);
  tr.addEventListener('scroll',()=>{const i=Math.round(tr.scrollLeft/tr.clientWidth);$$('#sdDots i').forEach((d,k)=>d.classList.toggle('on',k===i));},{passive:true});
  tr.addEventListener('click',e=>{const el=e.target.closest('[data-i]');if(!el)return;const imgs=[...tr.children].map(x=>({src:x.style.backgroundImage.slice(5,-2),cap:cur}));window.openLB(imgs,+el.dataset.i,cur);});
  $('#sdOrder').onclick=()=>{const n=cur;close();openOrder(n);};
  $$('.card').forEach(card=>{
    const name=card.querySelector('h3')?.textContent.trim();
    const m=document.createElement('div');m.className='more';m.textContent='View details →';(card.querySelector('.card-foot')||card.querySelector('.price')).before(m);
    card.addEventListener('click',e=>{if(e.target.closest('.req,.gal-btn,summary,.addons'))return;openSD(name);});
    card.tabIndex=0;card.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target===card)openSD(name);});
  });
})();


// VTubers marquee
(function(){
  const t=$('#vtTrack');if(!VTUBERS.length){$('#clients').hidden=true;return;}
  const item=v=>{const inner=`<img src="images/${v.img}.webp" alt="${esc(v.name||'Original VTuber character by KeikoArts')}" loading="lazy">${v.name?`<span>${esc(v.name)}</span>`:''}`;
    return v.link&&/^https:\/\//.test(v.link)?`<a class="vt" href="${esc(v.link)}" target="_blank" rel="noopener">${inner}</a>`:`<div class="vt">${inner}</div>`;};
  const set=VTUBERS.map(item).join(''),one=set.repeat(Math.max(1,Math.ceil(2600/(VTUBERS.length*170))));   // repeated so even very wide screens never show an empty gap
  t.innerHTML=one+`<span aria-hidden="true" class="vt-dup">${one}</span>`;
  t.style.setProperty('--dur',Math.max(20,VTUBERS.length*5)*Math.max(1,Math.ceil(2600/(VTUBERS.length*170)))+'s');
})();

// performance: lazy-load gallery images, play video only when visible
(function(){
  const loadSlide=el=>{if(el.dataset.bg){el.style.backgroundImage=`url(${el.dataset.bg})`;delete el.dataset.bg;}};
  const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){const t=e.target;
    const first=t.querySelector('.gal-slide[data-bg]');if(first)loadSlide(first);
    // load the rest after first is shown
    const rest=()=>t.querySelectorAll('.gal-slide[data-bg]').forEach(loadSlide);
    ['pointerenter','touchstart','focusin'].forEach(ev=>t.addEventListener(ev,rest,{once:true,passive:true}));
    const tk=t.querySelector('.gal-track');if(tk)tk.addEventListener('scroll',rest,{once:true,passive:true});io.unobserve(t);}}),{rootMargin:'200px'});
  $$('.gal').forEach(g=>io.observe(g));
  const vids=[...document.querySelectorAll('.works.fw video')];if(!vids.length)return;
  // posters load only when the videos come near (saves ~180 KB at page load)
  const lp=v=>{if(v.dataset.poster){v.poster=v.dataset.poster;v.removeAttribute('data-poster');}};
  if('IntersectionObserver' in window){const pio=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){lp(e.target);pio.unobserve(e.target);}}),{rootMargin:'600px'});vids.forEach(v=>pio.observe(v));}else vids.forEach(lp);
  if(matchMedia('(max-width:820px)').matches){vids.forEach(v=>v.controls=true);return;}   // phones: poster only, tap play (saves data)
  vids.forEach(v=>{
  const anyModal=()=>!!document.querySelector('.modal.show,.sd.show,.lb.show');
  let vis=false;
  const sync=()=>{if(vis&&!anyModal()&&document.visibilityState==='visible'){v.play().catch(()=>{});}else v.pause();};
  new IntersectionObserver(es=>{vis=es[0].isIntersecting;sync();},{threshold:.25}).observe(v);
  new MutationObserver(sync).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('visibilitychange',sync);});
})();


// red dot on the browser tab icon + "(n)" in the tab title while something is unread
const tabDot=(()=>{let base=null,img=null,on=null;const link=document.querySelector('link[rel="icon"]');const title0=document.title.replace(/^\(\d+\+?\) /,'');
  function draw(show){try{const c=document.createElement('canvas');c.width=c.height=64;const x=c.getContext('2d');
      x.save();x.beginPath();x.arc(32,32,32,0,Math.PI*2);x.clip();x.drawImage(img,0,0,64,64);x.restore();
      if(show){x.beginPath();x.arc(48,16,15,0,Math.PI*2);x.fillStyle='#fff';x.fill();x.beginPath();x.arc(48,16,11.5,0,Math.PI*2);x.fillStyle='#e8173c';x.fill();}
      link.href=c.toDataURL('image/png');}catch(_){if(base)link.href=base;}}
  return function(n,label){n=Number(n)||0;const t=(label||title0);document.title=(n?`(${n>9?'9+':n}) `:'')+t;
    if(!link||on===!!n)return;on=!!n;
    if(!base)base=link.getAttribute('href');
    if(!n&&!img){return;}
    if(img&&img.complete){draw(!!n);return;}
    img=new Image();img.onload=()=>draw(on);img.onerror=()=>{};img.src=base;};
})();
let tabVisitorN=0,tabAdminN=0;const tabSync=()=>tabDot(tabVisitorN+tabAdminN);
// ===== live chat widget =====
(function(){
  const API='chat-api.php', KEY='ka_chat';
  const bubble=$('#kcBubble'),panel=$('#kcPanel'),body=$('#kcBody'),badge=$('#kcBadge'),errEl=$('#kcErr');
  let sess=null,last=0,timer=null,busy=false,mem=null;
  const load=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch(_){return mem}};
  const save=v=>{mem=v;try{v?localStorage.setItem(KEY,JSON.stringify(v)):localStorage.removeItem(KEY)}catch(_){}};
  const isOpen=()=>!panel.hidden;
  const t=ts=>{const d=new Date(ts*1000);return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})+(d.toDateString()!==new Date().toDateString()?' · '+d.toLocaleDateString([],{day:'numeric',month:'short'}):'')};
  async function api(data){
    const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store'});
    let j={};try{j=await r.json()}catch(_){}
    if(!r.ok){const e=new Error(j.error||'Connection problem, please try again.');e.status=r.status;throw e;}
    return j;
  }
  function add(m){
    if(m.id&&body.querySelector(`[data-id="${m.id}"]`))return;
    const bot=m.sender==='bot';const d=document.createElement('div');d.className='kc-msg '+(m.sender==='admin'||bot?'admin':'visitor')+(bot?' kc-auto':'');if(m.id)d.dataset.id=m.id;
    const p=document.createElement('p');p.textContent=m.body;d.appendChild(p);
    const sm=document.createElement('small');sm.textContent=(bot?'Automatic reply · ':m.sender==='admin'?(m.agent||'KeikoArts')+' · ':'')+t(m.created);d.appendChild(sm);
    body.appendChild(d);if(m.id)last=Math.max(last,m.id);
  }
  const scroll=()=>{body.scrollTop=body.scrollHeight};
  function firstUI(){const f=$('#kcFirst');if(f)f.hidden=!!sess;}
  function mode(){firstUI();ctUI();}
  // contact details: so Keiko can reply by email / Discord after the visitor leaves
  const ct=$('#kcContact'),ctOpen=$('#kcCtOpen');let ctSkipped=false;
  function ctUI(){const need=!!sess&&!sess.hasContact;ct.hidden=!(need&&!ctSkipped);ctOpen.hidden=!(need&&ctSkipped);if(sess&&sess.hasContact){ct.hidden=true;ctOpen.hidden=true;}}
  ctOpen.onclick=()=>{ctSkipped=false;ctUI();$('#kcEmail').focus();};
  $('#kcCtSkip').onclick=()=>{ctSkipped=true;ctUI();};
  ct.addEventListener('submit',async e=>{e.preventDefault();const em=$('#kcEmail').value.trim(),dc=$('#kcDc').value.trim();errEl.textContent='';
    if(!em&&!dc){errEl.textContent='Please enter your email or Discord username.';return;}
    try{const j=await api({action:'contact',id:sess.id,token:sess.token,email:em,discord:dc,since:last});sess.hasContact=true;save(sess);ctUI();j.messages.forEach(add);
      const sys=document.createElement('div');sys.className='kc-sys';sys.textContent=em?'Saved ♡ I\'ll also email you when I reply.':'Saved ♡ I\'ll add you on Discord.';body.appendChild(sys);scroll();}
    catch(err){errEl.textContent=err.message;}});
  function setBadge(n){badge.hidden=!n;badge.textContent=n>9?'9+':n;tabVisitorN=Number(n)||0;tabSync();}
  async function poll(){
    if(!sess||busy)return;
    try{const j=await api({action:'poll',id:sess.id,token:sess.token,since:last,open:isOpen()});
      if(j.messages.length){j.messages.forEach(add);if(isOpen())scroll();}
      setBadge(isOpen()?0:j.unread);if(j.has_contact!==undefined){sess.hasContact=!!j.has_contact;save(sess);ctUI();}
    }catch(e){if(e.status===401){save(null);sess=null;mode();}}
  }
  let tick=0;
  function schedule(){clearInterval(timer);if(!sess)return;timer=setInterval(()=>{tick++;if(document.visibilityState==='visible'||tick%4===0)poll();},isOpen()?4000:30000);}   // a background tab still checks every 2 minutes, so the tab dot can appear
  function openChat(){panel.hidden=false;bubble.setAttribute('aria-expanded','true');setBadge(0);poll().then(scroll);schedule();setTimeout(()=>$('#kcInput').focus(),50);}
  function closeChat(){panel.hidden=true;bubble.setAttribute('aria-expanded','false');schedule();bubble.focus();}
  bubble.onclick=()=>isOpen()?closeChat():openChat();
  $('#kcClose').onclick=closeChat;
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&isOpen())closeChat();});
  const input=$('#kcInput');
  input.addEventListener('input',()=>{input.style.height='auto';input.style.height=Math.min(input.scrollHeight,110)+'px';});
  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#kcSend').requestSubmit();}});
  $('#kcSend').addEventListener('submit',async e=>{
    e.preventDefault();const text=input.value.trim();if(!text||busy)return;errEl.textContent='';
    if(!sess){const fe=$('#kcFEmail').value.trim(),fd=$('#kcFDc').value.trim(),fn=$('#kcFName').value.trim();
      if(fn.length<2){errEl.textContent='Please add your name or VTuber name.';$('#kcFName').focus();return;}
      if(!fe&&!fd){errEl.textContent='Please add your email or your Discord username so I can reply even after you leave.';$('#kcFEmail').focus();return;}
      if(fe&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fe)){errEl.textContent='Please check your email address.';$('#kcFEmail').focus();return;}
      if(fd&&!/^@?[a-zA-Z0-9_.]{2,32}(#\d{4})?$/.test(fd)){errEl.textContent='Please check your Discord username (letters, numbers, _ and . only).';$('#kcFDc').focus();return;}}
    busy=true;
    const tmp=document.createElement('div');tmp.className='kc-msg visitor pending';const p=document.createElement('p');p.textContent=text;tmp.appendChild(p);body.appendChild(tmp);scroll();
    input.value='';input.style.height='auto';
    try{
      if(!sess){const j=await api({action:'start',message:text,page:location.pathname,_honey:e.target._honey.value,email:$('#kcFEmail').value.trim(),discord:$('#kcFDc').value.trim(),name:$('#kcFName').value.trim()});
        sess={id:j.id,token:j.token};save(sess);tmp.remove();j.messages.forEach(add);
        sess.hasContact=true;save(sess);firstUI();ctUI();scroll();schedule();}
      else{const j=await api({action:'send',id:sess.id,token:sess.token,message:text,since:last});tmp.remove();j.messages.forEach(add);scroll();}
    }
    catch(err){tmp.remove();input.value=text;errEl.textContent=err.message;if(err.status===401){save(null);sess=null;}}
    busy=false;
  });
  // restore an existing chat on this device
  sess=load();mode();
  if(sess){poll();schedule();}
  window.openChat=openChat;
  if(location.hash==='#chat')setTimeout(openChat,400);   // link in the reply email opens the chat
})();

// admin shortcut on the website
(function(){
  let tok='';try{tok=localStorage.getItem('ka_auth')||''}catch(_){}
  if(!tok||!location.protocol.startsWith('http'))return;
  const pill=$('#adminPill'),cnt=$('#adminCount');
  async function check(){
    try{const r=await fetch('chat-api.php',{method:'POST',headers:{'Content-Type':'application/json','X-Auth':tok},body:JSON.stringify({action:'list',status:'open',_auth:tok}),cache:'no-store'});
      if(r.status===401){pill.hidden=true;try{localStorage.removeItem('ka_auth')}catch(_){}return false;}
      if(!r.ok)return true;const j=await r.json();pill.hidden=false;cnt.hidden=!j.unread_total;cnt.textContent=j.unread_total>9?'9+':j.unread_total;tabAdminN=Number(j.unread_total)||0;tabSync();
    }catch(_){}return true;
  }
  check().then(ok=>{if(ok)setInterval(check,30000);});   // also while the tab is in the background, for the tab dot
})();

// service search
(function(){
  const input=$('#svcSearch'),empty=$('#svcEmpty');if(!input)return;
  const TAGS={ // extra words clients might type
    "VTuber":"vtuber model live2d rig rigging art full body half bust vts avatar",
    "VTuber Packages":"package bundle debut set full debut starter",
    "Background":"background bg room scene stream background",
    "Stream Overlay":"overlay stream screens starting soon brb ending panels layout obs twitch",
    "Custom PFP":"pfp profile picture icon avatar headshot portrait",
    "Emotes":"emote emotes sticker twitch discord animated",
    "Banner":"banner eye banner mouth banner header",
    "VTuber Logo":"logo name lettering text logo brand",
    "PNGTuber":"pngtuber png tuber simple avatar veadotube",
    "VTuber Pet":"pet mascot animal companion",
    "Chibi VTuber":"chibi cute mini sd",
    "Custom Inquiry":"custom inquiry illustration art other request commission"};
  const norm=t=>(t||'').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g,'');
  const cards=[...$$('.services .card')].map(card=>{
    const name=card.querySelector('h3').textContent.trim(),sv=SERVICES[name]||{},d=DETAILS[name]||{};
    return {card,key:norm(name+' '+(TAGS[name]||'')),text:norm([card.querySelector('p')?.textContent,(sv.packages||[]).map(p=>p[0]+' '+p[2]).join(' '),(sv.addons||[]).map(a=>a[0]).join(' '),d.about,(d.includes||[]).join(' ')].join(' '))};
  });
  const has=(hay,w)=>new RegExp('(^|[^a-z0-9])'+w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).test(hay);
  function run(){
    const words=norm(input.value.trim()).split(/\s+/).filter(Boolean);
    let hits=cards.filter(c=>words.every(w=>has(c.key,w)));            // strong: name / tags
    if(!hits.length)hits=cards.filter(c=>words.every(w=>has(c.key+' '+c.text,w))); // fallback: full description
    const show=words.length?new Set(hits):new Set(cards);
    cards.forEach(c=>c.card.classList.toggle('hide-s',!show.has(c)));
    $('.services').classList.toggle('searching',words.length>0);
    empty.hidden=show.size>0;empty.querySelector('span').textContent=input.value.trim();
  }
  input.addEventListener('input',run);
  input.addEventListener('keydown',e=>{if(e.key==='Escape'){input.value='';run();}});
  $('#navSearch').onclick=()=>{$('#services').scrollIntoView({behavior:'smooth',block:'start'});setTimeout(()=>input.focus({preventScroll:true}),450);$('#menu').classList.remove('open');};
})();
// reviews: carousel controls on phones; floating buttons step aside while reviews are at the bottom of the screen
(function(){
  const g=$('.rv-grid'),nav=$('.rv-nav');if(!g||!nav)return;
  const cards=[...g.querySelectorAll('.rv-card')],dots=nav.querySelector('.rv-dots'),prev=nav.querySelector('.rv-prev'),next=nav.querySelector('.rv-next');
  dots.innerHTML='<span class="rv-ctr" aria-live="polite"></span>';const ctr=dots.firstChild;
  const step=()=>cards.length>1?(cards[1].offsetLeft-cards[0].offsetLeft)||g.clientWidth:g.clientWidth;
  const cur=()=>Math.max(0,Math.min(cards.length-1,Math.round(g.scrollLeft/step())));
  const go=i=>{i=Math.max(0,Math.min(cards.length-1,i));g.scrollTo({left:cards[i].offsetLeft-cards[0].offsetLeft,behavior:'smooth'});};
  const fit=i=>{g.style.height=getComputedStyle(nav).display==='none'?'':(cards[i].offsetHeight+6)+'px';};   // phones: carousel as tall as the card shown
  const upd=()=>{const i=cur();ctr.textContent=(i+1)+' / '+cards.length;prev.disabled=i===0;next.disabled=i===cards.length-1;fit(i);};
  addEventListener('resize',()=>fit(cur()),{passive:true});
  let raf=0;g.addEventListener('scroll',()=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(upd);},{passive:true});
  prev.onclick=()=>go(cur()-1);next.onclick=()=>go(cur()+1);
  if('IntersectionObserver' in window){const io=new IntersectionObserver(es=>{if(es[0].isIntersecting){io.disconnect();upd();}},{rootMargin:'400px'});io.observe(g);}else upd();   // measure only when the reviews come near (saves layout work at load)
  if('IntersectionObserver' in window)new IntersectionObserver(es=>es.forEach(e=>document.body.classList.toggle('in-reviews',e.isIntersecting)),{rootMargin:'-85% 0px 0px 0px'}).observe($('#reviews'));
})();
// reviews on wider screens: 8 first, the rest behind "Show all"
(function(){const g=$('.rv-grid'),b=$('#rvMoreBtn');if(!g||!b)return;const n=g.querySelectorAll('.rv-card').length;
  if(n<=8){$('#rvMore').remove();return;}
  b.textContent=`Show all ${n} reviews`;b.onclick=()=>{g.classList.add('all');$('#rvMore').remove();};})();

// slots left per service (SLOTS.per): on the service cards, in the service list and in the order form
const slotTxt=k=>{if(typeof SLOTS==='undefined'||!SLOTS.open||!SLOTS.per||!(k in SLOTS.per))return '';const n=SLOTS.per[k];return n>0?`${n} slot${n===1?'':'s'} left`:'Fully booked';};
(function(){
  $$('.card').forEach(c=>{const h=c.querySelector('h3'),t=h&&slotTxt(h.textContent.trim());if(!t)return;
    const e=document.createElement('span');e.className='slot-left'+(/Fully/.test(t)?' full':'');e.innerHTML='<i aria-hidden="true"></i>'+t;h.after(e);});
  $$('#svcOpts label').forEach(l=>{const inp=document.getElementById(l.htmlFor),t=inp&&slotTxt(inp.value),sm=l.querySelector('small');if(t&&sm)sm.textContent+=' · '+t;});
})();

{const c=$$('#services .card').find(x=>((x.querySelector('h3')||{}).textContent||'').trim()==='VTuber Packages');const m=Math.max(0,...[0,1,2].map(pkgSaving));
  if(c&&m){const pr=c.querySelector('.price'),s=document.createElement('span');s.className='psave';s.textContent=`Debut packages save up to $${m} vs buying separately`;pr&&pr.appendChild(s);}}
// buyer helpers: installments on the cards, "start small", which-package quiz, work in progress (real numbers from the orders)
(function(){
  const fromMove=k=>{const sv=SERVICES[k];if(!sv)return 0;const mv=sv.packages.filter(p=>/Art \+ Rig/.test(p[0])).map(p=>p[1]);return mv.length?Math.min(...mv):sv.from;};
  $$('#services .card').forEach(c=>{const k=(c.querySelector('h3')||{}).textContent;if(!k||!SERVICES[k.trim()]||SERVICES[k.trim()].quote)return;const base=fromMove(k.trim());if(base<150)return;
    const third=Math.ceil(base*(1+TAX)/3*100)/100,pr=c.querySelector('.price');if(!pr)return;const s=document.createElement('span');s.className='pinst';s.textContent=`or 3 payments of ${money2(third)} (incl. PayPal fee)`;pr.appendChild(s);});
  const small=[['Emotes','emotes for your channel'],['PNGTuber','a simple talking avatar'],['Custom PFP','a profile picture of your character']].filter(([k])=>SERVICES[k]);
  $('#startSmallList').innerHTML=small.map(([k,d])=>`<a href="#order" data-order="${esc(k)}"><span>${esc(k)}<small style="display:block;font-weight:400;color:var(--muted);font-size:12.5px">${esc(d)}</small></span><b>from ${money(SERVICES[k].from)}${SERVICES[k].qty?' each':''}</b></a>`).join('');
  const ans={};
  $('#fq').addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;const g=b.parentNode;g.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));ans[g.dataset.q]=b.dataset.v;
    if(!(ans.b&&ans.m&&ans.x))return;
    const vp=n=>{const p=(SERVICES.VTuber.packages.find(x=>x[0]===n)||[])[1];return p?money(p):'';},pk=SERVICES['VTuber Packages'].packages;
    let t,o;
    if(ans.m==='no'){t=`<b>PNGTuber</b> from ${money(SERVICES.PNGTuber.from)}: a talking avatar that switches images when you speak. Easy to start, and you can move to Live2D later.`;o='PNGTuber';}
    else if(ans.x==='yes'&&ans.b!=='low'){const p=ans.b==='high'?pk[pk.length-1]:pk[0];t=`<b>${esc(p[0])}</b> ${money(p[1])}: ${esc(p[2])}. Everything for your debut in one style.`;o='VTuber Packages';}
    else if(ans.b==='low'){t=`<b>PNGTuber</b> from ${money(SERVICES.PNGTuber.from)} fits your budget now. A Live2D model starts at ${vp('Bust · Art + Rig')} (or 3 payments).`;o='PNGTuber';}
    else if(ans.b==='mid'){t=`<b>Live2D VTuber model, bust</b> ${vp('Bust · Art + Rig')} or <b>half body</b> ${vp('Half body · Art + Rig')}: art + rig, ready for VTube Studio.`;o='VTuber';}
    else{t=`<b>Live2D VTuber model, full body</b> ${vp('Full body · Art + Rig')}: art + rig with full-body movement. Add VBridger or extra toggles in the order form.`;o='VTuber';}
    $('#fqRes').innerHTML=t+`<br><a href="#order" data-order="${esc(o)}" class="btn btn-pink">Order this</a>`;$('#fqRes').hidden=false;});
  if(location.protocol.startsWith('http')&&!/[?&]dryrun=1/.test(location.search))fetch('order-api.php?a=queue').then(r=>r.json()).then(j=>{if(!j||!j.ok||!(j.working>0))return;
    const w=$('#workNow');w.innerHTML=`<i aria-hidden="true"></i>Working on ${j.working} commission${j.working>1?'s':''} now`;w.hidden=false;}).catch(()=>{});
})();
// "Chat with us" in the phone menu opens the chat
document.addEventListener('click',e=>{const a=e.target.closest('.menu-chat');if(!a)return;e.preventDefault();$('#menu').classList.remove('open');const b=$('#kcBubble');if(b)b.click();});
// the floating "Order now" button appears once the hero buttons are scrolled away
(function(){if(typeof SEASON==='undefined'||!SEASON.christmas||new Date()>=new Date(SEASON.until))return;document.body.classList.add('xmas');
  const h=document.querySelector('.hero');if(!h||matchMedia('(prefers-reduced-motion:reduce)').matches)return;
  const box=document.createElement('div');box.className='xmas-snow';box.setAttribute('aria-hidden','true');
  const n=innerWidth<700?14:26,cols=['#f7b6cc','#fbd3e0','#e9dcff','#ffd9e6'];let html='';
  for(let i=0;i<n;i++){const r=Math.random;html+=`<i style="left:${(r()*100).toFixed(1)}%;--s:${(4+r()*6).toFixed(1)}px;--c:${cols[i%4]};--d:${(9+r()*9).toFixed(1)}s;--l:-${(r()*18).toFixed(1)}s;--x:${(r()*60-30).toFixed(0)}px"></i>`;}
  box.innerHTML=html;h.prepend(box);})();
(function(){if(!document.body.classList.contains('xmas'))return;
  // Christmas spin wheel: one spin per visitor, prize + claim code for Discord (prizes set by the owner; Keiko applies them by hand)
  const KEY='ka-wheel-2026';
  const GIFTS=['Free emotes','Free Christmas badges','Free source files','Free skeb (surprise-me art)','Free sketch','10% off your next commission'];   // same order as GIFTS in spin-api.php (the server draws the prize)
  const SHORT=['Free emotes','Xmas badges','Source files','Skeb · rare','Free sketch','10% off'];   // Skeb is a rare prize (owner, Nov 2026): the server gives it a small chance
  const N=SHORT.length,slice=r=>r.g;
  const n=GIFTS.length,cols=['#f2628f','#ffd1df','#c9a7ff','#ffd166','#ff8fb1','#efe6ff'],ink=['#fff','#7a2846','#fff','#7a2846','#fff','#7a2846'];
  let res=null;try{res=JSON.parse(localStorage.getItem(KEY)||'null')}catch(_){}
  const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(res))}catch(_){}};
  // spins from before skeb was removed (6 slices): keep the prize the visitor won, move the others to the new slice numbers
  if(res&&res.v===2&&!res.prize&&res.g>=3)res.g+=1;   // spins made while skeb was off (5-prize list)
  if(res&&res.v!==3){if(res.prize)res.g=3;delete res.prize;res.g=Math.max(0,Math.min(n-1,res.g|0));res.v=3;save();}
  const top=document.querySelector('.hero-top');if(!top)return;
  const chip=document.createElement('button');chip.type='button';chip.className='gift-hunt';top.appendChild(chip);
  const label=()=>{chip.innerHTML=res?'<svg class="ic" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><rect x="3.5" y="8" width="17" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M5 12v8h14v-8M12 8v12M12 8c-2-3.5-6-3-5-.5.6 1.4 5 .5 5 .5Zm0 0c2-3.5 6-3 5-.5-.6 1.4-5 .5-5 .5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg> Your prize':'<svg class="ic" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" stroke="currentColor" stroke-width="1.2" opacity=".6"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/></svg><span class="gh-l">Spin the Christmas wheel</span><span class="gh-s">Spin &amp; win</span>';};label();
  // open from links like /?spin=1 (service pages), or once by itself for a new visitor (not during order tests)
  const busy=()=>!!document.querySelector('.modal.show,.gift-win,.lb.show,.sd.show,#tyModal.show,.kc-panel:not([hidden])');
  const q=new URLSearchParams(location.search);
  if(q.get('spin')==='1'){q.delete('spin');history.replaceState(null,'',location.pathname+(q.toString()?'?'+q:'')+location.hash);setTimeout(()=>{if(!busy())chip.click();},600);}
  else if(false){   // automatic pop-up switched off (UX review, Nov 2026): the button in the hero and /?spin=1 still open it
let seen=false;try{seen=!!localStorage.getItem(KEY+'-seen')}catch(_){seen=true}
    if(!seen){let fired=false;const fire=()=>{if(fired||res||busy())return;fired=true;try{localStorage.setItem(KEY+'-seen','1')}catch(_){}chip.click();removeEventListener('scroll',onScroll);};
      const t0=Date.now();const onScroll=()=>{if(scrollY>innerHeight*2.5&&Date.now()-t0>20000)fire();};addEventListener('scroll',onScroll,{passive:true});setTimeout(fire,35000);}}   // not before 20 s of browsing, so it never interrupts the first look
  const confetti=()=>{if(matchMedia('(prefers-reduced-motion:reduce)').matches)return;const cs=['#f2628f','#ff8fb1','#c9a7ff','#ffd166','#9be7c4'];
    for(let i=0;i<60;i++){const c=document.createElement('i');c.className='confetti';c.style.left=(Math.random()*100)+'vw';c.style.background=cs[i%5];
      c.style.setProperty('--d',(2+Math.random()*2).toFixed(2)+'s');c.style.setProperty('--x',(Math.random()*160-80).toFixed(0)+'px');c.style.setProperty('--r',(Math.random()*720).toFixed(0)+'deg');c.style.animationDelay=(Math.random()*.6).toFixed(2)+'s';
      document.body.appendChild(c);setTimeout(()=>c.remove(),4800);}};
  const wheelSVG=()=>{let g='';const R=100,seg=360/N,rad=d=>(d-90)*Math.PI/180;
    for(let i=0;i<N;i++){const a0=i*seg,a1=a0+seg,x0=R+R*Math.cos(rad(a0)),y0=R+R*Math.sin(rad(a0)),x1=R+R*Math.cos(rad(a1)),y1=R+R*Math.sin(rad(a1)),m=a0+seg/2;
      g+=`<path d="M${R} ${R} L${x0.toFixed(2)} ${y0.toFixed(2)} A${R} ${R} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z" fill="${cols[i]}" stroke="#fff" stroke-width="2"/>`+
         `<text x="${R+21}" y="${R+3.5}" transform="rotate(${m-90} ${R} ${R})" font-size="10" font-weight="600" font-family="Poppins,sans-serif" fill="${ink[i]}">${SHORT[i]}</text>`;}
    return `<svg viewBox="0 0 200 200" class="wh-svg" aria-hidden="true">${g}<circle cx="100" cy="100" r="16" fill="#fff" stroke="#fbd3e0" stroke-width="3"/><text x="100" y="105" text-anchor="middle" font-size="14">🎁</text></svg>`;};
  const result=(w)=>{w.querySelector('h3').textContent=GIFTS[res.g]+'!';
    w.querySelector('.gw-msg').innerHTML='Your claim code: <b class="gw-code">'+res.c+'</b><small>Send this code (or a screenshot) to Keiko on Discord to claim it with your next commission. One prize per person, valid until 6 Jan 2027.</small>';
    w.querySelector('.btns').innerHTML='<a class="btn btn-pink" href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener">Claim on Discord</a><button class="btn btn-ghost" type="button">Close</button>';
    w.querySelector('.btns button').onclick=()=>w.remove();};
  chip.onclick=()=>{const w=document.createElement('div');w.className='gift-win';
    w.innerHTML='<div role="dialog" aria-modal="true" aria-label="Christmas spin wheel"><h3>Christmas spin wheel</h3><p class="gw-msg">One free spin per person. Every slice is a prize from Keiko ♡ (Skeb is the rare one)</p><div class="wh"><div class="wh-pin"></div><div class="wh-rot">'+wheelSVG()+'</div></div><div class="btns"><button class="btn btn-pink wh-go" type="button">Spin!</button><button class="btn btn-ghost wh-x" type="button">Close</button></div></div>';
    document.body.appendChild(w);w.addEventListener('click',e=>{if(e.target===w)w.remove();});w.querySelector('.wh-x').onclick=()=>w.remove();
    const esc=e=>{if(e.key==='Escape'){w.remove();document.removeEventListener('keydown',esc);chip.focus();}};document.addEventListener('keydown',esc);setTimeout(()=>{const f=w.querySelector('.wh-go:not([disabled]),.btns a,.btns button');if(f)f.focus();},50);
    const rot=w.querySelector('.wh-rot'),seg=360/N;
    if(res){rot.style.transform=`rotate(${360-(slice(res)+.5)*seg}deg)`;result(w);return;}
    w.querySelector('.wh-go').onclick=async e=>{e.target.disabled=true;
      const calm=matchMedia('(prefers-reduced-motion:reduce)').matches;
      if(!calm){rot.style.transition='transform 1.2s ease-in';rot.style.transform='rotate(720deg)';}   // starts turning while the server draws
      let r=null;try{const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),6000);
        const q=await fetch('spin-api.php',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',signal:ctl.signal});clearTimeout(t);
        const j=await q.json();if(j&&j.ok&&Number.isInteger(j.g)&&j.g>=0&&j.g<n&&/^XMAS-[A-Z0-9]{5}$/.test(j.c))r={g:j.g,c:j.c,v:3};}catch(_){}
      if(!r){rot.style.transition='none';rot.style.transform='rotate(0deg)';e.target.disabled=false;
        w.querySelector('.gw-msg').textContent='The wheel is stuck for a moment. Please try again in a minute ♡';return;}
      res=r;save();const jit=(Math.random()-.5)*seg*.6;
      requestAnimationFrame(()=>{rot.style.transition=calm?'none':'transform 4.2s cubic-bezier(.17,.67,.12,1)';
        rot.style.transform=`rotate(${(calm?0:720+360*5)+360-(slice(res)+.5)*seg+jit}deg)`;});
      setTimeout(()=>{result(w);label();confetti();KA_STAT('spin');},calm?50:4300);};};
})();
(function(){if(navigator.webdriver||matchMedia('(prefers-reduced-motion:reduce)').matches||!('IntersectionObserver' in window))return;   // reveal on scroll (skipped for automated tests)
  const els=[...document.querySelectorAll('.sec-head,.works .work,#services .card,.rv-grid,.step,.member,#faq details,.fc-box')].filter(e=>e.getBoundingClientRect().top>innerHeight);
  if(!els.length)return;document.documentElement.classList.add('rv-on');
  const groups=new Map();els.forEach(e=>{const k=e.parentElement;const i=groups.get(k)||0;groups.set(k,i+1);e.style.setProperty('--rd',Math.min(i,6)*.07+'s');e.classList.add('rv');
    if(e.matches('#services .card,.member,.fc-box'))e.classList.add('rv-zoom');else if(e.matches('.works .work'))e.classList.add(i%2?'rv-right':'rv-left');});
  const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target);}}),{rootMargin:'0px 0px -8% 0px'});
  els.forEach(e=>io.observe(e));})();
(function(){if(matchMedia('(prefers-reduced-motion:reduce)').matches)return;   // hero sparkles, parallax art, card tilt
  const h=document.querySelector('.hero');if(h){const pos=[[54,12,14,4.6,0],[93,18,18,5.4,1.2],[61,78,12,4.2,2.1],[97,72,16,5.8,.6],[48,46,10,4.8,3],[80,6,12,5,2.6]];
    h.insertAdjacentHTML('beforeend',pos.map(([x,y,f,d,de],i)=>`<span class="hero-spark" aria-hidden="true" style="left:${x}%;top:${y}%;--fs:${f}px;--du:${d}s;--de:${de}s;color:${i%2?'#c9a7ff':'#f2628f'}">✦</span>`).join(''));}
  const art=null;if(art){let tk=false;addEventListener('scroll',()=>{if(tk)return;tk=true;requestAnimationFrame(()=>{const y=scrollY;if(y<innerHeight*1.2)art.style.transform=`translateY(${(y*.08).toFixed(1)}px)`;tk=false;});},{passive:true});}
  if(false)document.querySelectorAll('#services .card').forEach(c=>{   // card tilt off (design review, Nov 2026)
    c.addEventListener('pointermove',e=>{const r=c.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;c.style.transform=`perspective(900px) rotateY(${(x*6).toFixed(2)}deg) rotateX(${(-y*6).toFixed(2)}deg) translateY(-3px)`;});
    c.addEventListener('pointerleave',()=>{c.style.transform='';});});
})();
(function(){const hd=document.querySelector('header');if(!hd)return;const calm=matchMedia('(prefers-reduced-motion:reduce)');
  hd.addEventListener('pointerdown',e=>{const el=e.target.closest('a,button');if(!el||!hd.contains(el))return;
    el.classList.add('tap');setTimeout(()=>el.classList.remove('tap'),160);if(calm.matches)return;
    const ch=document.body.classList.contains('xmas')?'\u2744\uFE0E':'\u2726',cols=['#f2628f','#ff8fb1','#c9a7ff'];
    for(let i=0;i<7;i++){const s=document.createElement('span'),a=(Math.PI*2*i/7)+Math.random()*.5,d=18+Math.random()*16;
      s.className='tap-spark';s.textContent=ch;s.style.color=cols[i%3];s.style.fontSize=(9+Math.random()*6)+'px';
      s.style.setProperty('--x0',(e.clientX-5)+'px');s.style.setProperty('--y0',(e.clientY-6)+'px');
      s.style.setProperty('--dx',(Math.cos(a)*d).toFixed(1)+'px');s.style.setProperty('--dy',(Math.sin(a)*d).toFixed(1)+'px');s.style.setProperty('--r',(Math.random()*120-60).toFixed(0)+'deg');
      document.body.appendChild(s);setTimeout(()=>s.remove(),650);}
  },{passive:true});})();
(function(){if(typeof SLOTS==='undefined'||!SLOTS.open||!SLOTS.start)return;   // "start now" note (edit SLOTS.start)
  const p=$('#startPill'),c=$('#cStart');if(p){p.innerHTML='<svg class="ic" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M13 2 5 14h6l-1 8 8-12h-6l1-8Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>'+esc(SLOTS.start);p.hidden=false;}if(c){c.textContent=SLOTS.start+'.';c.hidden=false;}})();
(function(){const b=$('#slotBadge');if(b&&typeof SLOTS!=='undefined'){b.textContent=SLOTS.text;b.className='slot-badge '+(SLOTS.open?'open':'closed');
  const xm=typeof SEASON!=='undefined'&&SEASON.christmas&&SEASON.orderBy&&SLOTS.open&&new Date()<new Date(SEASON.until)&&new Date()<=new Date(SEASON.orderBy+'T23:59:59+07:00');
  const st=SLOTS.open?'<span class="sb-main sb-cute"><img class="sb-emote" src="images/contact-emote.webp" alt="" width="244" height="258" decoding="async"><span class="sb-txt"><span class="sb-lbl">Commissions</span><b class="sb-open"><i class="sb-live" aria-hidden="true"></i>open</b></span></span>':'';
  if(st){b.innerHTML=st;b.classList.add('sb-split');}
  // hero badge shows only "Commissions open" (owner, Nov 2026); the Christmas deadline stays in the order form
  }})();
(function(){const t=[...document.querySelectorAll('#start,footer')];if(!t.length||!('IntersectionObserver' in window))return;const on=new Set();const io=new IntersectionObserver(es=>{es.forEach(e=>e.isIntersecting?on.add(e.target):on.delete(e.target));document.body.classList.toggle('fab-off',on.size>0);});t.forEach(x=>io.observe(x));})();
(function(){const hb=document.querySelector('.hero .btns');if(!hb||!('IntersectionObserver' in window)){document.body.classList.add('past-hero');return;}
  new IntersectionObserver(es=>es.forEach(e=>document.body.classList.toggle('past-hero',!e.isIntersecting&&e.boundingClientRect.top<0))).observe(hb);})();
// services: 6 main ones, the rest behind "View all services"
(function(){const b=$('#svcAll'),g=$('.services');if(!b||!g)return;
  const n=g.querySelectorAll('.card').length;b.textContent='View all services ('+n+')';
  b.onclick=()=>{const open=g.classList.toggle('all');b.setAttribute('aria-expanded',open);b.textContent=open?'Show fewer services':'View all services ('+n+')';
    if(!open)$('#services').scrollIntoView({behavior:'smooth',block:'start'});};})();
// open Terms when a TOS link is used
document.addEventListener('click',e=>{const a=e.target.closest('a[href="#tos"],a[href="#privacy"]');if(a){const d=$('.tos-box');if(d)d.open=true;}});
if(/^#(tos|privacy)$/.test(location.hash)){const d=$('.tos-box');if(d){d.open=true;setTimeout(()=>document.querySelector(location.hash).scrollIntoView(),50);}}
// nav
const links=$$('.menu a[href^="#"]');
addEventListener('scroll',()=>{let cur='home';links.forEach(l=>{const s=document.querySelector(l.getAttribute('href'));if(s&&s.getBoundingClientRect().top<120)cur=s.id});
  links.forEach(l=>l.classList.toggle('active',l.getAttribute('href')==='#'+cur))},{passive:true});
$$('.menu a').forEach(l=>l.addEventListener('click',()=>$('#menu').classList.remove('open')));
const TY0={};['tyTitle','tyLead','tyPayT','tyPaySm','tyDcT','tyDcS','tyNote','tyRefLbl','tyDiscord','tyKofiRef'].forEach(k=>TY0[k]=$('#'+k).textContent);
function closeTy(){try{sessionStorage.removeItem('ka_ty');}catch(_){}const ty=$('#tyModal');ty.classList.remove('show');ty.setAttribute('aria-hidden','true');document.body.style.overflow='';
  if(/[?&](sent|paid|rid)=/.test(location.search)){const q=new URLSearchParams(location.search);['sent','paid','rid'].forEach(k=>q.delete(k));const qs=q.toString();history.replaceState(null,'',location.pathname+(qs?'?'+qs:''));}}
$$('[data-tyclose]').forEach(b=>b.onclick=closeTy);$('#tyModal').addEventListener('click',e=>{if(e.target.id==='tyModal')closeTy();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#tyModal').classList.contains('show'))closeTy();});
function showThanks(last){
  try{if(last&&last.id)sessionStorage.setItem('ka_ty',last.id);}catch(_){}
  const ty=$('#tyModal');
  Object.entries(TY0).forEach(([k,v])=>$('#'+k).textContent=v);
  ['#tyRef','#tySummary','#tyPay','#tyInv','#invActions','#tyTrack'].forEach(q=>$(q).hidden=true);
  if(last&&last.track&&/^https:\/\/keikoartist\.com\/order-api\.php\?a=track/.test(last.track)||last&&last.track&&/^http:\/\/(localhost|127\.0\.0\.1)/.test(last.track)){$('#tyTrack').href=last.track;$('#tyTrack').hidden=false;}
  if(last&&last.inv){$('#invActions').hidden=false;$('#invCopy').hidden=!last.payUrl;$('#invCopy').textContent='🔗 Copy payment link';
    $('#invCopy').onclick=async()=>{try{await navigator.clipboard.writeText(last.payUrl);$('#invCopy').textContent='Copied ✓';}catch(_){prompt('Your payment link',last.payUrl);}};
    $('#invSave').onclick=()=>window.print();}
  $('#tyWarn').textContent=(last&&last.warn)||'';$('#tyWarn').hidden=!(last&&last.warn);
  if(last&&!last.inv)$('#tyNote').textContent='Questions? Just email me:';
  if(last){$('#tyRefId').textContent=last.id;$('#tyRef').hidden=false;
    $('#tySummary').innerHTML=last.rows.filter(r=>!(r[0]==='Discord'&&r[1]==='-')).map(([a,b])=>`<div><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');$('#tySummary').hidden=false;}
  const payNow=last&&last.payUrl&&last.due>0;
  if(payNow){$('#tyPay').hidden=false;$('#tyPayAmt').textContent=money2(last.due);$('#tyPayInfo').textContent=planLabel(last.plan)+' · Request '+last.id;$('#tyPayBtn').href=last.payUrl;$('#tyPayLabel').textContent='Pay '+money2(last.due)+' with PayPal';}
  const inv=last&&last.inv;
  if(inv){
    const custom=inv.custom!==undefined?!!inv.custom:true;
    const lines=inv.lines||[[`Custom commission (${inv.usage||'Personal'} use)`,inv.sub],['PayPal fee (13%)',inv.tax]];
    const total=+inv.total||0, due=last.due!=null?+last.due:total, partial=!custom&&due<total;
    const dl=inv.deadline?new Date(inv.deadline+'T00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'';
    const meta=dl?'Deadline '+dl:'';
    const [first,...rest]=custom?[lines[0]]:lines;
    const amt=a=>a?money2(a):'Free';
    $('#tyTitle').textContent='Your invoice ♡';
    $('#tyLead').textContent=payNow?(partial?`Thank you for your order! Pay ${money2(due)} now (${planLabel(inv.plan||last.plan)}) with PayPal to secure your slot ♡`:'Thank you for your order! Pay your invoice with PayPal to confirm it ♡')
      :"Thank you for your order! Here's your invoice. Message me on Discord with your Order ID and I'll send you a PayPal link ♡";
    $('#tyRef').hidden=true;$('#tySummary').hidden=true;
    $('#tyInv').innerHTML=`<div class="inv">
      <div class="inv-head"><div><b>KeikoArts</b><small>Illustration &amp; Live2D Studio<br>keikoartist.com</small></div><span class="inv-tag">INVOICE</span></div>
      <div class="inv-meta"><div><small>Order ID</small><b>${esc(last.id)}</b></div><div><small>Date</small><b>${esc(inv.date)}</b></div><div><small>Billed to</small><b>${esc(inv.name)}</b>${inv.contact?`<span>${esc(inv.contact)}</span>`:''}</div></div>
      <table class="inv-t"><thead><tr><th>Description</th><th>Amount</th></tr></thead>
      <tbody><tr><td>${esc(first[0])}${meta?`<small>${esc(meta)}</small>`:''}${inv.brief?`<small>“${esc(inv.brief)}${inv.brief.length>=140?'…':''}”</small>`:''}</td><td>${amt(first[1])}</td></tr>${rest.map(([l,a])=>`<tr><td>${esc(l)}</td><td>${amt(a)}</td></tr>`).join('')}</tbody>
      <tfoot>${custom?`<tr><td>Subtotal</td><td>${money2(lines[0][1])}</td></tr><tr><td>PayPal fee (13%)</td><td>${money2(lines[1]?lines[1][1]:0)}</td></tr><tr class="grand"><td>Total due (USD)</td><td>${money2(total)}</td></tr>`
        :partial?`<tr><td>Total</td><td>${money2(total)}</td></tr><tr class="grand"><td>Pay now · ${esc(planLabel(inv.plan||last.plan))}</td><td>${money2(due)}</td></tr>`
        :`<tr class="grand"><td>Total due (USD)</td><td>${money2(total)}</td></tr>`}</tfoot></table>
      ${last.payUrl&&due>0?`<p class="print-only pay-link">Pay ${money2(due)} online with PayPal: <a href="${esc(last.payUrl)}">${esc(last.payUrl)}</a></p>`:''}
    </div>`;$('#tyInv').hidden=false;
    if(payNow){$('#tyPayT').textContent=partial?'Pay now to secure your slot':'Pay your invoice';$('#tyPayInfo').textContent=(custom?'Total incl. 13% PayPal fee':partial?planLabel(inv.plan||last.plan):'Full payment')+' · '+last.id;$('#tyPayAmt').textContent=money2(due);$('#tyPayLabel').textContent='Pay '+money2(due)+' with PayPal';
      $('#tyPaySm').textContent="Secure checkout on PayPal (card or PayPal balance). Your slot is secured as soon as you pay. Full refund if I can't take your order.";$('#tyKofiRef').textContent='Order ID';
      $('#tyDcT').textContent='Questions about your order?';$('#tyDcS').textContent='Message me on Discord with your Order ID.';}
    else{$('#tyDcS').textContent='Send me your Order ID so I can send your PayPal link.';}
    $('#tyNote').textContent=inv.emailed?'A copy of this invoice was sent to your email (check Spam). Other ways to reach me:':'Other ways to reach me:';
  }
  const steps=inv?(payNow?[['Pay with PayPal','PayPal emails you a receipt.'],['I review your order',"I confirm within 6 hours. Full refund if I can't take it."],['Work starts',inv.custom===false&&last.due<inv.total?'I send progress updates; the rest is paid later as agreed ♡':'I send progress updates until your art is done ♡']]
      :[['Message me on Discord','Send your Order ID. I reply within 6 hours.'],['Pay your invoice','I send you a PayPal link for '+money2(inv.total)+'.'],['Work starts','I send progress updates until your art is done ♡']])
    :payNow?[['Pay with PayPal','Secure your slot now. PayPal emails you a receipt.'],['Work starts','Done within 3 weeks. Follow every stage with the tracking link in your email.'],['Questions?','Message me on Discord with your Order ID.']]
    :[['I check your idea & price','Within 6 hours (WIB). If I have questions, I email you.'],['Get your invoice','Once we agree on the price, I email your invoice with a one-click PayPal link. Please check Spam too.'],['Pay & start','Your slot is secured and I start working ♡']];
  $('#tySteps').innerHTML=steps.map(([a,b])=>`<li><b>${a}</b><span>${b}</span></li>`).join('');
  ty.classList.add('show');ty.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';ty.scrollTop=0;
  $('#tyDiscord').onclick=async()=>{const id=last&&last.id;if(id){try{await navigator.clipboard.writeText(id);$('#tyDiscord').textContent='Copied '+id+' ✓ Opening…';}catch(_){}}window.open('https://discord.gg/FbgWxMPjf','_blank','noopener');};
}
if(location.search.includes('sent=1')){let last=null;try{last=JSON.parse(sessionStorage.getItem('ka_last')||'null');if(!(last&&last.inv))sessionStorage.removeItem('ka_last');}catch(_){}showThanks(last);}
if(/[?&]paid=1/.test(location.search)){
  const ty=$('#tyModal'),rid=(location.search.match(/[?&]rid=([\w-]+)/)||[])[1]||'';
  $('#tyTitle').textContent='Payment sent! ♡';
  $('#tyLead').textContent="Thank you! PayPal will email you a receipt. I'll confirm your payment and slot on Discord within 6 hours.";
  if(rid){$('#tyRefId').textContent=rid;$('#tyRef').hidden=false;if(/^INV-/.test(rid))$('#tyRefLbl').textContent='Order ID';}
  try{const l=JSON.parse(sessionStorage.getItem('ka_last')||'null');if(l&&l.id===rid)sessionStorage.removeItem('ka_last');}catch(_){}
  dropInvoice(rid);
  $('#tySteps').innerHTML=[['Chat on Discord','Send me your Order ID so I can match your payment.'],['Work starts','I start working and send progress updates on Discord.']].map(([a,b])=>`<li><b>${a}</b><span>${b}</span></li>`).join('');
  ty.classList.add('show');ty.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
  $('#tyDiscord').onclick=async()=>{if(rid){try{await navigator.clipboard.writeText(rid)}catch(_){}}window.open('https://discord.gg/FbgWxMPjf','_blank','noopener');};
}
{const m=(navigator.userAgent||'').match(/Instagram|FBAN|FBAV|FB_IAB|musical_ly|BytedanceWebview|TikTok|Line\/|Snapchat/i);
  if(m){const k=m[0],app=/insta/i.test(k)?'Instagram':/^FB/i.test(k)?'Facebook':/musical|bytedance|tiktok/i.test(k)?'TikTok':/line/i.test(k)?'LINE':'Snapchat';
    const n=$('#iabNote');n.hidden=false;n.querySelector('b').textContent=app;
    n.querySelector('button').onclick=async e=>{try{await navigator.clipboard.writeText('https://keikoartist.com/');e.target.textContent='Copied ✓';}catch(_){prompt('Copy this link and open it in Chrome or Safari','https://keikoartist.com/');}};}}
if(location.hash==='#order')openOrder();
{const q=new URLSearchParams(location.search);if(q.has('order')){const sv=q.get('order');q.delete('order');history.replaceState(null,'',location.pathname+(q.toString()?'?'+q:'')+location.hash);openOrder(SERVICES[sv]?sv:undefined);}}
let reopened=false;
if(!/[?&](sent|paid)=1/.test(location.search)){
  let t=null,o=null,y=0;try{t=sessionStorage.getItem('ka_ty');o=sessionStorage.getItem('ka_open');y=+sessionStorage.getItem('ka_open_y')||0;}catch(_){}
  const v=t&&readInvoice();
  if(v&&v.id===t){showThanks(v);reopened=true;}
  else if(o==='__list'){openOrder();reopened=true;}
  else if(o&&SERVICES[o]){openOrder(o);reopened=true;if(y)setTimeout(()=>{modal.scrollTop=y;},60);}
}
{const v=!reopened&&!/[?&](sent|paid)=1/.test(location.search)&&readInvoice();
  const showBar=()=>{if(document.querySelector('.inv-bar'))return;let off=false;try{off=sessionStorage.getItem('ka_inv_off')===v.id;}catch(_){}if(off)return;
    const bar=document.createElement('div');bar.className='resume inv-bar';bar.setAttribute('role','status');
    bar.innerHTML=`<span>Unpaid invoice <b>${esc(v.id)}</b> · ${money2(v.due)}</span><a class="btn btn-paypal" href="${esc(v.payUrl)}" target="_blank" rel="noopener">Pay now</a><button type="button" class="btn btn-ghost">View</button><button type="button" class="x" aria-label="Dismiss">✕</button>`;
    bar.querySelector('.btn-ghost').onclick=()=>{bar.remove();showThanks(v);};
    bar.querySelector('.x').onclick=()=>{bar.remove();try{sessionStorage.setItem('ka_inv_off',v.id);}catch(_){}};
    if(document.querySelector('.resume:not(.inv-bar)'))bar.style.bottom='74px';
    document.body.appendChild(bar);};
  if(v){
    if(v.key&&location.protocol.startsWith('http')){const fd=new FormData();fd.append('id',v.id);fd.append('key',v.key);
      xhr('order-api.php?a=status',fd,null,15000).then(r=>{const j=r.j;
        if(r.status===404||(r.status===200&&j&&j.ok&&(j.paid>0||['paid','in_progress','done','cancelled'].includes(j.status))))dropInvoice(v.id);else showBar();});}
    else showBar();
  }}
addEventListener('pageshow',()=>setBusy(false));
{const d=new Date(),z=n=>String(n).padStart(2,'0');$('#fDeadline').min=d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate());}
if(location.protocol.startsWith('http'))$('#fNext').value=location.origin+'/?sent=1';
