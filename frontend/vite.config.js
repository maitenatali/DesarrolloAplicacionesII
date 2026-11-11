import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Backend local (teacher-service + simulador de CORE). Cambiar con BACKEND_URL=http://localhost:8090 npm run dev
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.BACKEND_URL || 'http://localhost:8080';
  return {
    plugins: [react()],
    server: {
      port: 5173,
      // El orden importa: primero el gateway del Portal Docente, después CORE.
      proxy: {
        '/api/v1/teacher': { target, changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/v1\/teacher/, '/api/v1') },
        '/api/v1': { target, changeOrigin: true },
        '/.well-known': { target, changeOrigin: true },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        '/api/v1/teacher': { target, changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/v1\/teacher/, '/api/v1') },
        '/api/v1': { target, changeOrigin: true },
      },
    },
    test: { environment: 'jsdom', globals: true, setupFiles: './src/test/setup.js' },
  };
});
