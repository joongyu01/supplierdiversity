/* Opens official current-status channels; opening a link is never a validity decision. */
(()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let sources,opener,request=0;
 const dialog=document.createElement('dialog');dialog.id='verification-dialog';dialog.setAttribute('aria-label','사업장 현재 상태 확인');document.body.append(dialog);
 async function show(button){
  const current=++request;opener=button;const code=button.dataset.verify.replace(/\D/g,''),name=button.dataset.name||'',mask=Number(button.dataset.mask||0);
  dialog.innerHTML='<button class="dialog-close" aria-label="현재 상태 확인 닫기">×</button><p role="status">공식 조회 경로를 준비합니다.</p>';dialog.querySelector('button').onclick=()=>dialog.close();if(!dialog.open)dialog.showModal();
  try{
   sources ||= await fetch('./data/verification-sources.json').then(r=>{if(!r.ok)throw Error('load');return r.json();});
   if(current!==request||!dialog.open)return;
   dialog.innerHTML=`<button class="dialog-close" aria-label="현재 상태 확인 닫기">×</button><p class="eyebrow">OFFICIAL STATUS CHECK</p><h2>${esc(name||'사업장')} · 현재 상태 확인</h2><div class="verify-identity"><span>사업자번호 <strong>${esc(code||'미확인')}</strong></span>${/^\d{10}$/.test(code)?'<button class="secondary" id="copy-bizno">번호 복사</button>':''}</div><p class="verify-note">아래 버튼으로 공식 서비스에서 지금 조회하세요. 로그인 또는 확인서 번호가 필요할 수 있습니다. 이 화면은 인증 유효 여부를 자동 판정하지 않습니다.</p><p id="verify-message" role="status"></p><div class="verify-sources">${sources.map((s,i)=>`<section class="verify-source${mask&(1<<i)?' listed':''}"><h3>${esc(s.label)} ${mask&(1<<i)?'<small>명단 기록 있음</small>':''}</h3><p>${esc(s.help)}</p><a class="secondary" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.service)} ↗</a><a href="./cancellations.html?type=${s.key}">변경 공고 확인 →</a></section>`).join('')}</div>`;
   dialog.querySelector('.dialog-close').onclick=()=>dialog.close();
   dialog.querySelector('#copy-bizno')?.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(code);dialog.querySelector('#verify-message').textContent='사업자번호를 복사했습니다. 공식 조회 화면에 붙여넣으세요.';}catch{dialog.querySelector('#verify-message').textContent='사업자번호 '+code+'를 직접 복사해 주세요.';}});
  }catch{if(current!==request||!dialog.open)return;dialog.innerHTML='<button class="dialog-close" aria-label="닫기">×</button><p>조회 경로를 받지 못했습니다. 닫고 다시 눌러주세요.</p>';dialog.querySelector('button').onclick=()=>dialog.close();}
 }
 dialog.addEventListener('close',()=>opener?.focus());document.addEventListener('click',e=>{const b=e.target.closest('[data-verify]');if(b)show(b);});
})();
