import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [react(), basicSsl()],
  base: './',
  server: {
    host: '0.0.0.0',   // 같은 망의 다른 기기에서 접근 허용
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/api': {
        target: 'http://localhost:8000',
      },
      '/ai_modules': {
        target: 'http://localhost:8000',
      },
    },
  },
})
