/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        asphalt: { DEFAULT: '#1F2328', soft: '#2C3138' },
        // Indian national highway signs: white on green, with reflective yellow for caution
        sign: { DEFAULT: '#0B6E4F', dark: '#08573E', soft: '#E3F1EC' },
        caution: '#F2C200',
        stop: '#B42318',
        concrete: { DEFAULT: '#F3F4F2', line: '#DADDD8' },
        muted: '#5C6168',
      },
      fontFamily: { sans: ['Overpass', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
};
