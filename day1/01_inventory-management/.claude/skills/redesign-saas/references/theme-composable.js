// Reference composables for the SaaS redesign.
//
// Drop these into client/src/composables/ as two files:
//   useTheme.js   — exports useTheme()
//   useLayout.js  — exports useLayout()
//
// Both are singletons: module-level refs so every consumer reads the
// same value and a change in one place updates the whole app.

import { ref, watch } from 'vue'

const STORAGE_THEME = 'app:theme'
const STORAGE_COLLAPSED = 'app:sidebarCollapsed'
const COLLAPSE_BREAKPOINT_PX = 900

/**
 * useTheme — light/dark mode toggle.
 *
 * - Reads localStorage first; falls back to prefers-color-scheme.
 * - Writes the chosen value to <html data-theme="…"> so tokens.css picks it up.
 * - Persists every change.
 */
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


/**
 * useLayout — sidebar collapsed state, persisted + responsive.
 *
 * - Auto-collapses below COLLAPSE_BREAKPOINT_PX so the layout fits on
 *   small screens.
 * - User's manual choice still wins above the breakpoint; we only
 *   force-collapse, never force-expand.
 */
const collapsed = ref(loadCollapsed())

function loadCollapsed() {
  if (typeof window === 'undefined') return false
  if (window.innerWidth < COLLAPSE_BREAKPOINT_PX) return true
  const stored = localStorage.getItem(STORAGE_COLLAPSED)
  return stored === '1'
}

watch(collapsed, (next) => {
  // why: only persist when above the breakpoint — otherwise the
  // user's narrow-window auto-collapse would stick when they open
  // the app on a wider screen later.
  if (window.innerWidth >= COLLAPSE_BREAKPOINT_PX) {
    localStorage.setItem(STORAGE_COLLAPSED, next ? '1' : '0')
  }
})

if (typeof window !== 'undefined') {
  window.addEventListener('resize', () => {
    if (window.innerWidth < COLLAPSE_BREAKPOINT_PX && !collapsed.value) {
      collapsed.value = true
    }
  })
}

export function useLayout() {
  const toggleCollapsed = () => { collapsed.value = !collapsed.value }
  const setCollapsed = (value) => { collapsed.value = !!value }
  return { collapsed, toggleCollapsed, setCollapsed }
}
