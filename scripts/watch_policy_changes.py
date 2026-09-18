"""Bounded discovery on additional official boards. Never infer company validity from titles."""
import datetime as dt
import hashlib,json,re,time
from pathlib import Path
from urllib.parse import urljoin,urlparse,parse_qs,urlencode
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'site/data/policy-notices.json'
HOSTS={'www.mss.go.kr','www.kead.or.kr','www.goods.go.kr','www.coop.go.kr'}
SOURCES=[
 {'id':'mss-seoul','name':'서울지방중소벤처기업청','url':'https://www.mss.go.kr/site/seoul/ex/bbs/List.do?cbIdx=146&tgtTypeCd=SUB_CONT&searchKey=%EC%B7%A8%EC%86%8C','types':['sme','women','disabled','startup'],'parser':'mss'},
 {'id':'mss-chungnam','name':'충남지방중소벤처기업청','url':'https://www.mss.go.kr/site/chungnam/ex/bbs/List.do?cbIdx=315&tgtTypeCd=SUB_CONT&searchKey=%EC%B7%A8%EC%86%8C','types':['sme','women','disabled','startup'],'parser':'mss'},
 {'id':'mss-gyeonggi','name':'경기지방중소벤처기업청','url':'https://www.mss.go.kr/site/gyeonggi/ex/bbs/List.do?cbIdx=247&tgtTypeCd=SUB_CONT&searchKey=%EC%B7%A8%EC%86%8C','types':['sme','women','disabled','startup'],'parser':'mss'},
 {'id':'kead-notices','name':'한국장애인고용공단 공지사항','url':'https://www.kead.or.kr/bbs/deptgongji/bbsPage.do?menuId=MENU0895&searchCondition=SJ&searchKeyword=%ED%91%9C%EC%A4%80%EC%82%AC%EC%97%85%EC%9E%A5','types':['standard'],'parser':'kead'},
 {'id':'kead-standard','name':'한국장애인고용공단 표준사업장 자료실','url':'https://www.kead.or.kr/bbs/standardproduct/bbsPage.do?menuId=MENU0697','types':['standard'],'parser':'kead'},
 {'id':'goods','name':'꿈드래 공지사항','url':'https://www.goods.go.kr/pp/bd/board/noticeList.do?menuNo=5501000','types':['severe'],'parser':'goods'}]
def clean(s):return re.sub(r'\s+',' ',s).strip()
def safe(url):
 p=urlparse(url)
 if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.port:raise ValueError('Unexpected official URL')
 return url

def read(url):
 time.sleep(.4)
 with urlopen(Request(safe(url),headers={'User-Agent':'KPetro-PolicyNoticeMonitor/1.0'}),timeout=20) as r:
  safe(r.url);raw=r.read(4000001)
  if len(raw)>4000000:raise ValueError('Response too large')
  return raw.decode('utf-8')

def classify(title,attachments=''):
 t=re.sub(r'\s+','',title);full=t+re.sub(r'\s+','',attachments)
 types=[key for key,word in [('women','여성기업'),('disabled','장애인기업'),('startup','창업기업'),('sme','중소기업확인'),('standard','표준사업장'),('severe','중증장애인생산품'),('cooperative','사회적협동조합')] if word in t]
 if not types or not any(w in full for w in ['취소','반납','철회','인가취소','해산']):return None
 kind='prior_notice' if any(w in t for w in ['청문','사전통지','예정','의견제출']) else 'surrender_notice' if '반납' in t else 'cancellation_notice' if '취소' in t else 'status_update'
 return types,kind

def parse_listing(html,source):
 soup=BeautifulSoup(html,'html.parser');rows=soup.select('tbody tr');found=[];recognized=False
 for row in rows:
  a=None;url=None
  if source['parser']=='mss':
   m=re.search(r"doBbsFView\('(\d+)','(\d+)'",row.get('onclick',''))
   if m:
    recognized=True;a=row.select_one('a[href="#view"]');url=source['url'].split('List.do')[0]+f'View.do?cbIdx={m[1]}&bcIdx={m[2]}'
  elif source['parser']=='kead':
   a=row.select_one('a[onclick*="fn_bbsView"]')
   if a:
    m=re.search(r"fn_bbsView\('(\d+)'",a.get('onclick',''));recognized=True
    if m:url=source['url'].split('bbsPage.do')[0]+'bbsView.do?'+urlencode({'bbsCnId':m[1],'menuId':parse_qs(urlparse(source['url']).query)['menuId'][0]})
  else:
   a=row.select_one('a[href*="noticeView.do"]')
   if a:recognized=True;url=urljoin(source['url'],a['href'])
  if not a or not url:continue
  title=clean(a.get('title') or a.get_text(' ',strip=True));attachments=[]
  for link in row.select('a[href*="download"],a[href*="Download"]'):
   img=link.find('img');name=img.get('alt','') if img else clean(link.get_text(' ',strip=True))
   attachments.append({'name':name or '첨부파일','url':safe(urljoin(source['url'],link['href']))})
  result=classify(title,' '.join(x['name'] for x in attachments))
  if not result:continue
  dates=re.findall(r'20\d{2}[.-]\d{2}[.-]\d{2}',row.get_text(' ',strip=True))
  if not dates:raise ValueError('Missing notice date')
  day=dates[0].replace('.','-');dt.date.fromisoformat(day)
  if day<'2026-01-01':continue
  found.append({'id':hashlib.sha256(url.encode()).hexdigest()[:20],'title':title,'url':safe(url),'publishedAt':day,'enterpriseTypes':result[0],'kind':result[1],'sourceOffice':source['name'],'sourceId':source['id'],'attachments':attachments,'reviewStatus':'needs_review'})
 if not recognized:raise ValueError('Listing layout changed or empty search; previous records retained')
 return found

def main():
 prior=json.loads(OUT.read_text(encoding='utf-8-sig')) if OUT.exists() else {'notices':[],'sources':[]}
 records={n['url']:n for n in prior['notices']};old={s['id']:s for s in prior.get('sources',[])};sources=[];now=dt.datetime.now(dt.timezone.utc).isoformat()
 for source in SOURCES:
  info={**source,'checkedAt':now,'scope':'2026년 이후 게시물 · 해당 목록 검색 결과 앞 3페이지 (전국 전수 아님)'}
  try:
   got={}
   for page in range(1,4):
    param='pagerOffset' if source['parser']=='goods' else 'pageIndex';value=(page-1)*20 if param=='pagerOffset' else page
    rows=parse_listing(read(source['url']+'&'+urlencode({param:value})),source)
    for row in rows:got[row['url']]=row
   records.update(got);info.update(status='ok',lastSuccessfulScanAt=now,found=len(got))
  except Exception as e:info.update(status='error',error=type(e).__name__+': '+str(e),lastSuccessfulScanAt=old.get(source['id'],{}).get('lastSuccessfulScanAt'))
  sources.append(info);print(source['id'],info['status'],info.get('found',0),info.get('error',''))
 OUT.write_text(json.dumps({'schemaVersion':1,'checkedAt':now,'sources':sources,'notices':sorted(records.values(),key=lambda n:n['publishedAt'],reverse=True)},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
