'use strict';
const labels={cancellation_notice:'취소 관련 · 원문 확인',surrender_notice:'반납 관련 · 원문 확인',prior_notice:'청문·사전통지 · 취소 확정 아님',preliminary_enterprise:'예비사회적기업 관련',other_change:'기타 변경',status_update:'현황자료 · 취소 첨부 확인'};
const types={sme:'중소기업',women:'여성기업',disabled:'장애인기업',startup:'창업기업',severe:'중증장애인생산품 생산시설',standard:'장애인표준사업장',social:'사회적기업',cooperative:'사회적협동조합'};
const allowed=new Set(['www.moel.go.kr','www.mss.go.kr','www.kead.or.kr','www.goods.go.kr','www.coop.go.kr','www.smpp.go.kr','cert.k-startup.go.kr','www.seis.or.kr']);
let notices=[],sourceReports=[],official=[],pending=2;
const $=id=>document.getElementById(id);
function link(label,url){const parsed=new URL(url);if(parsed.protocol!=='https:'||!allowed.has(parsed.hostname)||parsed.username||parsed.port)throw Error('출처 URL 오류');const a=document.createElement('a');a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function renderNotices(){
 const q=$('query').value.trim().toLowerCase(),kind=$('kind').value,type=$('enterprise-type').value;
 const selected=notices.filter(n=>(!type||n.enterpriseTypes.includes(type))&&(!kind||n.kind===kind)&&(!q||`${n.title} ${n.sourceOffice}`.toLowerCase().includes(q))).sort((a,b)=>b.publishedAt.localeCompare(a.publishedAt));
 $('count').textContent=`${pending?'지금까지 받은 ':''}공고 ${selected.length}건 (기업 수와 다릅니다)`;
 $('notices').replaceChildren();
 for(const n of selected){const a=document.createElement('article'),h=document.createElement('h2'),meta=document.createElement('small'),files=document.createElement('ul');h.append(link(n.title,n.url));meta.textContent=`${n.publishedAt} · ${n.enterpriseTypes.map(t=>types[t]).join(' / ')} · ${n.sourceOffice} · ${labels[n.kind]||n.kind}`;
 for(const f of n.attachments||[]){const li=document.createElement('li');li.append(link(f.name,f.url));files.append(li);}a.append(h,meta,files);$('notices').append(a);}
 if(!selected.length){const p=document.createElement('p');p.className='offer-empty';p.textContent=pending?'공고를 받는 대로 표시합니다.':type==='cooperative'?'사회적협동조합은 소관 인가부처별 공고 수집이 아직 연결되지 않았습니다. 아래 공식 설립현황과 인가부처에서 확인하세요.':'현재 수집 범위에서 일치하는 공고가 없습니다. 취소 이력이 없거나 현재 유효하다는 뜻은 아닙니다.';$('notices').append(p);}
 const target=official.find(s=>s.key===type);$('official-notice-route').replaceChildren();if(target){const p=document.createElement('p');p.textContent=target.help;$('official-notice-route').append(link(target.service+' ↗',target.url),p);}
 $('source-report').replaceChildren();for(const s of sourceReports.filter(s=>!type||s.types.includes(type))){const p=document.createElement('p');p.textContent=`${s.name} · ${s.status==='ok'?'확인':'일부 확인 실패'} · ${s.scope} · 마지막 성공 ${s.lastSuccessfulScanAt?new Date(s.lastSuccessfulScanAt).toLocaleString('ko-KR'):'미확인'}`;if(s.url)p.append(' ',link('공식 게시판 ↗',s.url));$('source-report').append(p);}
 const error=sourceReports.some(s=>s.status==='error');$('status').textContent=pending?'공고 자료를 가져오는 중입니다. 검색 조건을 먼저 선택할 수 있습니다.':error?'일부 공식 게시판 확인에 실패했습니다. 이전 자료를 유지하며 수집 범위에서 실패한 출처를 확인할 수 있습니다.':'출처별 확인일과 수집 범위는 아래에서 확인하세요. 전국의 모든 취소 공고를 수집한 것은 아닙니다.';
 const stale=sourceReports.some(s=>s.lastSuccessfulScanAt&&Date.now()-Date.parse(s.lastSuccessfulScanAt)>48*3600*1000);$('freshness').hidden=!stale;$('freshness').textContent='일부 출처는 마지막 수집 성공 후 48시간이 지났습니다. 공식 게시판에서 최근 공고를 확인하세요.';
 const params=new URLSearchParams();if(type)params.set('type',type);if(q)params.set('q',$('query').value);history.replaceState(null,'',location.pathname+(params.size?'?'+params:''));
}
$('enterprise-type').innerHTML='<option value="">전체 기업 유형</option>'+Object.entries(types).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
const params=new URLSearchParams(location.search);if(types[params.get('type')])$('enterprise-type').value=params.get('type');$('query').value=params.get('q')||'';
for(const id of ['query','kind','enterprise-type'])$(id).addEventListener('input',renderNotices);
fetch('./data/verification-sources.json').then(r=>r.json()).then(d=>{official=d;renderNotices();}).catch(()=>{});
for(const [file,social] of [['cancellation-notices.json',true],['policy-notices.json',false]])fetch('./data/'+file,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('load');return r.json();}).then(d=>{
 if(!Array.isArray(d.notices))throw Error('schema');notices.push(...d.notices.map(n=>({...n,enterpriseTypes:n.enterpriseTypes||['social']})));
 if(social)sourceReports.push({name:'고용노동부 관서',types:['social'],status:'ok',scope:`${d.officeCount}개 관서 · ${d.since} 이후`,lastSuccessfulScanAt:d.lastSuccessfulScanAt});else sourceReports.push(...d.sources);
}).catch(()=>sourceReports.push({name:social?'고용노동부 관서':'추가 유형 공고',types:social?['social']:Object.keys(types),status:'error',scope:'자료 로딩 실패'})).finally(()=>{pending--;renderNotices();});
renderNotices();
