"""Build small, versioned public offer batches for progressive rendering at deployment."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(site):
    data=json.loads((site/'data/offers.json').read_text(encoding='utf-8'))
    groups=[];batch=[];size=0
    for b in data['businesses']:
        raw=json.dumps(b,ensure_ascii=False,separators=(',',':')).encode()
        limit=18000 if not groups else 190000
        if batch and size+len(raw)>limit: groups.append(batch);batch=[];size=0
        batch.append(b);size+=len(raw)
    if batch:groups.append(batch)
    if not groups:groups=[[]]
    target=site/'data/offer-batches';target.mkdir(exist_ok=True)
    parts=[]
    for batch in groups[1:]:
        raw=json.dumps(batch,ensure_ascii=False,separators=(',',':')).encode();name=hashlib.sha256(raw).hexdigest()[:16]+'.json'
        (target/name).write_bytes(raw);parts.append({'file':name,'businesses':len(batch)})
    boot={k:v for k,v in data.items() if k!='businesses'}
    boot.update(businesses=groups[0],parts=parts,totalBusinesses=len(data['businesses']))
    (target/'bootstrap.json').write_text(json.dumps(boot,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    return boot
if __name__=='__main__':
    result=build(ROOT/'site');print(f"Offer delivery: {len(result['businesses'])} initial businesses, {len(result['parts'])} batches")
