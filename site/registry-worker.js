'use strict';
let rows=[], manifest,complete=false,lastSearch;
const bitCount=n=>{let c=0;for(;n;n&=n-1)c++;return c;};
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s\-]/g,'');
onmessage=async({data:d})=>{
  try{
    if(d.action==='load'){
      const response=await fetch('./data/registry/manifest.json');if(!response.ok)throw Error('명단 안내 파일 오류');
      manifest=await response.json();let done=0;postMessage({action:'ready',manifest});
      const parts=new Array(manifest.indexParts);
      for(let i=0;i<manifest.indexParts;i+=4){
        await Promise.all(Array.from({length:Math.min(4,manifest.indexParts-i)},async(_,j)=>{
          const r=await fetch(`./data/registry/index-${String(i+j).padStart(2,'0')}.json`);
          if(!r.ok)throw Error('명단 일부를 받지 못했습니다');parts[i+j]=await r.json();
          parts[i+j].forEach(r=>r.push(norm(r[1]+' '+r[7])));rows.push(...parts[i+j]);postMessage({action:'progress',done:++done,total:manifest.indexParts});
        }));
        if(lastSearch)search(lastSearch);
      }
      rows.sort((a,b)=>a[0].localeCompare(b[0]));
      if(rows.length!==manifest.total)throw Error('명단 건수가 일치하지 않습니다');
      complete=true;if(lastSearch)search(lastSearch);return;
    }
    if(d.action==='search'){lastSearch=d;search(d);}
  }catch(e){postMessage({action:'error',message:e.message});}
};
function search(d){
      const q=norm(d.query),digits=/^\d+$/.test(q),counts=Array(8).fill(0),out=[];
      const stateColumn={all:2,period:3,unknown:4,expired:5,cancelled:6}[d.status]??2;
      for(const r of rows){
        const mask=r[stateColumn];
        if(!mask || (q && !(digits?r[0].includes(q):r[8].includes(q))))continue;
        if(d.extra>=0 && !(mask&(1<<d.extra)))continue;
        for(let i=0;i<8;i++)if(mask&(1<<i))counts[i]++;
        if(d.type<0 || mask&(1<<d.type))out.push(r.slice(0,7));
      }
      if(d.sort==='types')out.sort((a,b)=>bitCount(b[stateColumn])-bitCount(a[stateColumn])||a[0].localeCompare(b[0]));
      else out.sort((a,b)=>a[0].localeCompare(b[0]));
      const pages=Math.max(1,Math.ceil(out.length/20)),page=Math.min(Math.max(1,d.page),pages);
      postMessage({action:'results',id:d.id,total:out.length,counts,page,pages,complete,loaded:rows.length,expected:manifest.total,rows:out.slice((page-1)*20,page*20)});
    }
