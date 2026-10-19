import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 端口固定 5174，避免和仓库里另一个前端系统（crisis-sight）冲突
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
})
