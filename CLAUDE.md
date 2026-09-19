# 작업 메모 (Claude Code 세션용)

사용자와는 한국어로 대화합니다. 구조·실행 방법은 README.md를 따릅니다.

## 원칙
- 업체 결합은 사업자등록번호로만. 수집하지 않은 품목·가격을 만들어 넣지 않음.
- 공개 사이트(가치장터 sepp.or.kr, 꿈드래 goods.go.kr) 수집은 호스트별 요청 간격(기본 0.35초)을 지킴. 여러 에이전트·계정·IP로 나눠 속도 제한을 우회하지 않음.
- 인증키·원본 Excel·`private/`·`data/raw/`·`data/offers/`는 커밋하지 않음.

## 진행 상황 (2026-09-17)
- 두 저장소(supplier_diversity, supplier_diversity_2) 병합·배포 완료: https://joongyu01.github.io/supplierdiversity/
- 공개 상품 전체 수집(가치장터 약 7,700 + 꿈드래 12개 분류 약 20,900)은 GitHub Actions `Collect public offers`(`.github/workflows/collect-offers.yml`)에서 실행.
  - 전체 목록·상세 확보 및 빌드 검증을 통과할 때만 `site/data/offers.json`을 커밋·배포. 목록은 항상 재조회, 상세 캐시는 24시간 미만만 재사용. 실패·일부 범위 수집은 기존 공개 결과를 보존하고 `data/offers/collection-attempt.json`에 진단을 남김.
- 남은 일: 수집 완료 후 offers.html 화면 확인(검색 속도·결과), `site/purchase-categories.js` 분류를 새 상품에 맞게 보강 검토.
- 사용자 할 일: 저장소 Secret `DATA_GO_KR_SERVICE_KEY` 등록(collect.yml 전용).
