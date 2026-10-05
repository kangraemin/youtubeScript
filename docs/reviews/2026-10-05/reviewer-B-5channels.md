# 정성 검토 B — 5개 채널 × 10편 (mk_wallstreet, moneycomics, sbs_gyoyangi, shukaworld, yonhap_economy)

서브에이전트 보고서 원문(2026-10-05). 검토 범위는 고르지 않다. 매경·슈카·머니코믹스는 거의 정독했다. SBS는 3편 정독, 4편 일부, 3편은 headline만 봤다. 연합은 6편 정독, 4편 일부만 봤다. 아래 섹션 공유율 수치는 독립 감사에서 재현되지 않았다. REPORT.md는 110건 전체 재계산값을 쓴다.

## 총평
- 가장 유용한 섹션은 headline, raw_summary, verdicts다.
- headline이 50~80자 규칙을 어긴 경우가 26/50편이다(UocXAA9eck8 145자 등).
- 분량이 과하다. T6Km1iqhco0(23분)은 인용 306개, n99hFHFjka4는 JSON 65KB다.

## 채널별
**매경**
- 유용: 특파원 리포트의 verdicts와 lessons(JNrjyvI2FbU, oLn3XfN1CdA).
- action_items에 소비자 팁이 들어 있다. oLn3XfN1CdA "오우라링 사이징 키트", yKZQnlUqEAw 패션위크, CdNRPxL86w4 PB USDA 번호.
- macro_views에 잡담이 들어 있다. CdNRPxL86w4 "김밥 시장", ijjjLJU1J0Y "주유소 3중 구조".
- xZv3Xf5W9Ao chart_levels 5개는 전부 data_points와 같은 숫자다.

**머니코믹스**
- gR5OQxJr7Cs buys 10개 중 매수를 명시한 발언은 0개다.
- qqBqFPKFosk의 유튜버 추천 종목이 buys에 들어 있다. 신영증권은 buys와 sells 양쪽에 있다.
- qqBqFPKFosk action_items 10개 대부분이 lessons를 재진술한다(감사 결과 약 8개).
- U__2kW81Tlc action_items에 "선크림 바르기", "드라마 시청"이 있다.
- 짧은 클립 과잉 추출: K6hElDMPz14(77초)에 lessons 4개, 70_EsNIDAE0(55초 콩트)에 term "피터 린치".
- NdMG16MXAOU 차트 강의는 실용적이다.

**SBS 교양이**
- 유용: rule/counter. ik7NF4JbYwA "과열은 이익 비중과의 갭", Ho5UQgFZX8I "'다변화' 리포트 = 매도 신호".
- 중복: ik7NF4JbYwA "삼성 하락 = 매수"가 4곳, Ho5UQgFZX8I "호르무즈 8/16"이 4곳에 있다.
- chart_levels에 비가격 지표가 들어 있다(ik7NF4JbYwA, sb6Xd3Wj_eA).
- WtRnV4r1fb8 action_items는 기업에 대한 권고다. q0Jo5F8pHbs terms 11개는 다수가 법령명이다.

**슈카**
- 유용: 4u3VzpSKE1g, Us890Q2m3Tg, vSWPtH9V7so는 raw_summary만으로 충분하다.
- n7Z2vUJDgPU(티라노): macro_views "1905년 NYT 티렉스 마케팅", action_items "둘리사우루스 마케팅 트래킹".
- Zcs3uzxymd0 action_items는 모델이 만든 권고다.
- tjcnSiBmTs0은 8개 섹션을 비우고 "(경제·시장 내용 없음)"으로 표기했다. 잘 처리한 사례다. 다만 raw_summary와 narrative 유사도가 0.87이다.
- 5H1kX7kp2tc(107초): 한 문장이 6곳에 반복된다.

**연합경제**
- 유용: 종목별 조건부 대응. 2xMIb5tWthU "이수페타시스 12만 돌파 시 1차 13만", n99hFHFjka4 "WTI 80달러".
- n99hFHFjka4는 watchlist 26개, action_items 19개, verdicts 15개다.
- 2xMIb5tWthU verdicts 8개 중 5개가 action_items와 1:1로 겹친다.
- 교양 회차 96rKJwYGG4k, 5ubsE9NA1EU는 주식 섹션을 비워 적절히 처리됐다.

## 인용
- "..." 이어붙이기: 연합 115/981, 머니코믹스 21건. 전부 구버전 모델(opus-4-7·4-8, sonnet-4-6) 출력이고 opus-5 출력에는 0건이다.
- 조각 인용: 15자 미만이 머니코믹스 39건, SBS 34건이다. ju9EZDBo6c0 "[3:52] 집안,".
- 0uXCnSWRDAg: 200자 넘는 영어 인용 20건.
- Qy_YJorjIvE(4:29 영상): 마지막 인용이 2:14:26이라 후반이 누락됐다.
- n99hFHFjka4: timestamp 형식 오류 "3:28 (1:40:28)".

## 사실 위험
- 1yJLyvXWKi0: "스타인브레너"가 인용에 없고, 14년 vs 15년으로 불일치한다.
- ijjjLJU1J0Y: "랜드리스 리츠"(오인식 확장 의심), 케이시스 티커 "KCS"(실제 CASY로 알려짐).
- U__2kW81Tlc: quote 없는 data_point이고, 다른 영상 맥락이 섞였다.
- vSWPtH9V7so: 15년 vs 인용 "10년 차트", 맥도날드 -15% vs -10%.
- Us890Q2m3Tg: "역대 최고 판매량"으로 과장했다.
- 5H1kX7kp2tc: quote에 근거 없는 추측.
