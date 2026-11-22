import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    strictPort: true,
    host: '127.0.0.1',
    watch: {
      ignored: ['**/AI_workflow/**', '**/server/**', '**/dist/**', '**/scratch/**', '**/docs/**'],
    },
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
        secure: false,
      },

      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const setCookie = proxyRes.headers['set-cookie'];
            if (setCookie) {
              proxyRes.headers['set-cookie'] = setCookie.map(cookie =>
                cookie.replace(/;\s*Secure/gi, '').replace(/;\s*SameSite=Strict/gi, '; SameSite=Lax')
              );
            }
          });
        }
      }
    }
  }
})
