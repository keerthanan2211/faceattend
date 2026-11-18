import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  // In development, /api goes to FastAPI, so no CORS setup is needed
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
});
