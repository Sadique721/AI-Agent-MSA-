/** @type {import('tailwindcss').Config} */
export default {
  // Only scan JSX files — NOT node_modules or dist
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // MSA Design System tokens
      colors: {
        'msa-bg':      '#050b18',
        'msa-surface': '#0d1525',
        'msa-border':  '#1e2d47',
        'msa-accent':  '#6366f1',
        'msa-text':    '#e2e8f0',
        'msa-muted':   '#64748b',
      },
      fontFamily: {
        'sans':    ['Inter', 'system-ui', 'sans-serif'],
        'display': ['Orbitron', 'monospace'],
        'mono':    ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
