import { ref, watch } from 'vue'

const STORAGE_THEME = 'app:theme'

const initialTheme = (() => {
  const stored = localStorage.getItem(STORAGE_THEME)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
})()

const theme = ref(initialTheme)

const applyTheme = (value) => {
  document.documentElement.setAttribute('data-theme', value)
}
applyTheme(theme.value)

watch(theme, (next) => {
  applyTheme(next)
  localStorage.setItem(STORAGE_THEME, next)
})

export function useTheme() {
  const toggleTheme = () => { theme.value = theme.value === 'dark' ? 'light' : 'dark' }
  const setTheme = (value) => { theme.value = value }
  return { theme, toggleTheme, setTheme }
}
