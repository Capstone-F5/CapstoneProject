"""
Multi-turn persona test for kiosk AI backend.
Run: python test_personas.py
"""
import sys, os, asyncio, json

sys.path.insert(0, 'I:/DMU/인공지능캡스톤디자인/Project/CapstoneProject')
sys.path.insert(0, 'I:/DMU/인공지능캡스톤디자인/Project/CapstoneProject/backend')

from dotenv import load_dotenv
load_dotenv('I:/DMU/인공지능캡스톤디자인/Project/CapstoneProject/.env')

# Reset singleton before running
import ai_modules.llm.agent as ag
ag._executor = None

from backend.core.llm_service import run_agent


async def run_turn(session_id, turn_num, user_input, language, cart, screen, order_type):
    result = await run_agent(
        session_id=session_id,
        user_input=user_input,
        language=language,
        cart=cart,
        screen=screen,
        order_type=order_type,
    )
    output = result.get("output", "")
    actions = result.get("actions", [])
    return turn_num, user_input, output, actions


async def main():
    # ────────────────────────────────────────────────
    # PERSONA 1 - 80세 할머니
    # ────────────────────────────────────────────────
    p1_session = "granny-test-01"
    p1_turns = [
        (1, "여보세요? 거기 햄버거 집이죠?", 'ko', [], 'start', None),
        (2, "매장에서 먹을 거예요", 'ko', [], 'orderType', None),
        (3, "손자가 치즈버거 좋아하는데 치즈버거 있어요?", 'ko', [], 'menu', 'dine-in'),
        (4, "그냥 치즈버거 하나만 주세요 세트 말고요", 'ko', [], 'menu', 'dine-in'),
        (5, "감자튀김도 하나 주세요", 'ko',
            [{"cart_id":1001,"menu_id":5,"name":"치즈버거","item_type":"single","quantity":1,"unit_price":4200,"exclusion":"없음","side":None,"drink":None}],
            'menu', 'dine-in'),
        (6, "얼마예요? 카드 되나요?", 'ko',
            [{"cart_id":1001,"menu_id":5,"name":"치즈버거","item_type":"single","quantity":1,"unit_price":4200,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":1002,"menu_id":13,"name":"감자튀김","item_type":"single","quantity":1,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'cart', 'dine-in'),
        (7, "카드로 할게요", 'ko',
            [{"cart_id":1001,"menu_id":5,"name":"치즈버거","item_type":"single","quantity":1,"unit_price":4200,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":1002,"menu_id":13,"name":"감자튀김","item_type":"single","quantity":1,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'cart', 'dine-in'),
    ]

    print("PERSONA1:")
    for turn_num, user_input, lang, cart, screen, ot in p1_turns:
        t, inp, out, acts = await run_turn(p1_session, turn_num, user_input, lang, cart, screen, ot)
        print(f"T{t}|{inp}|{out}|{json.dumps(acts, ensure_ascii=False)}")

    print()

    # ────────────────────────────────────────────────
    # PERSONA 2 - 시각장애인
    # ────────────────────────────────────────────────
    p2_session = "blind-test-01"
    p2_turns = [
        (1, "안녕하세요", 'ko', [], 'start', None),
        (2, "포장이요", 'ko', [], 'orderType', None),
        (3, "버거 종류가 뭐가 있어요 전부 읽어주세요", 'ko', [], 'menu', 'takeout'),
        (4, "불고기버거 세트로 하나요", 'ko', [], 'menu', 'takeout'),
        (5, "사이드는 치킨너겟으로요", 'ko', [], 'menu', 'takeout'),
        (6, "음료는 제로콜라로요", 'ko', [], 'menu', 'takeout'),
        (7, "지금 담긴 거 다시 한번 읽어주세요", 'ko',
            [{"cart_id":2001,"menu_id":2,"name":"불고기버거","item_type":"set","quantity":1,"unit_price":8500,"exclusion":"없음","side":"치킨너겟","drink":"제로콜라"}],
            'cart', 'takeout'),
        (8, "네 그대로 카드로 결제할게요", 'ko',
            [{"cart_id":2001,"menu_id":2,"name":"불고기버거","item_type":"set","quantity":1,"unit_price":8500,"exclusion":"없음","side":"치킨너겟","drink":"제로콜라"}],
            'cart', 'takeout'),
    ]

    print("PERSONA2:")
    for turn_num, user_input, lang, cart, screen, ot in p2_turns:
        t, inp, out, acts = await run_turn(p2_session, turn_num, user_input, lang, cart, screen, ot)
        print(f"T{t}|{inp}|{out}|{json.dumps(acts, ensure_ascii=False)}")

    print()

    # ────────────────────────────────────────────────
    # PERSONA 3 - 독일인
    # ────────────────────────────────────────────────
    p3_session = "german-test-01"
    p3_turns = [
        (1, "Hello, I would like to order some food", 'en', [], 'start', None),
        (2, "I will eat here", 'en', [], 'orderType', None),
        (3, "What burgers do you have? Please read me the menu", 'en', [], 'menu', 'dine-in'),
        (4, "I will take the F burger as a set please", 'en', [], 'menu', 'dine-in'),
        (5, "French fries and cola please", 'en', [], 'menu', 'dine-in'),
        (6, "Also one cola separately", 'en',
            [{"cart_id":3001,"menu_id":1,"name":"F버거","item_type":"set","quantity":1,"unit_price":9500,"exclusion":"없음","side":"감자튀김","drink":"콜라"}],
            'menu', 'dine-in'),
        (7, "How much is that total? Can I pay by card?", 'en',
            [{"cart_id":3001,"menu_id":1,"name":"F버거","item_type":"set","quantity":1,"unit_price":9500,"exclusion":"없음","side":"감자튀김","drink":"콜라"},
             {"cart_id":3002,"menu_id":17,"name":"코카콜라","item_type":"single","quantity":1,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'cart', 'dine-in'),
        (8, "Card please", 'en',
            [{"cart_id":3001,"menu_id":1,"name":"F버거","item_type":"set","quantity":1,"unit_price":9500,"exclusion":"없음","side":"감자튀김","drink":"콜라"},
             {"cart_id":3002,"menu_id":17,"name":"코카콜라","item_type":"single","quantity":1,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'cart', 'dine-in'),
    ]

    print("PERSONA3:")
    for turn_num, user_input, lang, cart, screen, ot in p3_turns:
        t, inp, out, acts = await run_turn(p3_session, turn_num, user_input, lang, cart, screen, ot)
        print(f"T{t}|{inp}|{out}|{json.dumps(acts, ensure_ascii=False)}")

    print()

    # ────────────────────────────────────────────────
    # PERSONA 4 - 진상 고객
    # ────────────────────────────────────────────────
    p4_session = "jinsang-test-01"
    p4_turns = [
        (1, "야 빨리빨리", 'ko', [], 'start', None),
        (2, "매장이요", 'ko', [], 'orderType', None),
        (3, "여기 피자 없어요? 왜 햄버거밖에 없어", 'ko', [], 'menu', 'dine-in'),
        (4, "그럼 가장 비싼 버거가 뭐예요", 'ko', [], 'menu', 'dine-in'),
        (5, "그릴드비프버거 세트로 주세요 근데 가격 너무 비싼 거 아니에요 할인 안 돼요?", 'ko', [], 'menu', 'dine-in'),
        (6, "세트 말고 단품으로요 그리고 사이다도 따로 하나", 'ko', [], 'menu', 'dine-in'),
        (7, "잠깐만요 그거 다 취소하고 치즈버거 두 개 감자튀김 두 개 콜라 두 개", 'ko',
            [{"cart_id":4001,"menu_id":12,"name":"그릴드비프버거","item_type":"single","quantity":1,"unit_price":7800,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":4002,"menu_id":19,"name":"사이다","item_type":"single","quantity":1,"unit_price":2500,"exclusion":"없음","side":None,"drink":None}],
            'menu', 'dine-in'),
        (8, "근데 치즈버거 양파 빼줘요", 'ko',
            [{"cart_id":4010,"menu_id":5,"name":"치즈버거","item_type":"single","quantity":2,"unit_price":4200,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":4011,"menu_id":13,"name":"감자튀김","item_type":"single","quantity":2,"unit_price":2000,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":4012,"menu_id":17,"name":"코카콜라","item_type":"single","quantity":2,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'menu', 'dine-in'),
        (9, "됐어요 이대로 카드로 결제해요", 'ko',
            [{"cart_id":4010,"menu_id":5,"name":"치즈버거","item_type":"single","quantity":2,"unit_price":4200,"exclusion":"양파 제외","side":None,"drink":None},
             {"cart_id":4011,"menu_id":13,"name":"감자튀김","item_type":"single","quantity":2,"unit_price":2000,"exclusion":"없음","side":None,"drink":None},
             {"cart_id":4012,"menu_id":17,"name":"코카콜라","item_type":"single","quantity":2,"unit_price":2000,"exclusion":"없음","side":None,"drink":None}],
            'cart', 'dine-in'),
    ]

    print("PERSONA4:")
    for turn_num, user_input, lang, cart, screen, ot in p4_turns:
        t, inp, out, acts = await run_turn(p4_session, turn_num, user_input, lang, cart, screen, ot)
        print(f"T{t}|{inp}|{out}|{json.dumps(acts, ensure_ascii=False)}")


if __name__ == "__main__":
    asyncio.run(main())
