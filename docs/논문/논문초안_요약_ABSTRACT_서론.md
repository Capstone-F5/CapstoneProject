# LLM 및 컴퓨터 비전 기반 사회적 약자 맞춤형 배리어프리 키오스크 설계 및 구현

## Design and Implementation of an LLM- and Computer-Vision-Based Personalized Barrier-Free Kiosk for Vulnerable Users

> 편집 안내: 본 마크다운은 한국실천공학교육학회 논문지 양식의 제목, 요약, ABSTRACT, Key Words, 본문 장 번호 및 번호형 참고문헌 순서를 반영한 초안이다. 문서 하단의 “추가 실험 필요” 부분은 작성자 확인용이므로 최종 제출 전에 삭제한다.

## 요 약

셀프서비스 키오스크의 확산은 서비스 효율성을 높였으나, 화면 중심의 복잡한 절차와 제한된 입력 방식은 고령자, 장애인 및 디지털 숙련이나 언어 측면에서 제약을 겪는 사용자의 독립적인 서비스 이용을 어렵게 한다. 본 연구에서는 이러한 디지털 취약 사용자를 지원하기 위해 대규모 언어 모델(LLM; Large Language Model) 기반 음성 대화와 컴퓨터 비전 기반 비접촉 제스처를 통합한 배리어프리 키오스크를 설계하고 구현하였다. 본 연구에서 “맞춤형”은 시스템이 이용자의 연령이나 장애를 자동 분류하는 것이 아니라, 이용자가 터치·음성·제스처, 언어 및 접근성 설정을 명시적으로 선택하여 자신에게 맞는 상호작용을 구성하는 것을 의미한다. 제안 시스템은 음성을 텍스트로 변환한 뒤 대화 문맥, 현재 화면과 장바구니 상태를 함께 분석한다. 검색 증강 생성(RAG; Retrieval-Augmented Generation)과 제한된 도구 호출을 이용하여 실제 메뉴·옵션·주문 데이터에 근거한 화면 조작도 수행한다. MediaPipe Hands 기반 손 랜드마크는 포인터 이동, 확인, 손가락 개수와 방향성 제스처 처리에 사용하였다. React 기반 사용자 인터페이스와 FastAPI 기반 서버를 연동하고 한국어, 영어, 중국어 및 일본어 인터페이스를 제공하였다. 아울러 입력 인식 성능, 과업 수행과 주관적 사용성을 함께 측정하는 과업 기반 평가 프레임워크를 설계하였다. 제안 시스템의 정량적 효과는 해당 프레임워크에 따른 추가 실험으로 검증할 필요가 있다.

## ABSTRACT

The widespread adoption of self-service kiosks has improved service efficiency, but complex screen-oriented procedures and limited input methods continue to hinder independent use by older adults, people with disabilities, and users facing limited digital proficiency or language barriers. This study designs and implements a barrier-free kiosk that integrates large language model (LLM)-based voice interaction with computer-vision-based touchless gestures. In this study, personalization does not refer to automatic classification of a user’s age or disability. Instead, users explicitly select touch, voice, or gesture input, an interface language, and accessibility settings to configure an interaction method suited to their needs. After converting speech into text, the system interprets each utterance together with the dialogue history, current screen, and cart state. Retrieval-augmented generation (RAG) and constrained tool calls ground menu searches and interface actions in actual menu, option, and order data. MediaPipe Hands landmarks support pointer movement, confirmation, finger-count, and directional gestures. A React interface is connected to a FastAPI server, with Korean, English, Chinese, and Japanese interfaces. The study also defines a task-based evaluation framework combining input-recognition performance, task performance, and subjective usability. Further experiments are required to quantify the effectiveness of the proposed system using this framework.

**Key Words:** Barrier-free kiosk, Computer vision, Large language model, Multimodal interaction, Vulnerable users

## I. 서론

디지털 전환과 비대면 서비스의 확산으로 키오스크는 음식점, 교통, 금융 및 공공서비스 등 일상적인 서비스 접점에 빠르게 보급되고 있다. 그러나 화면과 터치 중심의 복잡한 절차는 고령자와 장애인, 한국어 사용에 제약이 있는 외국인 및 디지털 기기 사용 경험이 적은 이용자에게 접근성 장벽이 될 수 있다[1], [2]. 작은 글자와 복잡한 메뉴 구조, 제한 시간 및 단일 입력 방식은 이들의 독립적인 서비스 이용을 어렵게 한다. 본 논문에서는 이러한 이용자를 “디지털 취약 사용자”로 지칭한다.

기존 배리어프리 키오스크는 큰 글자, 높은 대비, 큰 버튼과 단순화된 화면을 제공해 왔다. 이러한 개선은 시인성을 높이지만 복잡한 정보 구조와 인지적 부담까지 해소하기는 어렵다[1], [2]. 음성 인식·합성과 의도 분석을 결합한 대화형 키오스크도 제안되었으나[3], 배경 소음과 다양한 발음, 메뉴 고유명사 및 복합 발화는 인식 오류를 유발한다. 이에 따라 발화 보정, 문맥 분석, 누락 정보에 대한 재질문과 처리 결과의 피드백이 함께 요구된다[4].

최근에는 다양한 자연어 표현을 처리하기 위해 대규모 언어 모델(LLM; Large Language Model) 기반 키오스크가 연구되고 있다[5], [6]. LLM 응답을 실제 서비스 데이터에 연결하는 검색 증강 생성(RAG; Retrieval-Augmented Generation)은 외부 지식의 검색과 갱신에 유용하다[7]. 그러나 검색 품질이 낮거나 필요한 정보가 없으면 근거가 불충분한 응답을 생성할 수 있다[8]. 따라서 주문과 결제처럼 상태를 변경하는 기능은 생성 응답과 분리하고, 데이터베이스 및 허용된 도구를 통해 실행할 필요가 있다.

컴퓨터 비전을 적용한 배리어프리 키오스크 연구에서는 영상으로 사용자 특성을 분석하여 사용자 인터페이스(UI; User Interface)를 전환하거나, 손동작을 이용한 비접촉 조작 방식을 제공하였다[9], [10]. 이러한 연구는 상황에 따른 인터페이스 조정 가능성을 보여주지만, 보조기기 감지에 따른 능동적 모드 전환과 사용자의 직접 선택을 터치·음성·제스처가 통합된 하나의 서비스 흐름에서 제공하는 연구는 부족하다. 통합 시스템을 입력 성능, 실제 주문 과업 및 주관적 사용성 측면에서 함께 평가하는 체계도 요구된다.

이에 본 연구는 React와 FastAPI를 기반으로 LLM 음성 대화, MediaPipe Hands 기반 제스처 및 터치 UI를 하나의 주문 흐름으로 통합한다. 컴퓨터 비전 모듈은 흰 지팡이를 감지하면 음성 안내와 음성 모드를 활성화하고, 휠체어를 감지하면 제스처 모드를 활성화한다. 제스처 모드에서는 MediaPipe Hands의 손 랜드마크 추정 기술[11]을 활용하여 휠체어 이용자 등 터치 인터페이스 사용이 어려운 사용자에게 비접촉 조작 방법을 제공한다. 사용자는 자동 전환된 모드를 직접 변경하거나 해제할 수 있다. 즉 본 연구의 “맞춤형”은 연령이나 장애 여부를 생체 특징으로 추정하는 방식이 아니라, 보조기기 감지에 따른 능동적 전환과 사용자의 명시적 선택을 결합한 혼합형 적응을 의미한다. 음성 발화는 대화 문맥과 현재 화면·장바구니 상태를 바탕으로 처리하며, 메뉴 검색과 장바구니 조작에는 RAG와 제한된 도구 호출을 사용한다. 본 연구의 기여는 첫째, 터치·음성·제스처를 통합한 상호작용 구조, 둘째, 실제 서비스 데이터와 연결된 LLM 도구 실행 구조, 셋째, 보조기기 감지 기반 능동적 모드 전환과 사용자 재선택을 결합한 접근성 설계, 넷째, 입력·과업·사용성의 세 계층으로 구성된 평가 프레임워크를 제시한 것이다. 실사용자 정량 평가는 후속 연구로 구분한다.

## References

[1] E. J. Sin and S. B. Lim, “Development of Evaluation Indicators and Usability Evaluation of Kiosk for the Elderly - the Case of KORAIL’s Kiosk for Ticketing,” The Journal of the Korea Contents Association, vol. 22, no. 1, pp. 188–196, 2022. DOI: 10.5392/JKCA.2022.22.01.188.

[2] E. Go, J. Choi, M. Lee, H. Lee, E. Kim, and J. Shin, “Visible, Yet Not Usable: A Comparative Study of Barrier-Free and General Kiosks for Older Adults,” Proceedings of HCI Korea 2026, pp. 384–390, 2026.

[3] S.-W. Kim, D.-J. Choi, Y.-M. Song, and I.-Y. Moon, “Design and Implementation of Voice-based Interactive Service KIOSK,” Journal of Practical Engineering Education, vol. 14, no. 1, pp. 99–108, 2022. DOI: 10.14702/JPEE.2022.099.

[4] J. S. Ryu and S. K. Jung, “Enhancing Robustness to Errors in AI-based Speech Recognition Kiosks,” The Transactions of the Korea Information Processing Society, vol. 15, no. 2, pp. 95–101, 2026. DOI: 10.3745/TKIPS.2026.15.2.95.

[5] S. Jung, S. Kim, J. Ha, and S. Kim, “Conversational Artificial Intelligence Kiosk Using GPT,” Proceedings of the 2023 KIIT Summer Conference, pp. 640–642, 2023.

[6] H. Kim, S. Lee, D. Jang, Y. Cha, J. Hwang, and D. Kim, “LLM-MCP Conversational Kiosk for Public Administrative Services,” Proceedings of the 2025 KIIT Fall Conference, pp. 1288–1291, 2025.

[7] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” Advances in Neural Information Processing Systems, vol. 33, pp. 9459–9474, 2020.

[8] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, M. Wang, and H. Wang, “Retrieval-Augmented Generation for Large Language Models: A Survey,” arXiv preprint arXiv:2312.10997, 2023.

[9] S. Y. Kang, Y. J. Lee, H. A. Jung, S. A. Cho, and H. G. Lee, “An User-Friendly Kiosk System Based on Deep Learning,” Journal of the Korea Society of Industrial Information Systems, vol. 29, no. 1, pp. 1–13, 2024. DOI: 10.9723/jksiis.2024.29.1.001.

[10] D.-K. Shin, J.-G. Cha, and S.-K. Kim, “A Study on Implementation a Barrier-Free Kiosk System for the Digitally Vulnerable,” Journal of the Korea Institute of Electronic Communication Sciences, vol. 20, no. 4, pp. 909–914, 2025. DOI: 10.13067/JKIECS.2025.20.4.909.

[11] F. Zhang, V. Bazarevsky, A. Vakunov, A. Tkachenka, G. Sung, C.-L. Chang, and M. Grundmann, “MediaPipe Hands: On-device Real-time Hand Tracking,” arXiv preprint arXiv:2006.10214, 2020.

---

## 작성자 확인용: 추가 실험 필요 항목

> 아래 내용은 논문 본문이 아닌 작성·실험 관리용이며 최종 제출본에서 삭제한다. 현재 코드에 설정된 임계값, 프레임 수, 모델의 confidence 값은 실험 정확도나 사용성 결과가 아니므로 논문 성능 수치로 사용할 수 없다.

| 번호 | 추가로 측정할 항목 | 권장 측정 방법 | 최종 원고에 들어갈 값 |
|---|---|---|---|
| 1 | 음성 전사 성능 | 실제 주문 발화 데이터에서 언어별·소음 조건별 단어 오류율(WER; Word Error Rate) 또는 문자 오류율(CER; Character Error Rate) 측정 | 발화 수 N, WER/CER, 소음 조건 |
| 2 | 주문 의도 및 도구 호출 정확도 | 메뉴 추가·수정·삭제, 옵션 변경, 결제 단계 등 시나리오별 정답 action과 실제 action 비교 | 시나리오 수 N, 정확도, 실패 유형 |
| 3 | LLM 근거성 및 장바구니 무결성 | 존재하지 않는 메뉴·가격 생성, 임의 옵션 선택, 잘못된 장바구니 변경 횟수 측정 | 오류율, 환각 사례 수, 무결성 성공률 |
| 4 | 제스처 인식 성능 | 사용자·거리·조명·배경 조건을 나누어 각 제스처의 confusion matrix 작성 | 사용자 수 N, 동작별 정확도·재현율·오인식률 |
| 5 | 입력 및 응답 지연 | 제스처 발생부터 화면 반응까지, 발화 종료부터 음성-텍스트 변환(STT; Speech-to-Text) 완료·LLM 첫 응답·전체 응답까지 구간별 측정 | 평균, 중앙값, 표준편차 또는 95백분위 지연시간 |
| 6 | 과업 기반 사용성 | 터치 전용 조건과 제안 멀티모달 조건에서 동일 주문 과업 비교 | 참가자 수 N, 성공률, 완료 시간, 재시도·도움 요청 수 |
| 7 | 디지털 취약 사용자 대상 평가 | 고령자·시각 또는 지체장애 사용자 등 실제 목표 집단을 명시하고 동의 절차 후 평가 | 집단별 N, 연령·특성 범위, SUS/PSSUQ 등 사용성 점수 |
| 8 | 다국어 성능 | 한국어·영어·중국어·일본어에서 동일 주문 시나리오 수행 | 언어별 전사·도구 호출·과업 성공률 |
| 9 | 사용자 인터페이스(UI; User Interface) 접근성 적합성 | 글자·버튼 크기, 명도 대비, 조작 영역 위치, 상태 피드백을 적용 기준과 대조 | 기준별 충족 여부와 측정값 |
| 10 | 보조기기 감지 및 모드 전환 성능 | 흰 지팡이·휠체어별로 거리·각도·조명·배경 조건을 나누어 감지와 모드 전환 결과 측정 | 클래스별 정밀도·재현율·F1 점수, 오전환율, 전환 지연시간 |

### 결과 확보 후 교체할 문장

- 국문 요약 마지막 문장의 “추가 실험으로 검증할 필요가 있다”를 실제 핵심 결과 1–2개로 교체한다.
- ABSTRACT 마지막 문장도 국문 결과와 동일한 범위와 수치로 교체한다.
- 실제 평가 방법과 결과는 후속 “실험 및 평가” 장에서 기술한다.
- 실험 전에는 “향상하였다”, “우수한 성능을 보였다”, “접근성을 개선하였다”와 같은 효과 단정 표현을 사용하지 않는다.
