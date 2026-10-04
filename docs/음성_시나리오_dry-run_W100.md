# 고정 100개 전체 흐름 시나리오(W001~W100) dry-run 문서

`python tools/voice_scenario_suite.py --category 대량흐름 --dry-run`(LLM 호출 0, 비용 0) 결과를 정리한 문서다.
dry-run은 발화와 **기대 장바구니**만 만들 뿐 서버 응답을 받지 않으므로 **통과/실패 결과는 없다**. 실제 통과율은 LLM 실행(≈4~9달러)이 필요하다. 마지막 실측은 53/100(가드 보강 전).

- 시나리오 100개, 말 턴 1122개, 평균 11.2턴/시나리오
- 턴마다 `cart_exact`(장바구니 정확 일치), `no_actions`(실행되면 안 되는 액션) 같은 검사가 붙는다.

## 1. 통계

### 묶음
| 묶음 | 개수 |
|---|---|
| 편집 | 30 |
| 기본 다품목 | 25 |
| 세트 옵션 | 25 |
| 종합 | 20 |

### 도입부
| 도입부 | 개수 |
|---|---|
| orderType_screen | 15 |
| menu_first | 14 |
| direct_take | 14 |
| stt_naejang | 14 |
| touch_type | 13 |
| greet_take | 12 |
| greet_dine | 11 |
| english | 7 |

### 메뉴 조작(시나리오 내 등장 횟수)
| 조작 | 개수 |
|---|---|
| add_single | 67 |
| add_burger_ask | 60 |
| remove_line | 53 |
| add_multi | 42 |
| undo_last | 36 |
| add_set_ask | 28 |
| convert_to_set | 25 |
| add_set_oneshot | 24 |
| convert_to_single | 24 |
| touch_add | 24 |
| reduce_qty | 23 |
| add_more | 16 |
| set_qty | 13 |
| readd_removed | 13 |
| change_side | 13 |
| add_second_set | 10 |
| change_drink | 9 |
| query | 8 |
| change_both | 8 |
| add_exclusion | 5 |

### 결제·포인트 유형
| 유형 | 개수 |
|---|---|
| no_points | 40 |
| back_to_menu | 22 |
| method_change | 16 |
| points_inline | 12 |
| points_phone | 10 |

### 검사 종류(턴 수)
| 검사 | 개수 |
|---|---|
| cart_exact | 715 |
| actions | 413 |
| no_actions | 196 |
| out_any | 73 |
| reply_lang | 7 |

## 2. 시나리오 색인

| ID | 묶음 | 도입부 | 조작 | 포인트/결제 | 말 턴 |
|---|---|---|---|---|---|
| W001 | 기본 다품목 | touch_type | add_burger_ask>add_burger_ask>set_qty | no_points | 8 |
| W002 | 기본 다품목 | menu_first | add_single>add_burger_ask | no_points | 9 |
| W003 | 기본 다품목 | greet_dine | add_multi>add_single | points_phone | 8 |
| W004 | 기본 다품목 | direct_take | add_burger_ask>add_burger_ask>add_burger_ask | method_change | 11 |
| W005 | 기본 다품목 | greet_take | add_burger_ask>add_single>add_more>add_burger_ask | method_change | 12 |
| W006 | 기본 다품목 | orderType_screen | add_burger_ask>set_qty>add_burger_ask | back_to_menu | 11 |
| W007 | 기본 다품목 | greet_take | add_multi>add_multi>add_more | no_points | 8 |
| W008 | 기본 다품목 | touch_type | add_burger_ask>add_single>add_more>query | points_phone | 9 |
| W009 | 기본 다품목 | touch_type | add_burger_ask>add_multi | back_to_menu | 8 |
| W010 | 기본 다품목 | direct_take | add_single>add_more>add_multi | no_points | 7 |
| W011 | 기본 다품목 | greet_dine | add_burger_ask>set_qty>add_more | back_to_menu | 11 |
| W012 | 기본 다품목 | greet_take | add_burger_ask>add_single>add_single | no_points | 9 |
| W013 | 기본 다품목 | stt_naejang | add_burger_ask>add_burger_ask | points_inline | 9 |
| W014 | 기본 다품목 | touch_type | add_burger_ask>add_burger_ask>add_single>add_burger_ask | back_to_menu | 12 |
| W015 | 기본 다품목 | greet_dine | add_single>add_more>add_multi | method_change | 9 |
| W016 | 기본 다품목 | orderType_screen | add_multi>add_single>query | method_change | 8 |
| W017 | 기본 다품목 | english | add_multi>add_more>add_single | back_to_menu | 10 |
| W018 | 기본 다품목 | direct_take | add_burger_ask>add_single>add_single>add_single | no_points | 9 |
| W019 | 기본 다품목 | direct_take | add_single>set_qty | points_inline | 6 |
| W020 | 기본 다품목 | menu_first | add_multi>add_more | method_change | 9 |
| W021 | 기본 다품목 | english | add_multi>add_burger_ask | points_inline | 8 |
| W022 | 기본 다품목 | direct_take | add_burger_ask>add_burger_ask>add_burger_ask | back_to_menu | 12 |
| W023 | 기본 다품목 | direct_take | add_burger_ask>add_single>query | no_points | 8 |
| W024 | 기본 다품목 | greet_take | add_multi>add_single | method_change | 8 |
| W025 | 기본 다품목 | stt_naejang | add_single>add_single>add_burger_ask | back_to_menu | 11 |
| W026 | 편집 | orderType_screen | add_single>reduce_qty>remove_line>add_single>undo_last>add_multi | no_points | 10 |
| W027 | 편집 | orderType_screen | add_multi>set_qty>reduce_qty>remove_line>readd_removed>set_qty>query | points_phone | 12 |
| W028 | 편집 | menu_first | add_multi>remove_line>add_single>reduce_qty>add_burger_ask>undo_last>reduce_qty | no_points | 14 |
| W029 | 편집 | direct_take | add_single>undo_last>add_multi>reduce_qty>remove_line | back_to_menu | 11 |
| W030 | 편집 | stt_naejang | add_single>undo_last>add_multi>remove_line | no_points | 9 |
| W031 | 편집 | menu_first | add_multi>remove_line>readd_removed>reduce_qty>set_qty>add_multi | no_points | 12 |
| W032 | 편집 | orderType_screen | add_multi>reduce_qty>remove_line>readd_removed>add_single>undo_last | method_change | 11 |
| W033 | 편집 | stt_naejang | add_multi>remove_line>reduce_qty>set_qty>add_single | points_phone | 11 |
| W034 | 편집 | touch_type | add_multi>remove_line>readd_removed>reduce_qty>add_single>undo_last | method_change | 10 |
| W035 | 편집 | orderType_screen | add_single>add_burger_ask>remove_line>readd_removed>add_more>undo_last>add_multi | no_points | 12 |
| W036 | 편집 | greet_dine | add_burger_ask>undo_last>add_single>remove_line>add_single | points_phone | 12 |
| W037 | 편집 | direct_take | add_multi>add_burger_ask>undo_last>remove_line>readd_removed>reduce_qty>add_more | method_change | 13 |
| W038 | 편집 | stt_naejang | add_burger_ask>remove_line>add_burger_ask>undo_last>add_burger_ask | back_to_menu | 15 |
| W039 | 편집 | menu_first | add_multi>remove_line>readd_removed>reduce_qty>add_single | back_to_menu | 13 |
| W040 | 편집 | stt_naejang | add_multi>add_more>undo_last>reduce_qty>remove_line>readd_removed>add_single | method_change | 13 |
| W041 | 편집 | greet_dine | add_single>add_burger_ask>undo_last>remove_line>add_burger_ask>add_more>reduce_qty | points_phone | 15 |
| W042 | 편집 | menu_first | add_burger_ask>undo_last>add_burger_ask>remove_line>add_multi | back_to_menu | 15 |
| W043 | 편집 | direct_take | add_multi>reduce_qty>remove_line>readd_removed>add_burger_ask | no_points | 10 |
| W044 | 편집 | orderType_screen | add_burger_ask>undo_last>add_burger_ask>remove_line>add_single>query | back_to_menu | 14 |
| W045 | 편집 | greet_take | add_multi>reduce_qty>remove_line>readd_removed>add_single | points_phone | 11 |
| W046 | 편집 | orderType_screen | add_burger_ask>remove_line>add_single>reduce_qty>query | no_points | 10 |
| W047 | 편집 | greet_take | add_burger_ask>add_more>undo_last>remove_line>add_multi>reduce_qty>add_multi | method_change | 14 |
| W048 | 편집 | english | add_burger_ask>undo_last>add_burger_ask>remove_line>add_single>undo_last>add_single | back_to_menu | 16 |
| W049 | 편집 | direct_take | add_single>add_multi>remove_line>readd_removed>reduce_qty>add_burger_ask>undo_last | no_points | 12 |
| W050 | 편집 | stt_naejang | add_multi>add_more>undo_last>reduce_qty>remove_line>readd_removed>add_multi | points_phone | 13 |
| W051 | 편집 | direct_take | add_single>undo_last>add_burger_ask>remove_line>add_burger_ask | no_points | 11 |
| W052 | 편집 | touch_type | add_single>set_qty>remove_line>add_burger_ask>undo_last>add_burger_ask>add_single | no_points | 12 |
| W053 | 편집 | greet_take | add_burger_ask>remove_line>add_burger_ask>undo_last>add_single | method_change | 13 |
| W054 | 편집 | menu_first | add_single>reduce_qty>add_single>remove_line>add_single>undo_last>add_burger_ask | back_to_menu | 16 |
| W055 | 편집 | greet_dine | add_multi>reduce_qty>remove_line>readd_removed>add_burger_ask | no_points | 11 |
| W056 | 세트 옵션 | greet_dine | add_single>add_set_oneshot>change_side>add_second_set>add_single>convert_to_set | no_points | 11 |
| W057 | 세트 옵션 | stt_naejang | add_single>add_set_ask>change_both>change_drink>change_side>add_second_set | points_phone | 14 |
| W058 | 세트 옵션 | direct_take | add_set_oneshot>change_drink>convert_to_single>convert_to_set>add_second_set>add_set_oneshot | back_to_menu | 12 |
| W059 | 세트 옵션 | menu_first | add_set_oneshot>add_set_oneshot>change_both>add_exclusion | back_to_menu | 12 |
| W060 | 세트 옵션 | touch_type | add_set_oneshot>add_set_ask>add_set_ask>add_set_ask | no_points | 13 |
| W061 | 세트 옵션 | touch_type | add_set_oneshot>change_drink>convert_to_single>add_exclusion | points_inline | 7 |
| W062 | 세트 옵션 | menu_first | add_set_ask>change_side>change_drink | back_to_menu | 13 |
| W063 | 세트 옵션 | greet_dine | add_set_oneshot>add_single>add_set_oneshot | back_to_menu | 10 |
| W064 | 세트 옵션 | greet_dine | add_set_ask>add_second_set>add_set_oneshot>add_set_ask>change_side | no_points | 14 |
| W065 | 세트 옵션 | orderType_screen | add_set_ask>change_drink>convert_to_single>convert_to_set | points_inline | 10 |
| W066 | 세트 옵션 | touch_type | add_set_ask>change_side>change_both | no_points | 8 |
| W067 | 세트 옵션 | greet_take | add_set_oneshot>add_set_ask>add_set_oneshot>add_single>add_set_ask>add_single | no_points | 15 |
| W068 | 세트 옵션 | menu_first | add_set_ask>change_both>convert_to_single>convert_to_set>add_second_set>add_set_ask | method_change | 17 |
| W069 | 세트 옵션 | greet_dine | add_single>add_exclusion>convert_to_set>convert_to_single | points_inline | 9 |
| W070 | 세트 옵션 | menu_first | add_set_oneshot>add_set_ask>change_drink | points_inline | 11 |
| W071 | 세트 옵션 | orderType_screen | add_set_oneshot>add_set_oneshot>add_single>add_set_oneshot | no_points | 8 |
| W072 | 세트 옵션 | english | add_set_oneshot>add_set_ask>add_second_set | no_points | 10 |
| W073 | 세트 옵션 | orderType_screen | add_set_ask>convert_to_single>convert_to_set>change_both | no_points | 10 |
| W074 | 세트 옵션 | orderType_screen | add_set_ask>add_second_set>add_set_ask>add_set_ask>change_both>change_drink | no_points | 16 |
| W075 | 세트 옵션 | greet_take | add_single>add_set_ask>change_drink | method_change | 11 |
| W076 | 세트 옵션 | touch_type | add_single>add_set_oneshot>add_set_ask | method_change | 9 |
| W077 | 세트 옵션 | english | add_set_ask>convert_to_single>convert_to_set>add_second_set>add_single | points_inline | 12 |
| W078 | 세트 옵션 | stt_naejang | add_set_oneshot>add_set_ask>change_both>add_second_set | back_to_menu | 13 |
| W079 | 세트 옵션 | touch_type | add_single>convert_to_set>change_both>change_side>convert_to_single | no_points | 8 |
| W080 | 세트 옵션 | greet_dine | add_set_ask>change_drink>add_exclusion>change_side>add_second_set>add_single | no_points | 13 |
| W081 | 종합 | direct_take | touch_add>convert_to_set>convert_to_single>remove_line>add_single>undo_last>add_single | back_to_menu | 12 |
| W082 | 종합 | touch_type | touch_add>remove_line>touch_add>add_multi>remove_line>remove_line>add_set_oneshot>undo_last | no_points | 9 |
| W083 | 종합 | menu_first | touch_add>remove_line>add_set_oneshot>undo_last>add_multi>convert_to_set>change_side | points_inline | 12 |
| W084 | 종합 | orderType_screen | touch_add>remove_line>add_burger_ask>undo_last>add_multi | no_points | 9 |
| W085 | 종합 | stt_naejang | add_single>touch_add>remove_line>reduce_qty>convert_to_set>convert_to_single>add_single>undo_last | no_points | 12 |
| W086 | 종합 | touch_type | add_single>undo_last>touch_add>remove_line>add_set_ask>convert_to_single>convert_to_set>change_side | method_change | 13 |
| W087 | 종합 | direct_take | touch_add>remove_line>add_multi>add_multi>add_multi | no_points | 8 |
| W088 | 종합 | menu_first | touch_add>remove_line>add_multi>convert_to_set>convert_to_single | no_points | 10 |
| W089 | 종합 | orderType_screen | add_set_oneshot>remove_line>touch_add>set_qty>convert_to_set>convert_to_single>add_more>undo_last | points_inline | 11 |
| W090 | 종합 | english | add_burger_ask>undo_last>touch_add>convert_to_set>change_side>convert_to_single>remove_line>touch_add | points_inline | 12 |
| W091 | 종합 | greet_take | touch_add>add_burger_ask>remove_line>convert_to_set>change_side>convert_to_single>set_qty>set_qty | points_phone | 14 |
| W092 | 종합 | stt_naejang | add_set_ask>touch_add>convert_to_single>convert_to_set>remove_line>change_side>add_set_oneshot>undo_last | no_points | 14 |
| W093 | 종합 | stt_naejang | touch_add>remove_line>add_single>undo_last>add_set_ask>convert_to_single>convert_to_set | points_inline | 13 |
| W094 | 종합 | greet_take | add_multi>remove_line>touch_add>convert_to_set>convert_to_single>set_qty>add_more>undo_last | no_points | 12 |
| W095 | 종합 | greet_take | touch_add>remove_line>add_burger_ask>convert_to_set>convert_to_single>query | back_to_menu | 13 |
| W096 | 종합 | stt_naejang | add_burger_ask>touch_add>remove_line>convert_to_set>convert_to_single>add_single>undo_last>add_exclusion | no_points | 13 |
| W097 | 종합 | orderType_screen | add_burger_ask>undo_last>touch_add>convert_to_set>change_side>convert_to_single>remove_line>touch_add | no_points | 11 |
| W098 | 종합 | stt_naejang | touch_add>remove_line>touch_add>convert_to_set>convert_to_single>remove_line>add_single | no_points | 10 |
| W099 | 종합 | english | touch_add>remove_line>add_set_ask>convert_to_single>convert_to_set | back_to_menu | 13 |
| W100 | 종합 | menu_first | add_burger_ask>touch_add>remove_line>reduce_qty>convert_to_set>convert_to_single>query>add_set_oneshot | no_points | 14 |

## 3. 시나리오별 발화와 기대 장바구니

`→`는 그 턴이 끝난 뒤 장바구니가 가져야 할 내용이다. 화살표가 없는 턴은 장바구니 검사가 없다.

```
W001  [기본 다품목] touch_type · add_burger_ask>add_burger_ask>set_qty · no_points
    [state] screen=menu, order_type=dine-in
    말: 치즈버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치즈 버거×1
    말: 모짜렐라버거 하나 줘   → 치즈 버거×1
    말: 단품으로 줘   → 치즈 버거×1, 모짜렐라 버거×1
    말: 모짜렐라버거 단품 3개로 바꿔줘   → 치즈 버거×1, 모짜렐라 버거×3
    말: 결제할게요   → 치즈 버거×1, 모짜렐라 버거×3
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W002  [기본 다품목] menu_first · add_single>add_burger_ask · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 치킨가슴살버거 단품 세 개 담아줘   → 치킨 가슴살 버거×3
    말: 더블불고기버거 하나 줘   → 치킨 가슴살 버거×3
    말: 단품으로 줘   → 치킨 가슴살 버거×3, 더블 불고기 버거×1
    말: 결제할게요   → 치킨 가슴살 버거×3, 더블 불고기 버거×1
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W003  [기본 다품목] greet_dine · add_multi>add_single · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 오렌지주스 세 잔 그리고 F버거 단품 하나 그리고 콘샐러드 하나 담아줘   → 오렌지 주스×3, F 버거×1, 콘샐러드×1
    말: 데리버거 단품으로 세 개 줘   → 오렌지 주스×3, F 버거×1, 콘샐러드×1, 데리버거×3
    말: 결제할게요   → 오렌지 주스×3, F 버거×1, 콘샐러드×1, 데리버거×3
    말: 포인트 적립할게요
    말: 01089969793
    말: 카드로 할게요
```

```
W004  [기본 다품목] direct_take · add_burger_ask>add_burger_ask>add_burger_ask · method_change
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 치킨가슴살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 가슴살 버거×1
    말: 비건버거 하나 줘   → 치킨 가슴살 버거×1
    말: 단품으로 줘   → 치킨 가슴살 버거×1, 비건 버거×1
    말: 비건버거 하나 줘   → 치킨 가슴살 버거×1, 비건 버거×1
    말: 단품으로 줘   → 치킨 가슴살 버거×1, 비건 버거×2
    말: 결제할게요   → 치킨 가슴살 버거×1, 비건 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W005  [기본 다품목] greet_take · add_burger_ask>add_single>add_more>add_burger_ask · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 치킨가슴살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 가슴살 버거×1
    말: 게살버거 단품으로 세 개 줘   → 치킨 가슴살 버거×1, 게살 버거×3
    말: 치킨가슴살버거 단품 두 개 더 줘   → 치킨 가슴살 버거×3, 게살 버거×3
    말: 치킨가슴살버거 하나 줘   → 치킨 가슴살 버거×3, 게살 버거×3
    말: 단품으로 줘   → 치킨 가슴살 버거×4, 게살 버거×3
    말: 결제할게요   → 치킨 가슴살 버거×4, 게살 버거×3
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W006  [기본 다품목] orderType_screen · add_burger_ask>set_qty>add_burger_ask · back_to_menu
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 치킨다릿살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 다릿살 버거×1
    말: 치킨다릿살버거 단품 4개로 바꿔줘   → 치킨 다릿살 버거×4
    말: F버거 하나 줘   → 치킨 다릿살 버거×4
    말: 단품으로 줘   → 치킨 다릿살 버거×4, F 버거×1
    말: 결제할게요   → 치킨 다릿살 버거×4, F 버거×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 치킨 다릿살 버거×4, F 버거×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W007  [기본 다품목] greet_take · add_multi>add_multi>add_more · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 치킨다릿살버거 단품 두 개 그리고 생수 두 잔 그리고 너겟 두 개 줘   → 치킨 다릿살 버거×2, 생수×2, 너겟(4조각)×2
    말: 콘샐러드 세 개 그리고 뽀로로음료수 한 잔 담아줘   → 치킨 다릿살 버거×2, 생수×2, 너겟(4조각)×2, 콘샐러드×3, 뽀로로 음료수×1
    말: 콘샐러드 하나 더 줘   → 치킨 다릿살 버거×2, 생수×2, 너겟(4조각)×2, 콘샐러드×4, 뽀로로 음료수×1
    말: 결제할게요   → 치킨 다릿살 버거×2, 생수×2, 너겟(4조각)×2, 콘샐러드×4, 뽀로로 음료수×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W008  [기본 다품목] touch_type · add_burger_ask>add_single>add_more>query · points_phone
    [state] screen=menu, order_type=takeout
    말: 치킨다릿살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 다릿살 버거×1
    말: 모짜렐라버거 단품으로 두 개 줘   → 치킨 다릿살 버거×1, 모짜렐라 버거×2
    말: 모짜렐라버거 단품 하나 더 줘   → 치킨 다릿살 버거×1, 모짜렐라 버거×3
    말: 가장 저렴한 버거가 뭐예요?   → 치킨 다릿살 버거×1, 모짜렐라 버거×3
    말: 결제할게요   → 치킨 다릿살 버거×1, 모짜렐라 버거×3
    말: 포인트 적립할게요
    말: 공일공 팔사사일 육이이육
    말: 삼성페이로 할게요
```

```
W009  [기본 다품목] touch_type · add_burger_ask>add_multi · back_to_menu
    [state] screen=menu, order_type=dine-in
    말: F버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → F 버거×1
    말: 오렌지주스 세 잔 그리고 치킨가슴살버거 단품 두 개 그리고 치즈스틱 세 개 줘   → F 버거×1, 오렌지 주스×3, 치킨 가슴살 버거×2, 치즈스틱(2개)×3
    말: 결제할게요   → F 버거×1, 오렌지 주스×3, 치킨 가슴살 버거×2, 치즈스틱(2개)×3
    말: 아 잠깐 오렌지주스도 한 잔 추가할게요   → F 버거×1, 오렌지 주스×4, 치킨 가슴살 버거×2, 치즈스틱(2개)×3
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W010  [기본 다품목] direct_take · add_single>add_more>add_multi · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 불고기버거 단품 하나 담아줘   → 불고기 버거×1
    말: 불고기버거 단품 두 개 더 줘   → 불고기 버거×3
    말: 생수 세 잔 그리고 모짜렐라버거 단품 하나 그리고 너겟 두 개 줘   → 불고기 버거×3, 생수×3, 모짜렐라 버거×1, 너겟(4조각)×2
    말: 결제할게요   → 불고기 버거×3, 생수×3, 모짜렐라 버거×1, 너겟(4조각)×2
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W011  [기본 다품목] greet_dine · add_burger_ask>set_qty>add_more · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 치즈버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치즈 버거×1
    말: 치즈버거 단품 2개로 바꿔줘   → 치즈 버거×2
    말: 치즈버거 단품 두 개 더 줘   → 치즈 버거×4
    말: 결제할게요   → 치즈 버거×4
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 치즈 버거×4, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W012  [기본 다품목] greet_take · add_burger_ask>add_single>add_single · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 게살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 게살 버거×1
    말: 게살버거 단품 두 개 담아줘   → 게살 버거×3
    말: 그릴드비프버거 단품 하나 담아줘   → 게살 버거×3, 그릴드 비프 버거×1
    말: 결제할게요   → 게살 버거×3, 그릴드 비프 버거×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W013  [기본 다품목] stt_naejang · add_burger_ask>add_burger_ask · points_inline
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 데리버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 데리버거×1
    말: 데리버거 하나 줘   → 데리버거×1
    말: 단품으로 줘   → 데리버거×2
    말: 결제할게요   → 데리버거×2
    말: 네 적립할게요 01013419290
    말: 카카오페이로 할게요
```

```
W014  [기본 다품목] touch_type · add_burger_ask>add_burger_ask>add_single>add_burger_ask · back_to_menu
    [state] screen=menu, order_type=takeout
    말: 비건버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 비건 버거×1
    말: 불고기버거 하나 줘   → 비건 버거×1
    말: 단품으로 줘   → 비건 버거×1, 불고기 버거×1
    말: 그릴드비프버거 단품 하나 담아줘   → 비건 버거×1, 불고기 버거×1, 그릴드 비프 버거×1
    말: 불고기버거 하나 줘   → 비건 버거×1, 불고기 버거×1, 그릴드 비프 버거×1
    말: 단품으로 줘   → 비건 버거×1, 불고기 버거×2, 그릴드 비프 버거×1
    말: 결제할게요   → 비건 버거×1, 불고기 버거×2, 그릴드 비프 버거×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 비건 버거×1, 불고기 버거×2, 그릴드 비프 버거×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W015  [기본 다품목] greet_dine · add_single>add_more>add_multi · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 비건버거 단품으로 하나 줘   → 비건 버거×1
    말: 비건버거 단품 하나 더 줘   → 비건 버거×2
    말: 모짜렐라버거 단품 하나 그리고 뽀로로음료수 한 잔 담아줘   → 비건 버거×2, 모짜렐라 버거×1, 뽀로로 음료수×1
    말: 결제할게요   → 비건 버거×2, 모짜렐라 버거×1, 뽀로로 음료수×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W016  [기본 다품목] orderType_screen · add_multi>add_single>query · method_change
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 너겟 세 개 그리고 생수 한 잔 담아줘   → 너겟(4조각)×3, 생수×1
    말: 모짜렐라버거 단품 두 개 담아줘   → 너겟(4조각)×3, 생수×1, 모짜렐라 버거×2
    말: 지금 뭐 담겼어?   → 너겟(4조각)×3, 생수×1, 모짜렐라 버거×2
    말: 결제할게요   → 너겟(4조각)×3, 생수×1, 모짜렐라 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W017  [기본 다품목] english · add_multi>add_more>add_single · back_to_menu
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 오렌지주스 한 잔 그리고 데리버거 단품 하나 줘   → 오렌지 주스×1, 데리버거×1
    말: 데리버거 단품 두 개 더 줘   → 오렌지 주스×1, 데리버거×3
    말: 데리버거 단품 하나 담아줘   → 오렌지 주스×1, 데리버거×4
    말: 결제할게요   → 오렌지 주스×1, 데리버거×4
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 오렌지 주스×1, 데리버거×4, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W018  [기본 다품목] direct_take · add_burger_ask>add_single>add_single>add_single · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 치킨다릿살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 다릿살 버거×1
    말: F버거 단품 세 개 주세요   → 치킨 다릿살 버거×1, F 버거×3
    말: 데리버거 단품 세 개 주세요   → 치킨 다릿살 버거×1, F 버거×3, 데리버거×3
    말: 비건버거 단품 하나 주세요   → 치킨 다릿살 버거×1, F 버거×3, 데리버거×3, 비건 버거×1
    말: 결제할게요   → 치킨 다릿살 버거×1, F 버거×3, 데리버거×3, 비건 버거×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W019  [기본 다품목] direct_take · add_single>set_qty · points_inline
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 불고기버거 단품 세 개 주세요   → 불고기 버거×3
    말: 불고기버거 단품 4개로 바꿔줘   → 불고기 버거×4
    말: 결제할게요   → 불고기 버거×4
    말: 네 적립할게요 01001150779
    말: 카카오페이로 할게요
```

```
W020  [기본 다품목] menu_first · add_multi>add_more · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 콘샐러드 세 개 그리고 생수 두 잔 그리고 F버거 단품 하나 주세요   → 콘샐러드×3, 생수×2, F 버거×1
    말: 생수 두 개 더 줘   → 콘샐러드×3, 생수×4, F 버거×1
    말: 결제할게요   → 콘샐러드×3, 생수×4, F 버거×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W021  [기본 다품목] english · add_multi>add_burger_ask · points_inline
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 치킨가슴살버거 단품 하나 그리고 콘샐러드 하나 그리고 뽀로로음료수 한 잔 주세요   → 치킨 가슴살 버거×1, 콘샐러드×1, 뽀로로 음료수×1
    말: 더블치즈버거 하나 줘   → 치킨 가슴살 버거×1, 콘샐러드×1, 뽀로로 음료수×1
    말: 단품으로 줘   → 치킨 가슴살 버거×1, 콘샐러드×1, 뽀로로 음료수×1, 더블 치즈 버거×1
    말: 결제할게요   → 치킨 가슴살 버거×1, 콘샐러드×1, 뽀로로 음료수×1, 더블 치즈 버거×1
    말: 네 적립할게요 01011491590
    말: 현금으로 낼게요
```

```
W022  [기본 다품목] direct_take · add_burger_ask>add_burger_ask>add_burger_ask · back_to_menu
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: F버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → F 버거×1
    말: 그릴드비프버거 하나 줘   → F 버거×1
    말: 단품으로 줘   → F 버거×1, 그릴드 비프 버거×1
    말: F버거 하나 줘   → F 버거×1, 그릴드 비프 버거×1
    말: 단품으로 줘   → F 버거×2, 그릴드 비프 버거×1
    말: 결제할게요   → F 버거×2, 그릴드 비프 버거×1
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → F 버거×2, 그릴드 비프 버거×1, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W023  [기본 다품목] direct_take · add_burger_ask>add_single>query · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 새우버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 새우 버거×1
    말: 그릴드비프버거 단품으로 세 개 줘   → 새우 버거×1, 그릴드 비프 버거×3
    말: 지금 뭐 담겼어?   → 새우 버거×1, 그릴드 비프 버거×3
    말: 결제할게요   → 새우 버거×1, 그릴드 비프 버거×3
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W024  [기본 다품목] greet_take · add_multi>add_single · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 새우버거 단품 두 개 그리고 콘샐러드 세 개 그리고 오렌지주스 한 잔 줘   → 새우 버거×2, 콘샐러드×3, 오렌지 주스×1
    말: 불고기버거 단품 두 개 주세요   → 새우 버거×2, 콘샐러드×3, 오렌지 주스×1, 불고기 버거×2
    말: 결제할게요   → 새우 버거×2, 콘샐러드×3, 오렌지 주스×1, 불고기 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W025  [기본 다품목] stt_naejang · add_single>add_single>add_burger_ask · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 그릴드비프버거 단품 두 개 담아줘   → 그릴드 비프 버거×2
    말: 그릴드비프버거 단품 세 개 담아줘   → 그릴드 비프 버거×5
    말: 비건버거 하나 줘   → 그릴드 비프 버거×5
    말: 단품으로 줘   → 그릴드 비프 버거×5, 비건 버거×1
    말: 결제할게요   → 그릴드 비프 버거×5, 비건 버거×1
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 그릴드 비프 버거×5, 비건 버거×1, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W026  [편집] orderType_screen · add_single>reduce_qty>remove_line>add_single>undo_last>add_multi · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 모짜렐라버거 단품으로 세 개 줘   → 모짜렐라 버거×3
    말: 모짜렐라버거 단품 한 개 줄여줘   → 모짜렐라 버거×2
    말: 모짜렐라버거 단품 전부 빼줘   → (빈 장바구니)
    말: 데리버거 단품 세 개 주세요   → 데리버거×3
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 콘샐러드 하나 그리고 불고기버거 단품 세 개 그리고 뽀로로음료수 한 잔 담아줘   → 콘샐러드×1, 불고기 버거×3, 뽀로로 음료수×1
    말: 결제할게요   → 콘샐러드×1, 불고기 버거×3, 뽀로로 음료수×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W027  [편집] orderType_screen · add_multi>set_qty>reduce_qty>remove_line>readd_removed>set_qty>query · points_phone
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 코울슬로 하나 그리고 게살버거 단품 두 개 줘   → 코울슬로×1, 게살 버거×2
    말: 게살버거 단품 4개로 바꿔줘   → 코울슬로×1, 게살 버거×4
    말: 게살버거 단품 하나만 빼줘   → 코울슬로×1, 게살 버거×3
    말: 코울슬로 빼줘   → 게살 버거×3
    말: 아까 뺀 코울슬로 다시 담아줘   → 게살 버거×3, 코울슬로×1
    말: 코울슬로 2개로 바꿔줘   → 게살 버거×3, 코울슬로×2
    말: 지금 뭐 담겼어?   → 게살 버거×3, 코울슬로×2
    말: 결제할게요   → 게살 버거×3, 코울슬로×2
    말: 포인트 적립할게요
    말: 공일공 사칠일구 일구사팔
    말: 간편결제로 할게요
```

```
W028  [편집] menu_first · add_multi>remove_line>add_single>reduce_qty>add_burger_ask>undo_last>reduce_qty · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 콘샐러드 두 개 그리고 그릴드비프버거 단품 세 개 그리고 생수 한 잔 담아줘   → 콘샐러드×2, 그릴드 비프 버거×3, 생수×1
    말: 콘샐러드 전부 지워줘   → 그릴드 비프 버거×3, 생수×1
    말: F버거 단품 하나 담아줘   → 그릴드 비프 버거×3, 생수×1, F 버거×1
    말: 그릴드비프버거 단품 하나만 빼줘   → 그릴드 비프 버거×2, 생수×1, F 버거×1
    말: 불고기버거 하나 줘   → 그릴드 비프 버거×2, 생수×1, F 버거×1
    말: 단품으로 줘   → 그릴드 비프 버거×2, 생수×1, F 버거×1, 불고기 버거×1
    말: 방금 담은 거 취소해줘   → 그릴드 비프 버거×2, 생수×1, F 버거×1
    말: 그릴드비프버거 단품 하나만 빼줘   → 그릴드 비프 버거×1, 생수×1, F 버거×1
    말: 결제할게요   → 그릴드 비프 버거×1, 생수×1, F 버거×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W029  [편집] direct_take · add_single>undo_last>add_multi>reduce_qty>remove_line · back_to_menu
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: F버거 단품으로 하나 줘   → F 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 새우버거 단품 하나 그리고 너겟 두 개 담아줘   → 새우 버거×1, 너겟(4조각)×2
    말: 너겟 하나만 빼줘   → 새우 버거×1, 너겟(4조각)×1
    말: 새우버거 단품 빼줘   → 너겟(4조각)×1
    말: 결제할게요   → 너겟(4조각)×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 너겟(4조각)×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W030  [편집] stt_naejang · add_single>undo_last>add_multi>remove_line · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 비건버거 단품으로 두 개 줘   → 비건 버거×2
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 치즈스틱 하나 그리고 불고기버거 단품 두 개 주세요   → 치즈스틱(2개)×1, 불고기 버거×2
    말: 불고기버거 단품 전부 취소해줘   → 치즈스틱(2개)×1
    말: 결제할게요   → 치즈스틱(2개)×1
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W031  [편집] menu_first · add_multi>remove_line>readd_removed>reduce_qty>set_qty>add_multi · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 치킨다릿살버거 단품 세 개 그리고 치즈스틱 세 개 줘   → 치킨 다릿살 버거×3, 치즈스틱(2개)×3
    말: 치킨다릿살버거 단품 전부 빼줘   → 치즈스틱(2개)×3
    말: 아까 뺀 치킨다릿살버거 단품 다시 담아줘   → 치즈스틱(2개)×3, 치킨 다릿살 버거×3
    말: 치킨다릿살버거 단품 하나만 빼줘   → 치즈스틱(2개)×3, 치킨 다릿살 버거×2
    말: 치킨다릿살버거 단품 4개로 바꿔줘   → 치즈스틱(2개)×3, 치킨 다릿살 버거×4
    말: F버거 단품 두 개 그리고 코울슬로 하나 그리고 오렌지주스 세 잔 줘   → 치즈스틱(2개)×3, 치킨 다릿살 버거×4, F 버거×2, 코울슬로×1, 오렌지 주스×3
    말: 결제할게요   → 치즈스틱(2개)×3, 치킨 다릿살 버거×4, F 버거×2, 코울슬로×1, 오렌지 주스×3
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W032  [편집] orderType_screen · add_multi>reduce_qty>remove_line>readd_removed>add_single>undo_last · method_change
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 뽀로로음료수 두 잔 그리고 콘샐러드 세 개 그리고 불고기버거 단품 두 개 주세요   → 뽀로로 음료수×2, 콘샐러드×3, 불고기 버거×2
    말: 뽀로로음료수 한 개 줄여줘   → 뽀로로 음료수×1, 콘샐러드×3, 불고기 버거×2
    말: 불고기버거 단품 전부 지워줘   → 뽀로로 음료수×1, 콘샐러드×3
    말: 아까 뺀 불고기버거 단품 다시 담아줘   → 뽀로로 음료수×1, 콘샐러드×3, 불고기 버거×2
    말: 그릴드비프버거 단품으로 하나 줘   → 뽀로로 음료수×1, 콘샐러드×3, 불고기 버거×2, 그릴드 비프 버거×1
    말: 방금 담은 거 취소해줘   → 뽀로로 음료수×1, 콘샐러드×3, 불고기 버거×2
    말: 결제할게요   → 뽀로로 음료수×1, 콘샐러드×3, 불고기 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W033  [편집] stt_naejang · add_multi>remove_line>reduce_qty>set_qty>add_single · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 코울슬로 세 개 그리고 치킨다릿살버거 단품 두 개 그리고 뽀로로음료수 한 잔 담아줘   → 코울슬로×3, 치킨 다릿살 버거×2, 뽀로로 음료수×1
    말: 코울슬로 전부 취소해줘   → 치킨 다릿살 버거×2, 뽀로로 음료수×1
    말: 치킨다릿살버거 단품 한 개 줄여줘   → 치킨 다릿살 버거×1, 뽀로로 음료수×1
    말: 치킨다릿살버거 단품 3개로 바꿔줘   → 치킨 다릿살 버거×3, 뽀로로 음료수×1
    말: 치킨다릿살버거 단품으로 두 개 줘   → 치킨 다릿살 버거×5, 뽀로로 음료수×1
    말: 결제할게요   → 치킨 다릿살 버거×5, 뽀로로 음료수×1
    말: 포인트 적립할게요
    말: 공일공 육오공육 삼이구육
    말: 카드로 할게요
```

```
W034  [편집] touch_type · add_multi>remove_line>readd_removed>reduce_qty>add_single>undo_last · method_change
    [state] screen=menu, order_type=dine-in
    말: 뽀로로음료수 한 잔 그리고 치즈스틱 두 개 그리고 치즈버거 단품 세 개 줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×3
    말: 치즈버거 단품 전부 지워줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2
    말: 아까 뺀 치즈버거 단품 다시 담아줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×3
    말: 치즈버거 단품 하나만 빼줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×2
    말: 치킨가슴살버거 단품으로 하나 줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×2, 치킨 가슴살 버거×1
    말: 방금 담은 거 취소해줘   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×2
    말: 결제할게요   → 뽀로로 음료수×1, 치즈스틱(2개)×2, 치즈 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W035  [편집] orderType_screen · add_single>add_burger_ask>remove_line>readd_removed>add_more>undo_last>add_multi · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: F버거 단품 하나 주세요   → F 버거×1
    말: 불고기버거 하나 줘   → F 버거×1
    말: 단품으로 줘   → F 버거×1, 불고기 버거×1
    말: 불고기버거 단품 취소해줘   → F 버거×1
    말: 아까 뺀 불고기버거 단품 다시 담아줘   → F 버거×1, 불고기 버거×1
    말: 불고기버거 단품 하나 더 줘   → F 버거×1, 불고기 버거×2
    말: 방금 담은 거 취소해줘   → F 버거×1, 불고기 버거×1
    말: 콘샐러드 세 개 그리고 오렌지주스 한 잔 주세요   → F 버거×1, 불고기 버거×1, 콘샐러드×3, 오렌지 주스×1
    말: 결제할게요   → F 버거×1, 불고기 버거×1, 콘샐러드×3, 오렌지 주스×1
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W036  [편집] greet_dine · add_burger_ask>undo_last>add_single>remove_line>add_single · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 게살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 게살 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 게살버거 단품 하나 주세요   → 게살 버거×1
    말: 게살버거 단품 빼줘   → (빈 장바구니)
    말: 그릴드비프버거 단품 두 개 주세요   → 그릴드 비프 버거×2
    말: 결제할게요   → 그릴드 비프 버거×2
    말: 포인트 적립할게요
    말: 공일공 삼팔공구 육오사이
    말: 삼성페이로 할게요
```

```
W037  [편집] direct_take · add_multi>add_burger_ask>undo_last>remove_line>readd_removed>reduce_qty>add_more · method_change
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 코울슬로 두 개 그리고 더블불고기버거 단품 두 개 주세요   → 코울슬로×2, 더블 불고기 버거×2
    말: 더블불고기버거 하나 줘   → 코울슬로×2, 더블 불고기 버거×2
    말: 단품으로 줘   → 코울슬로×2, 더블 불고기 버거×3
    말: 방금 담은 거 취소해줘   → 코울슬로×2, 더블 불고기 버거×2
    말: 코울슬로 전부 취소해줘   → 더블 불고기 버거×2
    말: 아까 뺀 코울슬로 다시 담아줘   → 더블 불고기 버거×2, 코울슬로×2
    말: 더블불고기버거 단품 한 개 줄여줘   → 더블 불고기 버거×1, 코울슬로×2
    말: 코울슬로 두 개 더 줘   → 더블 불고기 버거×1, 코울슬로×4
    말: 결제할게요   → 더블 불고기 버거×1, 코울슬로×4
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W038  [편집] stt_naejang · add_burger_ask>remove_line>add_burger_ask>undo_last>add_burger_ask · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 지워줘   → (빈 장바구니)
    말: 더블불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 불고기 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 더블불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 불고기 버거×1
    말: 결제할게요   → 더블 불고기 버거×1
    말: 아 잠깐 오렌지주스도 한 잔 추가할게요   → 더블 불고기 버거×1, 오렌지 주스×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W039  [편집] menu_first · add_multi>remove_line>readd_removed>reduce_qty>add_single · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 더블불고기버거 단품 하나 그리고 뽀로로음료수 두 잔 주세요   → 더블 불고기 버거×1, 뽀로로 음료수×2
    말: 더블불고기버거 단품 지워줘   → 뽀로로 음료수×2
    말: 아까 뺀 더블불고기버거 단품 다시 담아줘   → 뽀로로 음료수×2, 더블 불고기 버거×1
    말: 뽀로로음료수 하나만 빼줘   → 뽀로로 음료수×1, 더블 불고기 버거×1
    말: 더블치즈버거 단품 두 개 담아줘   → 뽀로로 음료수×1, 더블 불고기 버거×1, 더블 치즈 버거×2
    말: 결제할게요   → 뽀로로 음료수×1, 더블 불고기 버거×1, 더블 치즈 버거×2
    말: 아 잠깐 오렌지주스도 한 잔 추가할게요   → 뽀로로 음료수×1, 더블 불고기 버거×1, 더블 치즈 버거×2, 오렌지 주스×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W040  [편집] stt_naejang · add_multi>add_more>undo_last>reduce_qty>remove_line>readd_removed>add_single · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 오렌지주스 한 잔 그리고 불고기버거 단품 두 개 그리고 너겟 두 개 줘   → 오렌지 주스×1, 불고기 버거×2, 너겟(4조각)×2
    말: 너겟 하나 더 줘   → 오렌지 주스×1, 불고기 버거×2, 너겟(4조각)×3
    말: 방금 담은 거 취소해줘   → 오렌지 주스×1, 불고기 버거×2, 너겟(4조각)×2
    말: 너겟 한 개 줄여줘   → 오렌지 주스×1, 불고기 버거×2, 너겟(4조각)×1
    말: 오렌지주스 취소해줘   → 불고기 버거×2, 너겟(4조각)×1
    말: 아까 뺀 오렌지주스 다시 담아줘   → 불고기 버거×2, 너겟(4조각)×1, 오렌지 주스×1
    말: 불고기버거 단품 하나 담아줘   → 불고기 버거×3, 너겟(4조각)×1, 오렌지 주스×1
    말: 결제할게요   → 불고기 버거×3, 너겟(4조각)×1, 오렌지 주스×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W041  [편집] greet_dine · add_single>add_burger_ask>undo_last>remove_line>add_burger_ask>add_more>reduce_qty · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 치킨가슴살버거 단품 하나 주세요   → 치킨 가슴살 버거×1
    말: 그릴드비프버거 하나 줘   → 치킨 가슴살 버거×1
    말: 단품으로 줘   → 치킨 가슴살 버거×1, 그릴드 비프 버거×1
    말: 방금 담은 거 취소해줘   → 치킨 가슴살 버거×1
    말: 치킨가슴살버거 단품 취소해줘   → (빈 장바구니)
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 두 개 더 줘   → 그릴드 비프 버거×3
    말: 그릴드비프버거 단품 한 개 줄여줘   → 그릴드 비프 버거×2
    말: 결제할게요   → 그릴드 비프 버거×2
    말: 포인트 적립할게요
    말: 01094556628
    말: 카카오페이로 할게요
```

```
W042  [편집] menu_first · add_burger_ask>undo_last>add_burger_ask>remove_line>add_multi · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 새우버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 새우 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 지워줘   → (빈 장바구니)
    말: 오렌지주스 한 잔 그리고 치즈스틱 하나 그리고 모짜렐라버거 단품 두 개 줘   → 오렌지 주스×1, 치즈스틱(2개)×1, 모짜렐라 버거×2
    말: 결제할게요   → 오렌지 주스×1, 치즈스틱(2개)×1, 모짜렐라 버거×2
    말: 아 잠깐 생수도 한 잔 추가할게요   → 오렌지 주스×1, 치즈스틱(2개)×1, 모짜렐라 버거×2, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W043  [편집] direct_take · add_multi>reduce_qty>remove_line>readd_removed>add_burger_ask · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 콘샐러드 두 개 그리고 불고기버거 단품 두 개 줘   → 콘샐러드×2, 불고기 버거×2
    말: 불고기버거 단품 하나만 빼줘   → 콘샐러드×2, 불고기 버거×1
    말: 불고기버거 단품 취소해줘   → 콘샐러드×2
    말: 아까 뺀 불고기버거 단품 다시 담아줘   → 콘샐러드×2, 불고기 버거×1
    말: F버거 하나 줘   → 콘샐러드×2, 불고기 버거×1
    말: 단품으로 줘   → 콘샐러드×2, 불고기 버거×1, F 버거×1
    말: 결제할게요   → 콘샐러드×2, 불고기 버거×1, F 버거×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W044  [편집] orderType_screen · add_burger_ask>undo_last>add_burger_ask>remove_line>add_single>query · back_to_menu
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 비건버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 비건 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 데리버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 데리버거×1
    말: 데리버거 단품 빼줘   → (빈 장바구니)
    말: 비건버거 단품으로 하나 줘   → 비건 버거×1
    말: 장바구니에 뭐 있는지 알려줘   → 비건 버거×1
    말: 결제할게요   → 비건 버거×1
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 비건 버거×1, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W045  [편집] greet_take · add_multi>reduce_qty>remove_line>readd_removed>add_single · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 너겟 하나 그리고 데리버거 단품 세 개 담아줘   → 너겟(4조각)×1, 데리버거×3
    말: 데리버거 단품 하나만 빼줘   → 너겟(4조각)×1, 데리버거×2
    말: 너겟 지워줘   → 데리버거×2
    말: 아까 뺀 너겟 다시 담아줘   → 데리버거×2, 너겟(4조각)×1
    말: 새우버거 단품 세 개 주세요   → 데리버거×2, 너겟(4조각)×1, 새우 버거×3
    말: 결제할게요   → 데리버거×2, 너겟(4조각)×1, 새우 버거×3
    말: 포인트 적립할게요
    말: 01012229724
    말: 카카오페이로 할게요
```

```
W046  [편집] orderType_screen · add_burger_ask>remove_line>add_single>reduce_qty>query · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 더블불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품 지워줘   → (빈 장바구니)
    말: 더블불고기버거 단품 두 개 주세요   → 더블 불고기 버거×2
    말: 더블불고기버거 단품 하나만 빼줘   → 더블 불고기 버거×1
    말: 장바구니에 뭐 있는지 알려줘   → 더블 불고기 버거×1
    말: 결제할게요   → 더블 불고기 버거×1
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W047  [편집] greet_take · add_burger_ask>add_more>undo_last>remove_line>add_multi>reduce_qty>add_multi · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 하나 더 줘   → 그릴드 비프 버거×2
    말: 방금 담은 거 취소해줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 빼줘   → (빈 장바구니)
    말: 더블불고기버거 단품 하나 그리고 콘샐러드 두 개 그리고 생수 한 잔 줘   → 더블 불고기 버거×1, 콘샐러드×2, 생수×1
    말: 콘샐러드 하나만 빼줘   → 더블 불고기 버거×1, 콘샐러드×1, 생수×1
    말: 더블불고기버거 단품 하나 그리고 오렌지주스 두 잔 줘   → 더블 불고기 버거×2, 콘샐러드×1, 생수×1, 오렌지 주스×2
    말: 결제할게요   → 더블 불고기 버거×2, 콘샐러드×1, 생수×1, 오렌지 주스×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W048  [편집] english · add_burger_ask>undo_last>add_burger_ask>remove_line>add_single>undo_last>add_single · back_to_menu
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 데리버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 데리버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 게살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 게살 버거×1
    말: 게살버거 단품 지워줘   → (빈 장바구니)
    말: 데리버거 단품 하나 담아줘   → 데리버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 게살버거 단품 하나 담아줘   → 게살 버거×1
    말: 결제할게요   → 게살 버거×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 게살 버거×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W049  [편집] direct_take · add_single>add_multi>remove_line>readd_removed>reduce_qty>add_burger_ask>undo_last · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 게살버거 단품으로 하나 줘   → 게살 버거×1
    말: 모짜렐라버거 단품 하나 그리고 오렌지주스 두 잔 주세요   → 게살 버거×1, 모짜렐라 버거×1, 오렌지 주스×2
    말: 게살버거 단품 취소해줘   → 모짜렐라 버거×1, 오렌지 주스×2
    말: 아까 뺀 게살버거 단품 다시 담아줘   → 모짜렐라 버거×1, 오렌지 주스×2, 게살 버거×1
    말: 오렌지주스 하나만 빼줘   → 모짜렐라 버거×1, 오렌지 주스×1, 게살 버거×1
    말: 모짜렐라버거 하나 줘   → 모짜렐라 버거×1, 오렌지 주스×1, 게살 버거×1
    말: 단품으로 줘   → 모짜렐라 버거×2, 오렌지 주스×1, 게살 버거×1
    말: 방금 담은 거 취소해줘   → 모짜렐라 버거×1, 오렌지 주스×1, 게살 버거×1
    말: 결제할게요   → 모짜렐라 버거×1, 오렌지 주스×1, 게살 버거×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W050  [편집] stt_naejang · add_multi>add_more>undo_last>reduce_qty>remove_line>readd_removed>add_multi · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 너겟 세 개 그리고 그릴드비프버거 단품 하나 줘   → 너겟(4조각)×3, 그릴드 비프 버거×1
    말: 너겟 두 개 더 줘   → 너겟(4조각)×5, 그릴드 비프 버거×1
    말: 방금 담은 거 취소해줘   → 너겟(4조각)×3, 그릴드 비프 버거×1
    말: 너겟 하나만 빼줘   → 너겟(4조각)×2, 그릴드 비프 버거×1
    말: 그릴드비프버거 단품 지워줘   → 너겟(4조각)×2
    말: 아까 뺀 그릴드비프버거 단품 다시 담아줘   → 너겟(4조각)×2, 그릴드 비프 버거×1
    말: 치즈버거 단품 세 개 그리고 생수 두 잔 주세요   → 너겟(4조각)×2, 그릴드 비프 버거×1, 치즈 버거×3, 생수×2
    말: 결제할게요   → 너겟(4조각)×2, 그릴드 비프 버거×1, 치즈 버거×3, 생수×2
    말: 포인트 적립할게요
    말: 01035628352
    말: 카카오페이로 할게요
```

```
W051  [편집] direct_take · add_single>undo_last>add_burger_ask>remove_line>add_burger_ask · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 더블치즈버거 단품 두 개 주세요   → 더블 치즈 버거×2
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 불고기 버거×1
    말: 불고기버거 단품 취소해줘   → (빈 장바구니)
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 결제할게요   → 그릴드 비프 버거×1
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W052  [편집] touch_type · add_single>set_qty>remove_line>add_burger_ask>undo_last>add_burger_ask>add_single · no_points
    [state] screen=menu, order_type=dine-in
    말: 데리버거 단품 세 개 주세요   → 데리버거×3
    말: 데리버거 단품 5개로 바꿔줘   → 데리버거×5
    말: 데리버거 단품 전부 지워줘   → (빈 장바구니)
    말: 더블불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 불고기 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 더블치즈버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 치즈 버거×1
    말: 더블치즈버거 단품으로 두 개 줘   → 더블 치즈 버거×3
    말: 결제할게요   → 더블 치즈 버거×3
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W053  [편집] greet_take · add_burger_ask>remove_line>add_burger_ask>undo_last>add_single · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 치킨가슴살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 가슴살 버거×1
    말: 치킨가슴살버거 단품 빼줘   → (빈 장바구니)
    말: 치킨가슴살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 가슴살 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 치킨가슴살버거 단품 두 개 담아줘   → 치킨 가슴살 버거×2
    말: 결제할게요   → 치킨 가슴살 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W054  [편집] menu_first · add_single>reduce_qty>add_single>remove_line>add_single>undo_last>add_burger_ask · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 데리버거 단품 두 개 담아줘   → 데리버거×2
    말: 데리버거 단품 한 개 줄여줘   → 데리버거×1
    말: 데리버거 단품 하나 주세요   → 데리버거×2
    말: 데리버거 단품 전부 빼줘   → (빈 장바구니)
    말: 데리버거 단품 하나 주세요   → 데리버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 데리버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 데리버거×1
    말: 결제할게요   → 데리버거×1
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 데리버거×1, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W055  [편집] greet_dine · add_multi>reduce_qty>remove_line>readd_removed>add_burger_ask · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 치즈스틱 두 개 그리고 그릴드비프버거 단품 하나 그리고 오렌지주스 한 잔 주세요   → 치즈스틱(2개)×2, 그릴드 비프 버거×1, 오렌지 주스×1
    말: 치즈스틱 한 개 줄여줘   → 치즈스틱(2개)×1, 그릴드 비프 버거×1, 오렌지 주스×1
    말: 그릴드비프버거 단품 지워줘   → 치즈스틱(2개)×1, 오렌지 주스×1
    말: 아까 뺀 그릴드비프버거 단품 다시 담아줘   → 치즈스틱(2개)×1, 오렌지 주스×1, 그릴드 비프 버거×1
    말: 데리버거 하나 줘   → 치즈스틱(2개)×1, 오렌지 주스×1, 그릴드 비프 버거×1
    말: 단품으로 줘   → 치즈스틱(2개)×1, 오렌지 주스×1, 그릴드 비프 버거×1, 데리버거×1
    말: 결제할게요   → 치즈스틱(2개)×1, 오렌지 주스×1, 그릴드 비프 버거×1, 데리버거×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W056  [세트 옵션] greet_dine · add_single>add_set_oneshot>change_side>add_second_set>add_single>convert_to_set · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 데리버거 단품 세 개 주세요   → 데리버거×3
    말: 데리버거 세트 하나, 사이드는 치즈스틱 음료는 오렌지주스로 줘   → 데리버거×3, 데리버거(세트 업그레이드/치즈스틱/오렌지주스)×1
    말: 데리버거 세트 사이드를 양념감자튀김로 바꿔줘   → 데리버거×3, 데리버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 데리버거 세트 하나 더, 이번엔 사이드는 치즈스틱 음료는 생수로 줘   → 데리버거×3, 데리버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 데리버거(세트 업그레이드/치즈스틱/생수)×1
    말: F버거 단품 하나 담아줘   → 데리버거×3, 데리버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 데리버거(세트 업그레이드/치즈스틱/생수)×1, F 버거×1
    말: F버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 콜라   → 데리버거×3, 데리버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 데리버거(세트 업그레이드/치즈스틱/생수)×1, F 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 결제할게요   → 데리버거×3, 데리버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 데리버거(세트 업그레이드/치즈스틱/생수)×1, F 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W057  [세트 옵션] stt_naejang · add_single>add_set_ask>change_both>change_drink>change_side>add_second_set · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 그릴드비프버거 단품 두 개 담아줘   → 그릴드 비프 버거×2
    말: 치킨다릿살버거 세트로 하나 줘   → 그릴드 비프 버거×2
    말: 사이드는 양념감자튀김   → 그릴드 비프 버거×2
    말: 콜라로 주세요   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/양념감자튀김/콜라)×1
    말: 치킨다릿살버거 세트 사이드는 치킨너겟 음료는 오렌지주스로 바꿔줘   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 치킨다릿살버거 세트 음료를 제로사이다로 바꿔줘   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 치킨다릿살버거 세트 사이드를 양념감자튀김로 바꿔줘   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 치킨다릿살버거 세트 하나 더, 이번엔 사이드는 치킨너겟 음료는 오렌지주스로 줘   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/양념감자튀김/제로사이다)×1, 치킨 다릿살 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 결제할게요   → 그릴드 비프 버거×2, 치킨 다릿살 버거(세트 업그레이드/양념감자튀김/제로사이다)×1, 치킨 다릿살 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 포인트 적립할게요
    말: 공일공 팔일오이 삼오팔일
    말: 카카오페이로 할게요
```

```
W058  [세트 옵션] direct_take · add_set_oneshot>change_drink>convert_to_single>convert_to_set>add_second_set>add_set_oneshot · back_to_menu
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    말: 치킨가슴살버거 세트 하나, 사이드는 치즈스틱 음료는 콜라로 줘   → 치킨 가슴살 버거(세트 업그레이드/치즈스틱/콜라)×1
    말: 치킨가슴살버거 세트 음료를 생수로 바꿔줘   → 치킨 가슴살 버거(세트 업그레이드/치즈스틱/생수)×1
    말: 치킨가슴살버거 세트 말고 단품으로 바꿔줘   → 치킨 가슴살 버거×1
    말: 치킨가슴살버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 제로사이다   → 치킨 가슴살 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 치킨가슴살버거 세트 하나 더, 이번엔 사이드는 양념감자튀김 음료는 사이다로 줘   → 치킨 가슴살 버거(세트 업그레이드/감자튀김/제로사이다)×1, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 데리버거 세트 하나, 사이드는 치킨너겟 음료는 오렌지주스로 줘   → 치킨 가슴살 버거(세트 업그레이드/감자튀김/제로사이다)×1, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/사이다)×1, 데리버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 결제할게요   → 치킨 가슴살 버거(세트 업그레이드/감자튀김/제로사이다)×1, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/사이다)×1, 데리버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 아 잠깐 뽀로로음료수도 한 잔 추가할게요   → 치킨 가슴살 버거(세트 업그레이드/감자튀김/제로사이다)×1, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/사이다)×1, 데리버거(세트 업그레이드/치킨너겟/오렌지주스)×1, 뽀로로 음료수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W059  [세트 옵션] menu_first · add_set_oneshot>add_set_oneshot>change_both>add_exclusion · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 모짜렐라버거 세트 두 개, 사이드는 양념감자튀김 음료는 오렌지주스로 줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2
    말: 비건버거 세트 하나, 사이드는 치킨너겟 음료는 제로사이다로 줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2, 비건 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 비건버거 세트 사이드는 양념감자튀김 음료는 콜라로 바꿔줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2, 비건 버거(세트 업그레이드/양념감자튀김/콜라)×1
    말: 비건버거 세트 양상추 빼주세요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2, 비건 버거(세트 업그레이드/양념감자튀김/콜라/양상추 제외)×1
    말: 결제할게요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2, 비건 버거(세트 업그레이드/양념감자튀김/콜라/양상추 제외)×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×2, 비건 버거(세트 업그레이드/양념감자튀김/콜라/양상추 제외)×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W060  [세트 옵션] touch_type · add_set_oneshot>add_set_ask>add_set_ask>add_set_ask · no_points
    [state] screen=menu, order_type=dine-in
    말: 불고기버거 세트 두 개, 사이드는 치즈스틱 음료는 오렌지주스로 줘   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2
    말: 불고기버거 세트로 하나 줘   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2
    말: 사이드는 치킨너겟   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2
    말: 음료는 제로사이다   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 불고기버거 세트로 하나 줘   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 사이드는 감자튀김   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 뽀로로음료로 주세요   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 불고기 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 그릴드비프버거 세트로 하나 줘   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 불고기 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 사이드는 치킨너겟   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 불고기 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 음료는 생수   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 불고기 버거(세트 업그레이드/감자튀김/뽀로로음료)×1, 그릴드 비프 버거(세트 업그레이드/치킨너겟/생수)×1
    말: 결제할게요   → 불고기 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 불고기 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 불고기 버거(세트 업그레이드/감자튀김/뽀로로음료)×1, 그릴드 비프 버거(세트 업그레이드/치킨너겟/생수)×1
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W061  [세트 옵션] touch_type · add_set_oneshot>change_drink>convert_to_single>add_exclusion · points_inline
    [state] screen=menu, order_type=dine-in
    말: 게살버거 세트 하나, 사이드는 감자튀김 음료는 사이다로 줘   → 게살 버거(세트 업그레이드/감자튀김/사이다)×1
    말: 게살버거 세트 음료를 콜라로 바꿔줘   → 게살 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 게살버거 세트 말고 단품으로 바꿔줘   → 게살 버거×1
    말: 게살버거 단품 양상추 빼주세요   → 게살 버거(양상추 제외)×1
    말: 결제할게요   → 게살 버거(양상추 제외)×1
    말: 네 적립할게요 01018843345
    말: 삼성페이로 할게요
```

```
W062  [세트 옵션] menu_first · add_set_ask>change_side>change_drink · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 치킨다릿살버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치즈스틱   → (빈 장바구니)
    말: 제로콜라로 주세요   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/제로콜라)×1
    말: 치킨다릿살버거 세트 사이드를 감자튀김로 바꿔줘   → 치킨 다릿살 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 치킨다릿살버거 세트 음료를 제로사이다로 바꿔줘   → 치킨 다릿살 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 결제할게요   → 치킨 다릿살 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 아 잠깐 오렌지주스도 한 잔 추가할게요   → 치킨 다릿살 버거(세트 업그레이드/감자튀김/제로사이다)×1, 오렌지 주스×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W063  [세트 옵션] greet_dine · add_set_oneshot>add_single>add_set_oneshot · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 치킨다릿살버거 세트 두 개, 사이드는 치즈스틱 음료는 사이다로 줘   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/사이다)×2
    말: 치킨다릿살버거 단품으로 두 개 줘   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/사이다)×2, 치킨 다릿살 버거×2
    말: 새우버거 세트 두 개, 사이드는 양념감자튀김 음료는 사이다로 줘   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/사이다)×2, 치킨 다릿살 버거×2, 새우 버거(세트 업그레이드/양념감자튀김/사이다)×2
    말: 결제할게요   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/사이다)×2, 치킨 다릿살 버거×2, 새우 버거(세트 업그레이드/양념감자튀김/사이다)×2
    말: 아 잠깐 생수도 한 잔 추가할게요   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/사이다)×2, 치킨 다릿살 버거×2, 새우 버거(세트 업그레이드/양념감자튀김/사이다)×2, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W064  [세트 옵션] greet_dine · add_set_ask>add_second_set>add_set_oneshot>add_set_ask>change_side · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 게살버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치킨너겟   → (빈 장바구니)
    말: 음료는 생수   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1
    말: 게살버거 세트 하나 더, 이번엔 사이드는 치즈스틱 음료는 제로사이다로 줘   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 새우버거 세트 두 개, 사이드는 감자튀김 음료는 생수로 줘   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2
    말: 더블치즈버거 세트로 하나 줘   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2
    말: 사이드는 양념감자튀김   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2
    말: 제로사이다로 주세요   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 더블치즈버거 세트 사이드를 치즈스틱로 바꿔줘   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 결제할게요   → 게살 버거(세트 업그레이드/치킨너겟/생수)×1, 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 새우 버거(세트 업그레이드/감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W065  [세트 옵션] orderType_screen · add_set_ask>change_drink>convert_to_single>convert_to_set · points_inline
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 치킨다릿살버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치즈스틱   → (빈 장바구니)
    말: 음료는 뽀로로음료   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/뽀로로음료)×1
    말: 치킨다릿살버거 세트 음료를 생수로 바꿔줘   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/생수)×1
    말: 치킨다릿살버거 세트 말고 단품으로 바꿔줘   → 치킨 다릿살 버거×1
    말: 치킨다릿살버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 오렌지주스   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/오렌지주스)×1
    말: 결제할게요   → 치킨 다릿살 버거(세트 업그레이드/치즈스틱/오렌지주스)×1
    말: 네 적립할게요 01035867004
    말: 카드로 할게요
```

```
W066  [세트 옵션] touch_type · add_set_ask>change_side>change_both · no_points
    [state] screen=menu, order_type=dine-in
    말: 그릴드비프버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 감자튀김   → (빈 장바구니)
    말: 음료는 제로사이다   → 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 그릴드비프버거 세트 사이드를 치킨너겟로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 그릴드비프버거 세트 사이드는 양념감자튀김 음료는 오렌지주스로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 결제할게요   → 그릴드 비프 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W067  [세트 옵션] greet_take · add_set_oneshot>add_set_ask>add_set_oneshot>add_single>add_set_ask>add_single · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 치킨가슴살버거 세트 두 개, 사이드는 양념감자튀김 음료는 뽀로로음료로 줘   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2
    말: 치킨가슴살버거 세트로 하나 줘   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2
    말: 사이드는 감자튀김   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2
    말: 오렌지주스로 주세요   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1
    말: 치킨가슴살버거 세트 두 개, 사이드는 치즈스틱 음료는 오렌지주스로 줘   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2
    말: 새우버거 단품으로 두 개 줘   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2
    말: 치킨가슴살버거 세트로 하나 줘   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2
    말: 사이드는 양념감자튀김   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2
    말: 음료는 오렌지주스   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 비건버거 단품 하나 주세요   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 비건 버거×1
    말: 결제할게요   → 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×2, 치킨 가슴살 버거(세트 업그레이드/감자튀김/오렌지주스)×1, 치킨 가슴살 버거(세트 업그레이드/치즈스틱/오렌지주스)×2, 새우 버거×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1, 비건 버거×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W068  [세트 옵션] menu_first · add_set_ask>change_both>convert_to_single>convert_to_set>add_second_set>add_set_ask · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 모짜렐라버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치즈스틱   → (빈 장바구니)
    말: 음료는 제로사이다   → 모짜렐라 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 모짜렐라버거 세트 사이드는 감자튀김 음료는 제로콜라로 바꿔줘   → 모짜렐라 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 모짜렐라버거 세트 말고 단품으로 바꿔줘   → 모짜렐라 버거×1
    말: 모짜렐라버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 뽀로로음료   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1
    말: 모짜렐라버거 세트 하나 더, 이번엔 사이드는 양념감자튀김 음료는 제로사이다로 줘   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1, 모짜렐라 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: F버거 세트로 하나 줘   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1, 모짜렐라 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 사이드는 치즈스틱   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1, 모짜렐라 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 음료는 제로사이다   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1, 모짜렐라 버거(세트 업그레이드/양념감자튀김/제로사이다)×1, F 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 결제할게요   → 모짜렐라 버거(세트 업그레이드/치킨너겟/뽀로로음료)×1, 모짜렐라 버거(세트 업그레이드/양념감자튀김/제로사이다)×1, F 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W069  [세트 옵션] greet_dine · add_single>add_exclusion>convert_to_set>convert_to_single · points_inline
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 비건버거 단품 하나 담아줘   → 비건 버거×1
    말: 비건버거 단품 양상추 빼주세요   → 비건 버거(양상추 제외)×1
    말: 비건버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 오렌지주스   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스/양상추 제외)×1
    말: 비건버거 세트 말고 단품으로 바꿔줘   → 비건 버거(양상추 제외)×1
    말: 결제할게요   → 비건 버거(양상추 제외)×1
    말: 네 적립할게요 01077479567
    말: 삼성페이로 할게요
```

```
W070  [세트 옵션] menu_first · add_set_oneshot>add_set_ask>change_drink · points_inline
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 비건버거 세트 두 개, 사이드는 치킨너겟 음료는 제로콜라로 줘   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2
    말: 치킨가슴살버거 세트로 하나 줘   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2
    말: 사이드는 양념감자튀김   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2
    말: 오렌지주스로 주세요   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 치킨가슴살버거 세트 음료를 뽀로로음료로 바꿔줘   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1
    말: 결제할게요   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×2, 치킨 가슴살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1
    말: 네 적립할게요 01066474375
    말: 삼성페이로 할게요
```

```
W071  [세트 옵션] orderType_screen · add_set_oneshot>add_set_oneshot>add_single>add_set_oneshot · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 그릴드비프버거 세트 두 개, 사이드는 감자튀김 음료는 사이다로 줘   → 그릴드 비프 버거(세트 업그레이드/감자튀김/사이다)×2
    말: 데리버거 세트 두 개, 사이드는 치킨너겟 음료는 콜라로 줘   → 그릴드 비프 버거(세트 업그레이드/감자튀김/사이다)×2, 데리버거(세트 업그레이드/치킨너겟/콜라)×2
    말: 불고기버거 단품으로 세 개 줘   → 그릴드 비프 버거(세트 업그레이드/감자튀김/사이다)×2, 데리버거(세트 업그레이드/치킨너겟/콜라)×2, 불고기 버거×3
    말: 그릴드비프버거 세트 하나, 사이드는 감자튀김 음료는 콜라로 줘   → 그릴드 비프 버거(세트 업그레이드/감자튀김/사이다)×2, 데리버거(세트 업그레이드/치킨너겟/콜라)×2, 불고기 버거×3, 그릴드 비프 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 결제할게요   → 그릴드 비프 버거(세트 업그레이드/감자튀김/사이다)×2, 데리버거(세트 업그레이드/치킨너겟/콜라)×2, 불고기 버거×3, 그릴드 비프 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W072  [세트 옵션] english · add_set_oneshot>add_set_ask>add_second_set · no_points
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 비건버거 세트 두 개, 사이드는 감자튀김 음료는 오렌지주스로 줘   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2
    말: 게살버거 세트로 하나 줘   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2
    말: 사이드는 양념감자튀김   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2
    말: 음료는 뽀로로음료   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2, 게살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1
    말: 게살버거 세트 하나 더, 이번엔 사이드는 치즈스틱 음료는 사이다로 줘   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2, 게살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1, 게살 버거(세트 업그레이드/치즈스틱/사이다)×1
    말: 결제할게요   → 비건 버거(세트 업그레이드/감자튀김/오렌지주스)×2, 게살 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1, 게살 버거(세트 업그레이드/치즈스틱/사이다)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W073  [세트 옵션] orderType_screen · add_set_ask>convert_to_single>convert_to_set>change_both · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: F버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치킨너겟   → (빈 장바구니)
    말: 생수로 주세요   → F 버거(세트 업그레이드/치킨너겟/생수)×1
    말: F버거 세트 말고 단품으로 바꿔줘   → F 버거×1
    말: F버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 생수   → F 버거(세트 업그레이드/치킨너겟/생수)×1
    말: F버거 세트 사이드는 감자튀김 음료는 콜라로 바꿔줘   → F 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 결제할게요   → F 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W074  [세트 옵션] orderType_screen · add_set_ask>add_second_set>add_set_ask>add_set_ask>change_both>change_drink · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 그릴드비프버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치즈스틱   → (빈 장바구니)
    말: 음료는 제로콜라   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1
    말: 그릴드비프버거 세트 하나 더, 이번엔 사이드는 감자튀김 음료는 제로사이다로 줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 그릴드비프버거 세트로 하나 줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 사이드는 양념감자튀김   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 사이다로 주세요   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: F버거 세트로 하나 줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 사이드는 감자튀김   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 음료는 콜라   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1, F 버거(세트 업그레이드/감자튀김/콜라)×1
    말: F버거 세트 사이드는 치킨너겟 음료는 제로사이다로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1, F 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: F버거 세트 음료를 오렌지주스로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1, F 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 결제할게요   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 그릴드 비프 버거(세트 업그레이드/감자튀김/제로사이다)×1, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/사이다)×1, F 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W075  [세트 옵션] greet_take · add_single>add_set_ask>change_drink · method_change
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 데리버거 단품 세 개 담아줘   → 데리버거×3
    말: 데리버거 세트로 하나 줘   → 데리버거×3
    말: 사이드는 감자튀김   → 데리버거×3
    말: 뽀로로음료로 주세요   → 데리버거×3, 데리버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 데리버거 세트 음료를 오렌지주스로 바꿔줘   → 데리버거×3, 데리버거(세트 업그레이드/감자튀김/오렌지주스)×1
    말: 결제할게요   → 데리버거×3, 데리버거(세트 업그레이드/감자튀김/오렌지주스)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W076  [세트 옵션] touch_type · add_single>add_set_oneshot>add_set_ask · method_change
    [state] screen=menu, order_type=takeout
    말: 그릴드비프버거 단품으로 세 개 줘   → 그릴드 비프 버거×3
    말: 더블치즈버거 세트 두 개, 사이드는 감자튀김 음료는 제로콜라로 줘   → 그릴드 비프 버거×3, 더블 치즈 버거(세트 업그레이드/감자튀김/제로콜라)×2
    말: 그릴드비프버거 세트로 하나 줘   → 그릴드 비프 버거×3, 더블 치즈 버거(세트 업그레이드/감자튀김/제로콜라)×2
    말: 사이드는 양념감자튀김   → 그릴드 비프 버거×3, 더블 치즈 버거(세트 업그레이드/감자튀김/제로콜라)×2
    말: 음료는 제로콜라   → 그릴드 비프 버거×3, 더블 치즈 버거(세트 업그레이드/감자튀김/제로콜라)×2, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/제로콜라)×1
    말: 결제할게요   → 그릴드 비프 버거×3, 더블 치즈 버거(세트 업그레이드/감자튀김/제로콜라)×2, 그릴드 비프 버거(세트 업그레이드/양념감자튀김/제로콜라)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W077  [세트 옵션] english · add_set_ask>convert_to_single>convert_to_set>add_second_set>add_single · points_inline
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 새우버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 양념감자튀김   → (빈 장바구니)
    말: 음료는 뽀로로음료   → 새우 버거(세트 업그레이드/양념감자튀김/뽀로로음료)×1
    말: 새우버거 세트 말고 단품으로 바꿔줘   → 새우 버거×1
    말: 새우버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 사이다   → 새우 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 새우버거 세트 하나 더, 이번엔 사이드는 치즈스틱 음료는 생수로 줘   → 새우 버거(세트 업그레이드/양념감자튀김/사이다)×1, 새우 버거(세트 업그레이드/치즈스틱/생수)×1
    말: 새우버거 단품 세 개 주세요   → 새우 버거(세트 업그레이드/양념감자튀김/사이다)×1, 새우 버거(세트 업그레이드/치즈스틱/생수)×1, 새우 버거×3
    말: 결제할게요   → 새우 버거(세트 업그레이드/양념감자튀김/사이다)×1, 새우 버거(세트 업그레이드/치즈스틱/생수)×1, 새우 버거×3
    말: 네 적립할게요 01041091826
    말: 간편결제로 할게요
```

```
W078  [세트 옵션] stt_naejang · add_set_oneshot>add_set_ask>change_both>add_second_set · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 모짜렐라버거 세트 두 개, 사이드는 양념감자튀김 음료는 생수로 줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2
    말: 더블치즈버거 세트로 하나 줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2
    말: 사이드는 감자튀김   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2
    말: 제로사이다로 주세요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 더블치즈버거 세트 사이드는 치킨너겟 음료는 오렌지주스로 바꿔줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치킨너겟/오렌지주스)×1
    말: 더블치즈버거 세트 하나 더, 이번엔 사이드는 감자튀김 음료는 콜라로 줘   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치킨너겟/오렌지주스)×1, 더블 치즈 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 결제할게요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치킨너겟/오렌지주스)×1, 더블 치즈 버거(세트 업그레이드/감자튀김/콜라)×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/생수)×2, 더블 치즈 버거(세트 업그레이드/치킨너겟/오렌지주스)×1, 더블 치즈 버거(세트 업그레이드/감자튀김/콜라)×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W079  [세트 옵션] touch_type · add_single>convert_to_set>change_both>change_side>convert_to_single · no_points
    [state] screen=menu, order_type=takeout
    말: 그릴드비프버거 단품으로 하나 줘   → 그릴드 비프 버거×1
    말: 그릴드비프버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 제로콜라   → 그릴드 비프 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 그릴드비프버거 세트 사이드는 치즈스틱 음료는 제로사이다로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 그릴드비프버거 세트 사이드를 양념감자튀김로 바꿔줘   → 그릴드 비프 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 그릴드비프버거 세트 말고 단품으로 바꿔줘   → 그릴드 비프 버거×1
    말: 결제할게요   → 그릴드 비프 버거×1
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W080  [세트 옵션] greet_dine · add_set_ask>change_drink>add_exclusion>change_side>add_second_set>add_single · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 게살버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 감자튀김   → (빈 장바구니)
    말: 음료는 제로사이다   → 게살 버거(세트 업그레이드/감자튀김/제로사이다)×1
    말: 게살버거 세트 음료를 제로콜라로 바꿔줘   → 게살 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 게살버거 세트 양상추 빼주세요   → 게살 버거(세트 업그레이드/감자튀김/제로콜라/양상추 제외)×1
    말: 게살버거 세트 사이드를 치킨너겟로 바꿔줘   → 게살 버거(세트 업그레이드/치킨너겟/제로콜라/양상추 제외)×1
    말: 게살버거 세트 하나 더, 이번엔 사이드는 양념감자튀김 음료는 콜라로 줘   → 게살 버거(세트 업그레이드/치킨너겟/제로콜라/양상추 제외)×1, 게살 버거(세트 업그레이드/양념감자튀김/콜라)×1
    말: 게살버거 단품 하나 주세요   → 게살 버거(세트 업그레이드/치킨너겟/제로콜라/양상추 제외)×1, 게살 버거(세트 업그레이드/양념감자튀김/콜라)×1, 게살 버거×1
    말: 결제할게요   → 게살 버거(세트 업그레이드/치킨너겟/제로콜라/양상추 제외)×1, 게살 버거(세트 업그레이드/양념감자튀김/콜라)×1, 게살 버거×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W081  [종합] direct_take · touch_add>convert_to_set>convert_to_single>remove_line>add_single>undo_last>add_single · back_to_menu
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    [touch_add] name=모짜렐라 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: 모짜렐라버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 오렌지주스   → 모짜렐라 버거(세트 업그레이드/양념감자튀김/오렌지주스)×1
    말: 모짜렐라버거 세트 말고 단품으로 바꿔줘   → 모짜렐라 버거×1
    말: 모짜렐라버거 단품 취소해줘   → (빈 장바구니)
    말: 그릴드비프버거 단품 세 개 담아줘   → 그릴드 비프 버거×3
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: F버거 단품 하나 담아줘   → F 버거×1
    말: 결제할게요   → F 버거×1
    말: 아 잠깐 생수도 한 잔 추가할게요   → F 버거×1, 생수×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W082  [종합] touch_type · touch_add>remove_line>touch_add>add_multi>remove_line>remove_line>add_set_oneshot>undo_last · no_points
    [state] screen=menu, order_type=takeout
    [touch_add] name=치즈 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: 치즈버거 단품 지워줘   → (빈 장바구니)
    [touch_add] name=모짜렐라 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 코울슬로 하나 그리고 뽀로로음료수 세 잔 주세요   → 모짜렐라 버거×2, 코울슬로×1, 뽀로로 음료수×3
    말: 모짜렐라버거 단품 전부 취소해줘   → 코울슬로×1, 뽀로로 음료수×3
    말: 뽀로로음료수 전부 지워줘   → 코울슬로×1
    말: 모짜렐라버거 세트 하나, 사이드는 치즈스틱 음료는 제로사이다로 줘   → 코울슬로×1, 모짜렐라 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 방금 담은 거 취소해줘   → 코울슬로×1
    말: 결제할게요   → 코울슬로×1
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W083  [종합] menu_first · touch_add>remove_line>add_set_oneshot>undo_last>add_multi>convert_to_set>change_side · points_inline
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    [touch_add] name=게살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 게살버거 단품 전부 지워줘   → (빈 장바구니)
    말: 새우버거 세트 하나, 사이드는 치킨너겟 음료는 제로사이다로 줘   → 새우 버거(세트 업그레이드/치킨너겟/제로사이다)×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 게살버거 단품 하나 그리고 양념감자튀김 세 개 주세요   → 게살 버거×1, 양념감자튀김×3
    말: 게살버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 제로사이다   → 게살 버거(세트 업그레이드/치킨너겟/제로사이다)×1, 양념감자튀김×3
    말: 게살버거 세트 사이드를 치즈스틱로 바꿔줘   → 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 양념감자튀김×3
    말: 결제할게요   → 게살 버거(세트 업그레이드/치즈스틱/제로사이다)×1, 양념감자튀김×3
    말: 네 적립할게요 01052902002
    말: 현금으로 낼게요
```

```
W084  [종합] orderType_screen · touch_add>remove_line>add_burger_ask>undo_last>add_multi · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    [touch_add] name=더블 불고기 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 더블불고기버거 단품 전부 취소해줘   → (빈 장바구니)
    말: 그릴드비프버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 그릴드 비프 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 더블불고기버거 단품 하나 그리고 오렌지주스 한 잔 그리고 코울슬로 두 개 줘   → 더블 불고기 버거×1, 오렌지 주스×1, 코울슬로×2
    말: 결제할게요   → 더블 불고기 버거×1, 오렌지 주스×1, 코울슬로×2
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W085  [종합] stt_naejang · add_single>touch_add>remove_line>reduce_qty>convert_to_set>convert_to_single>add_single>undo_last · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 더블불고기버거 단품으로 두 개 줘   → 더블 불고기 버거×2
    [touch_add] name=그릴드 비프 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 그릴드비프버거 단품 전부 지워줘   → 더블 불고기 버거×2
    말: 더블불고기버거 단품 한 개 줄여줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 콜라   → 더블 불고기 버거(세트 업그레이드/치즈스틱/콜라)×1
    말: 더블불고기버거 세트 말고 단품으로 바꿔줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품으로 세 개 줘   → 더블 불고기 버거×4
    말: 방금 담은 거 취소해줘   → 더블 불고기 버거×1
    말: 결제할게요   → 더블 불고기 버거×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```

```
W086  [종합] touch_type · add_single>undo_last>touch_add>remove_line>add_set_ask>convert_to_single>convert_to_set>change_side · method_change
    [state] screen=menu, order_type=takeout
    말: 치즈버거 단품으로 두 개 줘   → 치즈 버거×2
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    [touch_add] name=비건 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 비건버거 단품 전부 빼줘   → (빈 장바구니)
    말: 치즈버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 감자튀김   → (빈 장바구니)
    말: 음료는 생수   → 치즈 버거(세트 업그레이드/감자튀김/생수)×1
    말: 치즈버거 세트 말고 단품으로 바꿔줘   → 치즈 버거×1
    말: 치즈버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 사이다   → 치즈 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 치즈버거 세트 사이드를 감자튀김로 바꿔줘   → 치즈 버거(세트 업그레이드/감자튀김/사이다)×1
    말: 결제할게요   → 치즈 버거(세트 업그레이드/감자튀김/사이다)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
    말: 아 카드로 바꿀게요
```

```
W087  [종합] direct_take · touch_add>remove_line>add_multi>add_multi>add_multi · no_points
    [state] screen=start, order_type=None
    말: 포장해 갈게요
    [touch_add] name=그릴드 비프 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 그릴드비프버거 단품 전부 지워줘   → (빈 장바구니)
    말: 오렌지주스 두 잔 그리고 F버거 단품 두 개 그리고 코울슬로 세 개 주세요   → 오렌지 주스×2, F 버거×2, 코울슬로×3
    말: 사이다 두 잔 그리고 불고기버거 단품 세 개 그리고 코울슬로 하나 줘   → 오렌지 주스×2, F 버거×2, 코울슬로×4, 사이다(M)×2, 불고기 버거×3
    말: 너겟 세 개 그리고 F버거 단품 두 개 그리고 생수 두 잔 담아줘   → 오렌지 주스×2, F 버거×4, 코울슬로×4, 사이다(M)×2, 불고기 버거×3, 너겟(4조각)×3, 생수×2
    말: 결제할게요   → 오렌지 주스×2, F 버거×4, 코울슬로×4, 사이다(M)×2, 불고기 버거×3, 너겟(4조각)×3, 생수×2
    말: 적립 안 할게요
    말: 삼성페이로 할게요
```

```
W088  [종합] menu_first · touch_add>remove_line>add_multi>convert_to_set>convert_to_single · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    [touch_add] name=비건 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 비건버거 단품 전부 빼줘   → (빈 장바구니)
    말: 코울슬로 세 개 그리고 F버거 단품 하나 그리고 뽀로로음료수 한 잔 주세요   → 코울슬로×3, F 버거×1, 뽀로로 음료수×1
    말: F버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 오렌지주스   → 코울슬로×3, F 버거(세트 업그레이드/치킨너겟/오렌지주스)×1, 뽀로로 음료수×1
    말: F버거 세트 말고 단품으로 바꿔줘   → 코울슬로×3, F 버거×1, 뽀로로 음료수×1
    말: 결제할게요   → 코울슬로×3, F 버거×1, 뽀로로 음료수×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W089  [종합] orderType_screen · add_set_oneshot>remove_line>touch_add>set_qty>convert_to_set>convert_to_single>add_more>undo_last · points_inline
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 게살버거 세트 하나, 사이드는 치즈스틱 음료는 오렌지주스로 줘   → 게살 버거(세트 업그레이드/치즈스틱/오렌지주스)×1
    말: 게살버거 세트 지워줘   → (빈 장바구니)
    [touch_add] name=게살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 게살버거 단품 1개로 바꿔줘   → 게살 버거×1
    말: 게살버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 콜라   → 게살 버거(세트 업그레이드/치즈스틱/콜라)×1
    말: 게살버거 세트 말고 단품으로 바꿔줘   → 게살 버거×1
    말: 게살버거 단품 두 개 더 줘   → 게살 버거×3
    말: 방금 담은 거 취소해줘   → 게살 버거×1
    말: 결제할게요   → 게살 버거×1
    말: 네 적립할게요 01018036772
    말: 카카오페이로 할게요
```

```
W090  [종합] english · add_burger_ask>undo_last>touch_add>convert_to_set>change_side>convert_to_single>remove_line>touch_add · points_inline
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    말: 더블치즈버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 치즈 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    [touch_add] name=새우 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: 새우버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 사이다   → 새우 버거(세트 업그레이드/감자튀김/사이다)×1
    말: 새우버거 세트 사이드를 치즈스틱로 바꿔줘   → 새우 버거(세트 업그레이드/치즈스틱/사이다)×1
    말: 새우버거 세트 말고 단품으로 바꿔줘   → 새우 버거×1
    말: 새우버거 단품 지워줘   → (빈 장바구니)
    [touch_add] name=더블 치즈 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 결제할게요   → 더블 치즈 버거×2
    말: 네 적립할게요 01043748156
    말: 카드로 할게요
```

```
W091  [종합] greet_take · touch_add>add_burger_ask>remove_line>convert_to_set>change_side>convert_to_single>set_qty>set_qty · points_phone
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    [touch_add] name=불고기 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 더블치즈버거 하나 줘   → 불고기 버거×2
    말: 단품으로 줘   → 불고기 버거×2, 더블 치즈 버거×1
    말: 불고기버거 단품 전부 취소해줘   → 더블 치즈 버거×1
    말: 더블치즈버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 콜라   → 더블 치즈 버거(세트 업그레이드/양념감자튀김/콜라)×1
    말: 더블치즈버거 세트 사이드를 치킨너겟로 바꿔줘   → 더블 치즈 버거(세트 업그레이드/치킨너겟/콜라)×1
    말: 더블치즈버거 세트 말고 단품으로 바꿔줘   → 더블 치즈 버거×1
    말: 더블치즈버거 단품 3개로 바꿔줘   → 더블 치즈 버거×3
    말: 더블치즈버거 단품 4개로 바꿔줘   → 더블 치즈 버거×4
    말: 결제할게요   → 더블 치즈 버거×4
    말: 포인트 적립할게요
    말: 공일공 칠구팔공 사육이삼
    말: 카카오페이로 할게요
```

```
W092  [종합] stt_naejang · add_set_ask>touch_add>convert_to_single>convert_to_set>remove_line>change_side>add_set_oneshot>undo_last · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 비건버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 감자튀김   → (빈 장바구니)
    말: 뽀로로음료로 주세요   → 비건 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    [touch_add] name=F 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 비건버거 세트 말고 단품으로 바꿔줘   → 비건 버거×1, F 버거×2
    말: 비건버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 제로사이다   → 비건 버거(세트 업그레이드/치즈스틱/제로사이다)×1, F 버거×2
    말: F버거 단품 전부 지워줘   → 비건 버거(세트 업그레이드/치즈스틱/제로사이다)×1
    말: 비건버거 세트 사이드를 양념감자튀김로 바꿔줘   → 비건 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 더블불고기버거 세트 하나, 사이드는 감자튀김 음료는 제로콜라로 줘   → 비건 버거(세트 업그레이드/양념감자튀김/제로사이다)×1, 더블 불고기 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 방금 담은 거 취소해줘   → 비건 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 결제할게요   → 비건 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W093  [종합] stt_naejang · touch_add>remove_line>add_single>undo_last>add_set_ask>convert_to_single>convert_to_set · points_inline
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    [touch_add] name=F 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: F버거 단품 전부 취소해줘   → (빈 장바구니)
    말: 더블치즈버거 단품 세 개 주세요   → 더블 치즈 버거×3
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    말: 모짜렐라버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 치킨너겟   → (빈 장바구니)
    말: 음료는 사이다   → 모짜렐라 버거(세트 업그레이드/치킨너겟/사이다)×1
    말: 모짜렐라버거 세트 말고 단품으로 바꿔줘   → 모짜렐라 버거×1
    말: 모짜렐라버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 뽀로로음료   → 모짜렐라 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 결제할게요   → 모짜렐라 버거(세트 업그레이드/감자튀김/뽀로로음료)×1
    말: 네 적립할게요 01056910573
    말: 삼성페이로 할게요
```

```
W094  [종합] greet_take · add_multi>remove_line>touch_add>convert_to_set>convert_to_single>set_qty>add_more>undo_last · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    말: 너겟 하나 그리고 새우버거 단품 두 개 그리고 콜라 두 잔 주세요   → 너겟(4조각)×1, 새우 버거×2, 콜라(M)×2
    말: 너겟 지워줘   → 새우 버거×2, 콜라(M)×2
    [touch_add] name=불고기 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: 불고기버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 콜라   → 새우 버거×2, 콜라(M)×2, 불고기 버거(세트 업그레이드/치킨너겟/콜라)×1
    말: 불고기버거 세트 말고 단품으로 바꿔줘   → 새우 버거×2, 콜라(M)×2, 불고기 버거×1
    말: 불고기버거 단품 2개로 바꿔줘   → 새우 버거×2, 콜라(M)×2, 불고기 버거×2
    말: 콜라 두 개 더 줘   → 새우 버거×2, 콜라(M)×4, 불고기 버거×2
    말: 방금 담은 거 취소해줘   → 새우 버거×2, 콜라(M)×2, 불고기 버거×2
    말: 결제할게요   → 새우 버거×2, 콜라(M)×2, 불고기 버거×2
    말: 적립 안 할게요
    말: 현금으로 낼게요
```

```
W095  [종합] greet_take · touch_add>remove_line>add_burger_ask>convert_to_set>convert_to_single>query · back_to_menu
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 포장할게요
    [touch_add] name=치킨 가슴살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 치킨가슴살버거 단품 전부 지워줘   → (빈 장바구니)
    말: 비건버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 비건 버거×1
    말: 비건버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 사이다   → 비건 버거(세트 업그레이드/양념감자튀김/사이다)×1
    말: 비건버거 세트 말고 단품으로 바꿔줘   → 비건 버거×1
    말: 가장 저렴한 버거가 뭐예요?   → 비건 버거×1
    말: 결제할게요   → 비건 버거×1
    말: 아 잠깐 콜라도 한 잔 추가할게요   → 비건 버거×1, 콜라(M)×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W096  [종합] stt_naejang · add_burger_ask>touch_add>remove_line>convert_to_set>convert_to_single>add_single>undo_last>add_exclusion · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    말: 더블불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 더블 불고기 버거×1
    [touch_add] name=게살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 게살버거 단품 전부 빼줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품을 세트로 바꿔줘. 사이드는 감자튀김 음료는 제로콜라   → 더블 불고기 버거(세트 업그레이드/감자튀김/제로콜라)×1
    말: 더블불고기버거 세트 말고 단품으로 바꿔줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품 하나 주세요   → 더블 불고기 버거×2
    말: 방금 담은 거 취소해줘   → 더블 불고기 버거×1
    말: 더블불고기버거 단품 양상추 빼주세요   → 더블 불고기 버거(양상추 제외)×1
    말: 결제할게요   → 더블 불고기 버거(양상추 제외)×1
    말: 적립 안 할게요
    말: 간편결제로 할게요
```

```
W097  [종합] orderType_screen · add_burger_ask>undo_last>touch_add>convert_to_set>change_side>convert_to_single>remove_line>touch_add · no_points
    [state] screen=orderType, order_type=None
    말: 여기서 먹고 갈게요
    말: 치킨다릿살버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 치킨 다릿살 버거×1
    말: 방금 담은 거 취소해줘   → (빈 장바구니)
    [touch_add] name=F 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: F버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 콜라   → F 버거(세트 업그레이드/치즈스틱/콜라)×1
    말: F버거 세트 사이드를 치킨너겟로 바꿔줘   → F 버거(세트 업그레이드/치킨너겟/콜라)×1
    말: F버거 세트 말고 단품으로 바꿔줘   → F 버거×1
    말: F버거 단품 지워줘   → (빈 장바구니)
    [touch_add] name=치킨 다릿살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 결제할게요   → 치킨 다릿살 버거×2
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W098  [종합] stt_naejang · touch_add>remove_line>touch_add>convert_to_set>convert_to_single>remove_line>add_single · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 내장에서 먹을게.
    [touch_add] name=새우 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 새우버거 단품 전부 취소해줘   → (빈 장바구니)
    [touch_add] name=불고기 버거, qty=1, set=False, side=None, drink=None, exclude=None
    말: 불고기버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 생수   → 불고기 버거(세트 업그레이드/치즈스틱/생수)×1
    말: 불고기버거 세트 말고 단품으로 바꿔줘   → 불고기 버거×1
    말: 불고기버거 단품 지워줘   → (빈 장바구니)
    말: 새우버거 단품 세 개 담아줘   → 새우 버거×3
    말: 결제할게요   → 새우 버거×3
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W099  [종합] english · touch_add>remove_line>add_set_ask>convert_to_single>convert_to_set · back_to_menu
    [state] screen=start, order_type=None
    말: Hello
    말: Dine in please
    [touch_add] name=게살 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 게살버거 단품 전부 취소해줘   → (빈 장바구니)
    말: 비건버거 세트로 하나 줘   → (빈 장바구니)
    말: 사이드는 양념감자튀김   → (빈 장바구니)
    말: 생수로 주세요   → 비건 버거(세트 업그레이드/양념감자튀김/생수)×1
    말: 비건버거 세트 말고 단품으로 바꿔줘   → 비건 버거×1
    말: 비건버거 단품을 세트로 바꿔줘. 사이드는 치즈스틱 음료는 제로콜라   → 비건 버거(세트 업그레이드/치즈스틱/제로콜라)×1
    말: 결제할게요   → 비건 버거(세트 업그레이드/치즈스틱/제로콜라)×1
    말: 아 잠깐 오렌지주스도 한 잔 추가할게요   → 비건 버거(세트 업그레이드/치즈스틱/제로콜라)×1, 오렌지 주스×1
    말: 이제 결제할게요
    말: 적립 안 할게요
    말: 카드로 할게요
```

```
W100  [종합] menu_first · add_burger_ask>touch_add>remove_line>reduce_qty>convert_to_set>convert_to_single>query>add_set_oneshot · no_points
    [state] screen=start, order_type=None
    말: 안녕하세요
    말: 매장에서 먹을게요
    말: 버거 뭐 있어요?
    말: 불고기버거 하나 줘   → (빈 장바구니)
    말: 단품으로 줘   → 불고기 버거×1
    [touch_add] name=비건 버거, qty=2, set=False, side=None, drink=None, exclude=None
    말: 불고기버거 단품 빼줘   → 비건 버거×2
    말: 비건버거 단품 한 개 줄여줘   → 비건 버거×1
    말: 비건버거 단품을 세트로 바꿔줘. 사이드는 치킨너겟 음료는 제로콜라   → 비건 버거(세트 업그레이드/치킨너겟/제로콜라)×1
    말: 비건버거 세트 말고 단품으로 바꿔줘   → 비건 버거×1
    말: 가장 저렴한 버거가 뭐예요?   → 비건 버거×1
    말: 불고기버거 세트 하나, 사이드는 양념감자튀김 음료는 제로사이다로 줘   → 비건 버거×1, 불고기 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 결제할게요   → 비건 버거×1, 불고기 버거(세트 업그레이드/양념감자튀김/제로사이다)×1
    말: 적립 안 할게요
    말: 카카오페이로 할게요
```
