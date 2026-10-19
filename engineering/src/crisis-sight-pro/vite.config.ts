import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 纯前端工程，没有后端代理，dev 端口固定 5173
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
