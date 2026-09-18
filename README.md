# K-Petro 정부권장정책 구매지원

공공기관 구매 담당자가 우선구매 대상 기업을 **① 무엇을 파는지(품목) → ② 얼마에 살 수 있는지(계약단가) → ③ 누구인지(사업장 명단)** 까지 한 사이트에서 확인하는 도구입니다.

`joongyu01/supplier_diversity`(종합쇼핑몰 우대기업 물품 카탈로그)와 `joongyu01/supplier_diversity_2`(구매이음 사업장 명단·품목 검색)를 합친 저장소입니다. 두 저장소의 커밋 이력은 모두 보존되어 있습니다.

- 웹사이트: https://joongyu01.github.io/supplierdiversity/

UI 구성과 수정 범위는 [docs/ui.md](docs/ui.md)를 참고하세요.

## 화면

| 화면 | 파일 | 하는 일 | 원래 저장소 |
|---|---|---|---|
| 사업장 명단 | `site/businesses.html` | 8개 유형 44만 사업자번호를 업체명·사업자번호로 조회, 유형·기간·취소 이력과 연락처 | supplier_diversity_2 |
| 품목으로 찾기 (홈) | `site/index.html`, `site/offers.html` | 가치장터·꿈드래 공개 상품·서비스로 업체 찾기, 사업자번호로 명단 연결 | supplier_diversity_2 |
| 계약단가 조회 | `site/catalog.html` | 나라장터 종합쇼핑몰 품명별 우대기업 품목·규격·계약단가, CSV, 중증 생산시설 생산품목 | supplier_diversity |
| 인증 변경 공고 | `site/cancellations.html` | 사회적기업 및 추가 유형의 공식 취소·반납·사전통지 공고 (수집 범위 명시) | 공통 |
| 이전 검색 화면 | `site/product-search.html` | 구 품목 검색·검토목록 (보존) | supplier_diversity_2 |

모든 화면은 같은 상단 메뉴로 이어집니다. 카탈로그와 품목 검색의 업체 옆 **사업장 명단·인증 이력 →** 링크는 `./businesses.html?q=<사업자번호>`로 명단 화면을 열어, 쇼핑몰 자료에 없는 유형·만료·취소 기록까지 확인하게 합니다.

품명 선택에는 `chunks[].names`의 **실제 품명 전체**를 제공하되 처음에는 첫 줄만 표시합니다. 펼치기·접어두기로 전환할 수 있고, 검색 중에는 일치하는 품명을 모두 표시합니다. 품명 검색 후 버튼을 누르면 모든 관련 묶음에서 그 품명만 조회합니다. 사업장 결과는 명단에 기록된 기업 유형이 많은순으로 정렬할 수 있습니다.

홈은 검색 조건을 먼저 표시하고 공개 판매정보를 받는 대로 결과를 추가합니다. 배포 시 `build_offer_delivery.py`가 `offers.json`에서 초기 묶음과 내용 해시 기반 후속 묶음을 생성합니다. 일부 요청 실패 시 이미 받은 결과는 유지하고 누락된 묶음만 재시도합니다.

업체의 **현재 상태 확인**은 사업자번호 복사와 8개 유형의 공식 조회 서비스 연결을 제공합니다. 로그인이나 확인서 번호가 필요한 서비스가 있어 사이트 자체에서 실시간 인증 유효성을 자동 판정하지 않습니다. 공고 발견만으로 사업장 상태를 변경하지 않습니다.

## 공통 원칙

- **사업자등록번호로만 결합합니다.** 업체명·대표자 이름 유사도로 합치지 않습니다.
- **가공하지 않습니다.** 원본이 없으면 빌드를 중단하고, 수집하지 않은 품목·가격을 채우지 않습니다. 수집 누락을 미판매로 판단하지 않습니다.
- **사업자등록 공개정보는 싣습니다.** 대표자·사업장 주소·전화는 구매 담당자의 확인·연락·방문용입니다. 담당자 개인 이메일·휴대전화는 싣지 않습니다.
- ‘기록된 기간 내’, 단가, 계약기간은 수집·생성 시점 값입니다. 발주 전 나라장터와 원문에서 확인하세요.
- 인증키, 원본 Excel, `data/raw/`, `private/`는 저장소에 넣지 않습니다.

자료별 출처·건수·한계는 [docs/data-sources.md](docs/data-sources.md), 조달청 API 실호출 기록은 [docs/api-notes.md](docs/api-notes.md), 공고 봇은 [docs/cancellation-monitor.md](docs/cancellation-monitor.md)에 있습니다.

## 설치와 확인

Python 3.10 이상.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build_offer_delivery.py       # 공개 판매정보를 작은 전송 묶음으로 준비
python -m http.server 8000 --directory site   # http://localhost:8000
```

## 자료 갱신

### 1. 사업장 명단 (`site/data/directory.json`, `site/data/registry/`)

```powershell
python scripts/build_directory.py --social "private/sources/social-enterprises-2026-2.xlsx" --policy "2026년 6월 30일 기준 정부권장정책.xlsx"
python scripts/build_registry_site.py
```

중소기업은 SMPP 2026-09-14 확인서 337,692건(`scripts/import_smpp_sme.py`), 사회적기업은 2026-07-14 누적 명단, 나머지는 2026-06-30 정부권장정책 자료입니다. 통합 고유 사업자번호 444,147개이며 과거·만료·취소 이력을 포함합니다. SMPP 전국 조회 대비 3,180건은 미확보입니다.

### 2. 품목으로 찾기 (`site/data/offers.json`)

```powershell
python scripts/collect_offers.py        # 가치장터 + 꿈드래 12개 대분류의 공개 목록 전체 (약 3만 요청, 2~3시간)
python scripts/build_offers_site.py
```

API가 아니라 공개 상품 페이지를 읽습니다. 가치장터는 상품 상세 → 판매기업 소개의 사업자번호, 꿈드래는 상품 상세의 시설 사업자번호로만 명단과 연결합니다. 호스트별 요청 간격(`--interval`, 기본 0.35초), 재시도, 응답 캐시(`private/offer-cache/`)를 쓰므로 중단돼도 다시 실행하면 이어서 받습니다. 빠른 확인은 `--sepp-pages 1 --goods-pages 1 --goods-categories 화훼`, 최신 원문 재수집은 `--refresh`.

`site/data/offers.json`(schemaVersion 2)은 연락처를 업체당 한 번만 싣고 상품은 `[id, 상품명, 분류, 확인일, 연락처 번호]`로 압축합니다. 상품 URL은 ID로 복원합니다. 정규화 원본과 수집 보고서는 `data/offers/`(git 미추적)에 둡니다.

### 3. 쇼핑몰 단가 카탈로그 (`site/data/catalog.json`, `site/data/chunks/`)

```
config/product_names.txt        기관이 실제 구매하는 품명 목록
        │  scripts/collect_shopmall.py — 품명별 2026년 등록분 수집
        ▼
data/raw/shopmall/<품명>.csv     원시 응답 (git 미추적)
        │  scripts/collect_suppliers.py — 등장 업체의 대표자·주소·전화
data/raw/suppliers.csv
        │  scripts/build_catalog.py — 정부권장정책 엑셀 사업자번호와 대조
        ▼
site/data/catalog.json          업체 + 품명 인덱스 + 중증 생산시설 (초기 로드)
site/data/chunks/<품명>.json     품목 상세 (품명 선택 시 로드)
```

```powershell
$env:DATA_GO_KR_SERVICE_KEY = "발급받은 키"   # 공공데이터포털 15129471 활용신청
python scripts/collect_shopmall.py            # 이미 있는 품명 파일은 건너뜀
python scripts/collect_shopmall.py 프로젝터 UPS
python scripts/collect_suppliers.py
python scripts/build_catalog.py               # 엑셀 원본이 저장소 루트에 있어야 함
```

종합쇼핑몰 API는 등록·변경 이벤트 피드라 전체 수집은 월 10~19만 건입니다. 품명 필터로 필요한 품명만 받습니다(하루 1,000회 한도).

### 4. 인증 변경 공고 (`site/data/cancellation-notices.json`, `site/data/policy-notices.json`)

GitHub Actions `watch-cancellations.yml`이 매일 08:23(KST) 실행합니다. 전체 관서 수집에 성공할 때만 JSON을 교체하고, 공고만으로 업체 상태를 바꾸지 않습니다. 수동 실행: `python scripts/watch_cancellations.py` (`requirements-cancellation.txt`). 추가 유형은 `python scripts/watch_policy_changes.py`로 서울·충남·경기 중기청, 장애인고용공단, 꿈드래의 2026년 이후 앞 3페이지를 확인합니다. 전국 전수 수집이 아니며, 사회적협동조합 인가부처별 자동 수집은 아직 연결되지 않았습니다. 게시판별 실패 시 기존 기록과 마지막 성공일을 유지합니다.

### 보조: 지정 업체 등록 물품 (`scripts/collect.py`)

`config/suppliers.json`의 업체를 사용자정보 API로 조회해 `site/data/registered-products.json`에 저장합니다. 화면에서는 쓰지 않는 탐색용이며, 카탈로그의 `catalog.json`을 덮어쓰지 않도록 출력 파일을 분리했습니다. GitHub Actions `collect.yml`(수동 실행)이 이 스크립트를 돌립니다.

## 구조

```text
site/                          GitHub Pages 정적 사이트 (main push 시 배포)
  index.html  registry.js registry-worker.js registry.css directory.css   사업장 명단
  offers.html offers.js offers.css purchase-categories.js                  품목으로 찾기
  catalog.html app.js styles.css                                           쇼핑몰 단가 카탈로그
  cancellations.html cancellations.js                                      인증 변경 공고
  product-search.html directory.js                                         이전 검색 화면
  data/                        directory.json registry/ offers.json catalog.json chunks/ summary.json cancellation-notices.json
config/                        product_names.txt suppliers.json cancellation-sources.json
scripts/                       build_directory · build_registry_site · import_smpp_sme · extract/package_business_registries
                               collect_offers · build_offers_site
                               collect_shopmall · collect_suppliers · build_catalog
                               watch_cancellations · collect
tests/                         test_directory · test_offers · test_mall_catalog · test_collect · test_cancellations
docs/                          data-sources · api-notes · cancellation-monitor
```
