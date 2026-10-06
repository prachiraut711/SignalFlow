import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Resolve target: inside Docker Compose, VITE_BACKEND_URL is http://backend:8000;
// for local host development outside Docker, default to http://localhost:8000
const backendUrl = process.env.VITE_BACKEND_URL || 'http://localhost:8000';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/health': {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
});
