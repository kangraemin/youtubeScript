# 정성 검토 A — 6개 채널 × 10편 (alsangmoo, aspim_research, developmong, doniggangpae, jisik_inside, wepoll)

서브에이전트 보고서 원문(2026-10-05). 표본: `sample110.json`, 원문: `rawdata/transcripts/`. 수치는 독립 감사(`audit.md`)에서 일부 교정됐다. 교정된 수치는 REPORT.md를 따른다.

## 총평
- 인용 정확도: 4,922개 중 정확 일치 4,816, 말줄임 일치 79, 불일치 27(0.5%)
- 분량 과잉: 돈깡패 숏폼은 요약이 원문의 5~9배다(0Macqxsu5HY 274자 → 2,399자, gcAhsPVvO_I 256자 → 1,383자). 알상무는 1.2~4.9배다(iQ2zUAaGoEw 12분 → 20,958자). 위폴은 편당 20~46K자다. 인용이 분량의 25~35%를 차지한다.
- 쓸모 있는 부분: headline, raw_summary, 채널별 1~2개 섹션

## 채널별
- **알상무**
  - 유용: raw_summary, verdicts. 예: a76Y7MkS0os "꼭 사야 한다면 종가에".
  - action_items가 있는 9편 중 8편이 verdicts나 watchlist를 재진술한다. 예: Kz3Yv976HNY는 action 1·2·4와 verdict 1·2·4가 같다.
  - iQ2zUAaGoEw 10:11 인용이 watchlist·chart_levels·verdicts·action_items 4곳에 있다. 인용 사용 924회 중 191회가 재사용이다.
  - a76Y7MkS0os sells 2건은 시청자 권유다.
  - eQ2D4kFRpSM data_points 7개는 잡정보다("37층", "모니터 6대", "MBTI INTJ").
  - 3LbiXN2gnqE verdicts에 가십이 들어 있다.
  - buys는 10편 모두 비어 있다.
- **애스핌**
  - 유용: data_points(TGA·QRA·엔화 숏 계약 수).
  - 인용 재사용 74/625로 가장 적다.
  - mtEuFO6dL4o는 verdict와 action이 같은 말이다.
  - OrAGiIJ2W78 chart_levels "나스닥 선물 -2~-250포인트 등락"은 가격대가 아니다.
  - buys·sells는 10편 모두 비어 있다.
- **디벨로몽**
  - 10편 모두 data_points에 본인 계좌 잔고가 있다(1fYU5TvGT9o "총 7억 7,600만 수익").
  - 2zpFCT_g0xY: action_items에 "토스증권+인스타 쓰레드 팔로우", lessons.reference에 멤버십 후기, chart_levels에 "USD +1,000%"가 들어 있다.
  - hMUNNwuSLfE buys "USD — 홀딩 중"은 기존 보유다. 같은 영상 verdicts "본인 자산 6억 1,300만원 | 15억 근접"은 조건문이 아니다.
- **돈깡패**
  - gcAhsPVvO_I(25초)의 한 규칙이 narrative·headline·raw_summary·verdicts 2건·lessons에 6번 반복된다.
  - Kdu98eqP_Zk data_points는 가정 예시다.
  - 55l_4wlvvbI는 실제 매수 발언을 watchlist에 넣었다.
  - macro_views 8편, chart_levels 7편이 비어 있다.
- **지식인사이드**
  - 유용: lessons, raw_summary.
  - x_5g8eAz424 verdicts에 격언이 들어 있다. CUDAP7ayiac verdicts "탄도탄 요격 독자보유국 | 3~5개국"은 조건문이 아니다.
  - kV3AHq165xo data_points "차인표 데뷔 1993년 MBC", action_items "신작+연극 관람". K8sYRXeLtVg "본인 심박수 200+".
  - chart_levels 8편이 비어 있다. 교양 5편은 buys·sells·chart_levels가 모두 비어 있다.
  - d0BBMk-ImME는 게스트 추천을 buys/sells에 넣었다.
- **위폴**
  - 편당 lessons 12~16개, macro_views 8~16개, data_points 14~24개다.
  - hMZqFCDmoAw buys 4건은 보유 유지다. NXFxevuIDlI sells 2건은 2024년 회고다.
  - NXFxevuIDlI data_points에 협찬 떡갈비 가격·함량, lessons.reference에 떡갈비 유래가 들어 있다.

## 공통
- buys·sells 30건 중 15건이 새 매매가 아니다. 보유 7, 시청자 권유 2, 게스트 추천 3, 과거 회고·정리 2, "안 사고 있다" 1이다. 종목명 없는 항목도 4건 있다.
- 인용 겹침: chart_levels ↔ data_points는 알상무 55%, 지식인사이드 71%. macro_views ↔ lessons는 알상무 36%. action_items ↔ verdicts는 알상무 30%, 디벨로몽 29%.
- terms에 사소한 항목이 들어 있다. iQ2zUAaGoEw "7,000 '안착' vs '올라온 것'", 3LbiXN2gnqE "갭상".
- headline·raw_summary·narrative가 겹친다. narrative는 최대 2,800자다.

## 사실 위험
- wepoll NXFxevuIDlI 52조 vs 61조 → **감사에서 기각.** 화자가 두 숫자를 다 말했다.
- alsangmoo wQwoW_HgNnM: 10년물 5% "위" vs "근접(미달)"이 모순된다.
- aspim JwiQ5iIH3Ys: 합계가 맞지 않는다.
- jisik YNAR4AiiiRU: "7배"는 계산상 4배이고, 원문의 "일곱 배"는 다른 맥락이다.
- jisik CUDAP7ayiac: 김효창/김호창 혼재, "1985~2025 60년" 계산 오류.
- developmong hMUNNwuSLfE: 원문에 없는 Direxion.
- aspim: 화자명 4종 표기.
- 알상무: "케빈 놀" vs "케빈 워시".
