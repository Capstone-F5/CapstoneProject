#!/bin/sh
# 라즈베리파이 키오스크 시작 스크립트 — PC(서버)에서 이 앱이 떠 있는 포트를 자동으로 찾아 Chromium을 키오스크로 연다.
#
# PC의 Vite 포트는 start_servers.ps1이 비어 있는 포트를 골라 쓰므로 서버를 다시 켤 때마다 바뀔 수 있다.
# 주소를 고정해 두면 "서버는 켜져 있는데 Pi에서 접속이 안 되는" 일이 생기므로, 5173~5200을 훑어
# 이 앱의 정적 파일(/vad.worklet.bundle.min.js)이 실제로 응답하는 포트를 찾는다.
# (다른 Vite 앱은 같은 경로에 index.html을 돌려주므로 '<'로 시작하면 건너뛴다.)
# PC 주소는 KIOSK_HOST 환경변수 또는 ~/kiosk-helper/pc_host 파일로 바꿀 수 있다.
HOST="${KIOSK_HOST:-$(cat "$HOME/kiosk-helper/pc_host" 2>/dev/null || echo 192.168.0.32)}"

find_port() {
  p=5173
  while [ "$p" -le 5200 ]; do
    body=$(curl -sk -m 3 "https://$HOST:$p/vad.worklet.bundle.min.js" 2>/dev/null | head -c 16)
    case "$body" in
      ""|"<"*) ;;
      *) echo "$p"; return 0 ;;
    esac
    p=$((p + 1))
  done
  return 1
}

# 서버가 아직 안 떠 있으면 뜰 때까지 기다린다
while :; do
  PORT=$(find_port) && break
  sleep 5
done

exec /usr/bin/chromium \
  --kiosk \
  --no-first-run \
  --no-default-browser-check \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --ignore-certificate-errors \
  "https://$HOST:$PORT"
