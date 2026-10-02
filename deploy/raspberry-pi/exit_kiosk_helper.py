#!/usr/bin/env python3
"""키오스크 Chromium을 전체화면(--kiosk)에서 창 모드로 되돌리는 로컬 도우미.

웹 페이지의 JS는 --kiosk 전체화면을 해제할 수 없어서, 화면 좌상단 10회 터치 시
프론트가 이 서버(127.0.0.1:8765)로 신호를 보내면 Chromium을 --kiosk 없이 다시 띄운다.
다음 부팅 때는 labwc autostart가 다시 --kiosk로 실행한다.
"""
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST, PORT = "127.0.0.1", 8765
# 키오스크 프론트가 제공되는 origin만 허용 (사설망 IP 또는 운영 도메인)
ALLOWED_ORIGIN = re.compile(r"^https://(192\.168\.\d{1,3}\.\d{1,3}(:\d+)?|cap\.dmuce-stu\.kr)$")


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if ALLOWED_ORIGIN.match(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        if self.path != "/exit-fullscreen" or not ALLOWED_ORIGIN.match(origin):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self._cors()
        self.end_headers()
        exit_fullscreen(origin)

    def log_message(self, *args):
        pass


def exit_fullscreen(url):
    subprocess.run(["pkill", "-x", "chromium"])
    time.sleep(2)
    env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/%d" % os.getuid(), WAYLAND_DISPLAY="wayland-0")
    subprocess.Popen(
        ["/usr/bin/chromium", "--ozone-platform=wayland", "--no-first-run",
         "--no-default-browser-check", "--ignore-certificate-errors", url + "/"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )


if __name__ == "__main__":
    HTTPServer((HOST, PORT), Handler).serve_forever()
