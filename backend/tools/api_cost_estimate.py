"""월 API 비용 추정(LLM·STT·TTS). 실측값과 가정을 분리해 둔다 — 가정은 상수만 바꿔서 다시 돌리면 된다.

    python tools/api_cost_estimate.py

실측(2026-10-03, 이 저장소): LLM 호출 1회 고정 입력 약 10,970토큰(시스템 프롬프트 9,146 + 도구 스키마 1,824),
대표 주문 9턴에서 턴당 LLM 호출 1.78회·입력 약 20,500토큰, 응답 평균 42.5자, 손님 발화 평균 12.9자,
시나리오 평균 11.1턴, LLM을 거치지 않는 턴(직접 처리) 21%.
단가: https://developers.openai.com/api/docs/pricing (gpt-4o-mini, whisper-1, tts-1)
"""
# ── 단가 (USD) ──
IN, IN_CACHED, OUT = 0.15 / 1e6, 0.075 / 1e6, 0.60 / 1e6   # gpt-4o-mini 토큰당
STT_PER_MIN = 0.006                                          # whisper-1 (.env 설정). gpt-4o-mini-transcribe는 0.003
TTS_PER_CHAR = 15.0 / 1e6                                    # tts-1

# ── 실측 ──
IN_PER_TURN, OUT_PER_TURN = 20_500, 100        # LLM을 거친 턴당 토큰(출력은 도구 호출+응답 문장 추정)
PREFIX_SHARE = 10_970 * 1.78 / IN_PER_TURN     # 입력 중 고정 접두(캐시 대상) 비율 ≈ 95%
LLM_TURN_SHARE = 0.79                          # 직접 처리(LLM 없음) 21% 제외
REPLY_CHARS, SPEECH_SEC = 42.5, 3.5            # 응답 글자 수(실측), 발화 길이(실측 12.9자 + VAD 여유 가정)
TURNS_PER_ORDER = 11.1

# ── 가정 (실측 아님: 매장·고객에 맞게 수정) ──
KRW_PER_USD = 1400
AVG_ORDER_KRW = 9000
DAYS = 30
AGE = {  # 연령대: (방문 비율, 음성 사용률, 턴 배수)
    "10대": (0.10, 0.20, 1.0), "20대": (0.30, 0.25, 1.0), "30대": (0.25, 0.15, 1.0),
    "40대": (0.15, 0.15, 1.0), "50대": (0.10, 0.25, 1.2), "60대+": (0.10, 0.40, 1.5),
}


def turn_cost(cache_hit: float) -> dict:
    """음성 한 턴(평균)의 비용. cache_hit = 고정 접두 중 캐시로 처리되는 비율(0~1)."""
    cached = IN_PER_TURN * PREFIX_SHARE * cache_hit
    llm = LLM_TURN_SHARE * ((IN_PER_TURN - cached) * IN + cached * IN_CACHED + OUT_PER_TURN * OUT)
    stt = SPEECH_SEC / 60 * STT_PER_MIN
    tts = REPLY_CHARS * TTS_PER_CHAR
    return {"llm": llm, "stt": stt, "tts": tts, "total": llm + stt + tts}


def month(daily_sales_krw: int, cache_hit: float, voice_rate: float | None = None) -> dict:
    orders = daily_sales_krw / AVG_ORDER_KRW
    # 음성 사용률은 연령대 가정의 가중 평균(또는 직접 지정), 턴 배수는 항상 연령대 가정의 가중 평균
    base = sum(s * r for s, r, _ in AGE.values())
    mult = sum(s * r * m for s, r, m in AGE.values()) / base
    voice = base if voice_rate is None else voice_rate
    voice_orders = orders * voice * DAYS
    turns = voice_orders * TURNS_PER_ORDER * mult
    c = turn_cost(cache_hit)
    usd = {k: v * turns for k, v in c.items()}
    return {"orders_day": orders, "voice_rate": voice, "voice_orders_month": voice_orders, "turns_month": turns,
            "usd": usd, "krw": usd["total"] * KRW_PER_USD, "krw_per_order": usd["total"] * KRW_PER_USD / (voice_orders or 1) }


if __name__ == "__main__":
    for hit, label in ((0.0, "캐시 없음(상한)"), (0.8, "캐시 80%")):
        c = turn_cost(hit)
        print(f"[{label}] 음성 1턴 ${c['total']:.5f} = LLM {c['llm']:.5f} + STT {c['stt']:.5f} + TTS {c['tts']:.5f}")
    print()
    for sales in (1_500_000, 3_000_000, 6_000_000):
        for hit in (0.0, 0.8):
            m = month(sales, hit)
            print(f"하루 매출 {sales // 10000}만원 캐시{int(hit * 100)}% | 주문 {m['orders_day']:.0f}건/일 음성 {m['voice_rate']:.0%} "
                  f"음성주문 {m['voice_orders_month']:.0f}건/월 {m['turns_month']:.0f}턴 | ${m['usd']['total']:.0f} = {m['krw'] / 10000:.1f}만원 "
                  f"(LLM {m['usd']['llm'] / m['usd']['total']:.0%}) | 음성 주문 1건 {m['krw_per_order']:.0f}원")
    print()
    for rate in (0.10, 0.22, 0.40, 1.00):
        m = month(3_000_000, 0.0, rate)
        print(f"[민감도] 매출 300만원 음성 사용률 {rate:.0%}: ${m['usd']['total']:.0f} = {m['krw'] / 10000:.1f}만원/월")
    print()
    for age, (s, r, mu) in AGE.items():
        m = month(3_000_000, 0.0)
        share = s * r * mu / sum(a * b * c for a, b, c in AGE.values())
        print(f"{age}: 방문 {s:.0%} 음성 {r:.0%} → 음성 이용자 중 {s * r / sum(a * b for a, b, _ in AGE.values()):.0%}, 비용 비중 {share:.0%}")
