import { fileURLToPath, URL } from 'node:url'
import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// vad-react/onnxruntime 소스맵 경고 억제 (warn + warnOnce 모두 처리)
const logger = createLogger()
const suppress = (msg) =>
  typeof msg === 'string' &&
  msg.includes('Sourcemap') &&
  msg.includes('missing source files')

const _warn = logger.warn.bind(logger)
logger.warn = (msg, opts) => { if (!suppress(msg)) _warn(msg, opts) }

const _warnOnce = logger.warnOnce?.bind(logger)
if (_warnOnce) {
  logger.warnOnce = (msg, opts) => { if (!suppress(msg)) _warnOnce(msg, opts) }
}

export default defineConfig({
  customLogger: logger,
  plugins: [react(), basicSsl()],
  base: './',
  optimizeDeps: {
    // vad-react / vad-web: CJS → ESM 변환을 위해 pre-bundle 포함
    include: ['@ricky0123/vad-react', '@ricky0123/vad-web'],
    // onnxruntime-web: pre-bundle 제외 — Vite가 동적 import(.jsep.mjs 등) 경로를
    // /node_modules/.vite/deps/ 로 고정시켜 파일을 못 찾는 문제 방지.
    // 이 패키지는 ESM(ort.bundle.min.mjs)이므로 node_modules 직접 서빙 가능.
    exclude: ['onnxruntime-web'],
  },
  build: {
    rollupOptions: {
      // 회원가입은 키오스크 주문 SPA와 별개의 정적 페이지로 따로 빌드된다(signup.html).
      input: {
        main:   fileURLToPath(new URL('./index.html', import.meta.url)),
        signup: fileURLToPath(new URL('./signup.html', import.meta.url)),
      },
      onwarn(warning, warn) {
        if (warning.code === 'SOURCEMAP_ERROR') return
        warn(warning)
      },
    },
  },
  server: {
    host: '0.0.0.0',
    headers: {
      // onnxruntime-web 1.18+은 threaded WASM만 제공 → SharedArrayBuffer 필요
      // credentialless: 프록시 API 요청에 영향 없이 SAB 허용
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'credentialless',
    },
    proxy: {
      '/ws': { target: 'ws://localhost:8000', ws: true },
      '/api': { target: 'http://localhost:8000' },
      '/ai_modules': { target: 'http://localhost:8000' },
    },
  },
})
