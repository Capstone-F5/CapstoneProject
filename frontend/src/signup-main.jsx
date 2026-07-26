import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { LocaleProvider } from './i18n/LocaleContext'
import SignupScreen from './screens/SignupScreen'

// 회원가입 전용 진입점 — 키오스크 주문 SPA(main.jsx/App.jsx)와 완전히 분리된 별도 페이지.
// 세션/카트/제스처/음성 상태를 전혀 공유하지 않고, 오직 POST /api/user/register 만 사용한다.
// "뒤로가기"/"처음으로"는 SPA 내부 화면 전환이 아니라 실제 페이지 이동으로 처리한다.
function goToKiosk() {
  window.location.href = './index.html'
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LocaleProvider>
      <SignupScreen nav={goToKiosk} />
    </LocaleProvider>
  </StrictMode>,
)
