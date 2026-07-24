"""
메뉴/옵션 시드 데이터.

PDF SchemaSpecification 의 3.1 (MENU_ITEMS) / 3.2 (MENU_OPTIONS) 매핑.
- 단품가가 base_price, 세트는 +2,000 원 옵션으로 분리.
- 채소 제외 옵션은 +0 원.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Category, MenuItem, MenuOption


_CATEGORIES = [
    {"slug": "burger", "name_ko": "버거", "name_en": "Burger", "display_order": 1},
    {"slug": "side", "name_ko": "사이드", "name_en": "Side", "display_order": 2},
    {"slug": "beverage", "name_ko": "음료", "name_en": "Beverage", "display_order": 3},
]


_MENU = [
    # (slug, category_slug, name_ko, name_en, price, description, exclude_options_ko, has_set)
    ("burger_f", "burger", "F 버거", "F Burger", 7500,
     "[F 버거] 치킨과 불고기의 만남, 한 입에 끝내는 환상의 더블 콤보! 주요 재료: 치킨패티, 불고기패티, 불고기소스. 칼로리 820kcal (세트 1170kcal).",
     ["양상추", "양파"], True),
    ("burger_grilled_beef", "burger", "그릴드 비프 버거", "Grilled Beef Burger", 7800,
     "[그릴드 비프 버거] 진짜 불맛을 원한다면? 그릴 자국 선명한 정통 수제 패티! 주요 재료: 그릴드 비프 패티, 체다치즈, 적양파. 칼로리 710kcal (세트 1060kcal).",
     ["양상추", "토마토", "적양파"], True),
    ("burger_mozzarella", "burger", "모짜렐라 버거", "Mozzarella Burger", 7200,
     "[모짜렐라 버거] 치즈 폭포가 팡팡! 고소한 통치즈가 쭈욱 늘어나는 즐거움. 주요 재료: 소고기패티, 통모짜렐라 튀김, 마리나라. 칼로리 780kcal (세트 1130kcal).",
     ["양상추"], True),
    ("burger_vegan", "burger", "비건 버거", "Vegan Burger", 6800,
     "[비건 버거] 지구와 나를 위한 선택, 고기 없이도 완벽한 풍미와 건강함. 주요 재료: 식물성패티, 통밀번, 아보카도. 칼로리 420kcal (세트 770kcal).",
     ["양상추", "토마토", "적양파"], True),
    ("burger_crab", "burger", "게살 버거", "Crab Burger", 6500,
     "[게살 버거] 입안 가득 번지는 바다의 향기, 겉바속촉 게살의 진수! 주요 재료: 게살 튀김 패티, 타르타르 소스. 칼로리 550kcal (세트 900kcal).",
     ["양상추"], True),
    ("burger_chicken_thigh", "burger", "치킨 다릿살 버거", "Chicken Thigh Burger", 6200,
     "[치킨 다릿살 버거] 퍽퍽함 제로! 야들야들한 닭다리살의 육즙이 살아있는 버거. 주요 재료: 닭다리살 튀김, 마요네즈. 칼로리 650kcal (세트 1000kcal).",
     ["양배추(또는 양상추)"], True),
    ("burger_double_bulgogi", "burger", "더블 불고기 버거", "Double Bulgogi Burger", 6000,
     "[더블 불고기 버거] 더 진해진 달콤짭짤함, 불고기 매니아를 위한 두 배의 감동. 주요 재료: 불고기 패티 2장, 불고기 소스. 칼로리 680kcal (세트 1030kcal).",
     ["양상추", "양파"], True),
    ("burger_double_cheese", "burger", "더블 치즈 버거", "Double Cheese Burger", 5500,
     "[더블 치즈 버거] 치즈의 진한 풍미와 고소한 패티가 두 장씩! 치즈 덕후 필수. 주요 재료: 소고기 패티 2장, 치즈 2장, 피클. 칼로리 620kcal (세트 970kcal).",
     ["다진 양파", "피클"], True),
    ("burger_chicken_breast", "burger", "치킨 가슴살 버거", "Chicken Breast Burger", 5500,
     "[치킨 가슴살 버거] 담백함의 끝판왕! 크런치한 식감 뒤에 숨겨진 부드러운 속살. 주요 재료: 닭가슴살 튀김, 크리미 화이트 소스. 칼로리 520kcal (세트 870kcal).",
     ["양상추", "피클"], True),
    ("burger_shrimp", "burger", "새우 버거", "Shrimp Burger", 4800,
     "[새우 버거] 탱글탱글 씹히는 통새우살, 고소함이 남다른 마성의 버거. 주요 재료: 새우 패티, 타르타르 소스. 칼로리 480kcal (세트 830kcal).",
     ["채썬 양배추"], True),
    ("burger_bulgogi", "burger", "불고기 버거", "Bulgogi Burger", 4500,
     "[불고기 버거] 한국인의 소울 푸드! 변치 않는 달콤함의 베스트셀러. 주요 재료: 불고기 패티 1장, 불고기 소스. 칼로리 450kcal (세트 800kcal).",
     ["양상추", "양파"], True),
    ("burger_cheese", "burger", "치즈 버거", "Cheese Burger", 4200,
     "[치즈 버거] 심플한게 제일 맛있지! 정통 아메리칸 스타일의 치즈버거. 주요 재료: 소고기 패티, 체다치즈, 케첩, 머스타드. 칼로리 430kcal (세트 780kcal).",
     ["다진 양파", "피클"], True),
    ("burger_teri", "burger", "데리버거", "Teri Burger", 4000,
     "[데리버거] 달콤짭짤한 데리야끼 소스와 부드러운 패티의 환상적인 조화! 주요 재료: 혼합육 패티, 데리야끼 소스, 마요네즈. 칼로리 410kcal (세트 760kcal).",
     ["양상추", "양파"], True),
    # ---- 사이드 ----
    ("side_seasoned_fries", "side", "양념감자튀김", "Seasoned French Fries", 2500,
     "[양념감자튀김] 흔들어 먹는 재미! 입안에 착 붙는 마법의 가루 시즈닝. 380kcal.",
     [], False),
    ("side_nuggets", "side", "너겟(4조각)", "Chicken Nuggets (4pcs)", 2000,
     "[너겟 4조각] 한 입에 쏙! 아이들도 좋아하는 바삭하고 담백한 간식. 180kcal.",
     [], False),
    ("side_cheese_sticks", "side", "치즈스틱(2개)", "Cheese Sticks (2pcs)", 2000,
     "[치즈스틱 2개] 황금빛으로 잘 튀겨진 고소한 치즈가 쭈욱 늘어나는 맛. 160kcal.",
     [], False),
    ("side_fries_m", "side", "감자튀김(M)", "French Fries (M)", 2000,
     "[감자튀김 M] 갓 튀겨내어 바삭함이 살아있는 햄버거의 영원한 단짝. 350kcal.",
     [], False),
    ("side_corn_salad", "side", "콘샐러드", "Corn Salad", 1900,
     "[콘샐러드] 톡톡 터지는 옥수수 알갱이의 상큼함이 입안을 리프레쉬! 140kcal.",
     [], False),
    ("side_coleslaw", "side", "코울슬로", "Cole Slaw", 1900,
     "[코울슬로] 아삭아삭 씹는 맛이 일품! 버거와 최고의 궁합 샐러드. 130kcal.",
     [], False),
    # ---- 음료 ----
    ("bev_orange_juice", "beverage", "오렌지 주스", "Orange Juice", 2500,
     "[오렌지 주스] 상큼달콤 비타민 충전! 100% 신선한 과즙. 110kcal.",
     [], False),
    ("bev_coke_m", "beverage", "콜라(M)", "Coca Cola (M)", 2000,
     "[콜라 M] 얼음 가득 채운 짜릿한 탄산, 버거 맛을 200% 살려줘요. 140kcal.",
     [], False),
    ("bev_zero_coke_m", "beverage", "제로 콜라(M)", "Zero Coke (M)", 2000,
     "[제로 콜라 M] 맛은 그대로, 칼로리는 0! 부담 없이 즐기는 청량함.",
     [], False),
    ("bev_sprite_m", "beverage", "사이다(M)", "Sprite (M)", 2000,
     "[사이다 M] 투명하고 맑은 깨끗한 탄산의 정석, 입안이 깔끔해져요. 130kcal.",
     [], False),
    ("bev_zero_sprite_m", "beverage", "제로 사이다(M)", "Zero Sprite (M)", 2000,
     "[제로 사이다 M] 칼로리 걱정 끝! 가볍고 시원하게 터지는 청량 에너지.",
     [], False),
    ("bev_pororo", "beverage", "뽀로로 음료수", "Pororo Drink", 2000,
     "[뽀로로 음료수] 어린이 친구들의 최애 메뉴! 귀여운 캐릭터와 달콤한 맛. 120kcal.",
     [], False),
    ("bev_water", "beverage", "생수", "Mineral Water", 1000,
     "[생수] 갈증을 시원하게 풀어주는 맑고 투명한 순수한 물.",
     [], False),
]


# 세트 사이드/음료 선택 옵션 — frontend/src/data/menuData.js 의 SET_SIDES/SET_DRINKS 와
# 이름을 반드시 동일하게 유지한다(프론트가 이름으로 옵션을 찾아 selected_options 를 조립함).
_SET_SIDES = [
    ("감자튀김", "French Fries", 0),
    ("치즈스틱", "Cheese Sticks", 0),
    ("치킨너겟", "Chicken Nuggets", 0),
    ("양념감자튀김", "Seasoned French Fries", 500),
]
_SET_DRINKS = [
    ("콜라", "Coke", 0),
    ("제로콜라", "Zero Coke", 0),
    ("사이다", "Sprite", 0),
    ("제로사이다", "Zero Sprite", 0),
    ("생수", "Water", 0),
    ("뽀로로음료", "Pororo Drink", 0),
    ("오렌지주스", "Orange Juice", 500),
]

# 추천메뉴 탭(is_popular) — frontend mock 의 recommended 3종과 동일
_POPULAR_SLUGS = {"burger_f", "burger_crab", "burger_vegan"}


async def seed_menu(session: AsyncSession) -> None:
    """이미 시드되어 있으면 skip."""
    existing = (await session.execute(select(MenuItem))).first()
    if existing:
        return

    # 카테고리
    cat_map: dict[str, str] = {}
    for c in _CATEGORIES:
        cat = Category(
            name_ko=c["name_ko"], name_en=c["name_en"], display_order=c["display_order"]
        )
        session.add(cat)
        await session.flush()
        cat_map[c["slug"]] = cat.id

    # 메뉴 + 옵션
    for slug, cat_slug, name_ko, name_en, price, desc, excludes, has_set in _MENU:
        item = MenuItem(
            category_id=cat_map[cat_slug],
            name_ko=name_ko,
            name_en=name_en,
            base_price=Decimal(str(price)),
            description=desc,
            is_popular=slug in _POPULAR_SLUGS,
        )
        session.add(item)
        await session.flush()

        order = 0
        if has_set:
            session.add(
                MenuOption(
                    menu_item_id=item.id,
                    name_ko="세트 업그레이드",
                    name_en="Upgrade to Set",
                    description="세트 음료 및 사이드(감자튀김 M) 포함",
                    additional_price=Decimal("2000"),
                    display_order=order,
                    option_group="SET_UPGRADE",
                )
            )
            order += 1
            for name_ko_s, name_en_s, extra in _SET_SIDES:
                session.add(
                    MenuOption(
                        menu_item_id=item.id,
                        name_ko=name_ko_s,
                        name_en=name_en_s,
                        description="세트 사이드 선택",
                        additional_price=Decimal(str(extra)),
                        display_order=order,
                        option_group="SET_SIDE",
                    )
                )
                order += 1
            for name_ko_d, name_en_d, extra in _SET_DRINKS:
                session.add(
                    MenuOption(
                        menu_item_id=item.id,
                        name_ko=name_ko_d,
                        name_en=name_en_d,
                        description="세트 음료 선택",
                        additional_price=Decimal(str(extra)),
                        display_order=order,
                        option_group="SET_DRINK",
                    )
                )
                order += 1
        for veg in excludes:
            session.add(
                MenuOption(
                    menu_item_id=item.id,
                    name_ko=f"{veg} 제외",
                    name_en=f"Exclude {veg}",
                    description="알레르기 및 고령자 섭취 불편 호소 시 자동 차단 옵션",
                    additional_price=Decimal("0"),
                    display_order=order,
                    option_group="EXCLUDE",
                )
            )
            order += 1

    await session.commit()
