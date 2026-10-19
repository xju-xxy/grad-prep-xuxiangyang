/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 应急指挥大屏的深蓝黑底色，从深到浅排开
        abyss: {
          900: '#070c16',
          800: '#0b1220',
          700: '#0f1a2e',
          600: '#14203a',
          500: '#1b2b4a',
          400: '#243757',
        },
        cyanline: {
          400: '#67e8f9',
          500: '#22d3ee',
          600: '#06b6d4',
        },
        indigoink: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        amberwarn: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          '"Hiragino Sans GB"',
          'system-ui',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          '"Cascadia Code"',
          'Consolas',
          '"SFMono-Regular"',
          'monospace',
        ],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(34,211,238,0.18), 0 8px 40px -12px rgba(34,211,238,0.35)',
        panel: '0 24px 60px -30px rgba(2,8,23,0.9)',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '0.35', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.35)' },
        },
        drift: {
          '0%, 100%': { transform: 'translate3d(0,0,0)' },
          '50%': { transform: 'translate3d(0,-18px,0)' },
        },
        sweep: {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '200% 50%' },
        },
      },
      animation: {
        breathe: 'breathe 2.4s ease-in-out infinite',
        drift: 'drift 9s ease-in-out infinite',
        sweep: 'sweep 6s linear infinite',
      },
    },
  },
  plugins: [],
}
