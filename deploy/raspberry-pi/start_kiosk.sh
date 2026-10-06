#!/bin/sh
# 라즈베리파이 키오스크 시작 스크립트 — 부팅 때 labwc autostart가 실행한다.
#
# 기본(운영): 배포된 서버 https://cap.dmuce-stu.kr 를 키오스크로 연다. 네트워크·서버가 응답할 때까지 기다린 뒤 연다.
#   주소를 바꾸려면 KIOSK_URL 환경변수 또는 ~/kiosk-helper/kiosk_url 파일(첫 줄에 주소)을 쓴다.
#
# 개발(선택): ~/kiosk-helper/dev_host 파일(또는 KIOSK_DEV_HOST 환경변수)에 개발 PC 주소가 들어 있으면,
#   그 PC의 Vite(5173~5200) 중 이 앱이 응답하는 포트를 찾아 접속한다. start_servers.ps1이 빈 포트를 골라
#   쓰므로 PC를 다시 켤 때마다 포트가 바뀔 수 있어서다. (이 파일을 지우면 다시 운영 주소로 돌아간다.)
PROD_URL="${KIOSK_URL:-$(head -n 1 "$HOME/kiosk-helper/kiosk_url" 2>/dev/null)}"
PROD_URL="${PROD_URL:-https://cap.dmuce-stu.kr}"
DEV_HOST="${KIOSK_DEV_HOST:-$(head -n 1 "$HOME/kiosk-helper/dev_host" 2>/dev/null)}"

# 이 앱의 정적 파일이 실제로 응답하는지 본다. 다른 사이트나 오류 페이지는 같은 경로에 HTML('<')을 돌려주므로 건너뛴다.
app_is_up() {  # $1 = 기준 주소, $2 = curl 추가 옵션
  body=$(curl -s $2 -m 5 "$1/vad.worklet.bundle.min.js" 2>/dev/null | head -c 16)
  case "$body" in ""|"<"*) return 1 ;; *) return 0 ;; esac
}

if [ -n "$DEV_HOST" ]; then
  # ── 개발 모드: PC의 Vite 포트 탐색 ──
  while :; do
    p=5173
    URL=""
    while [ "$p" -le 5200 ]; do
      if app_is_up "https://$DEV_HOST:$p" "-k"; then URL="https://$DEV_HOST:$p"; break; fi
      p=$((p + 1))
    done
    [ -n "$URL" ] && break
    sleep 5
  done
  EXTRA="--ignore-certificate-errors"   # 개발 서버는 자체 서명 인증서
else
  # ── 운영 모드: 서버가 응답할 때까지 기다린다(부팅 직후에는 네트워크가 늦게 올라온다) ──
  until app_is_up "$PROD_URL" ""; do sleep 5; done
  URL="$PROD_URL"
  EXTRA=""
fi

exec /usr/bin/chromium \
  --kiosk \
  --no-first-run \
  --no-default-browser-check \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required \
  $EXTRA \
  "$URL"
