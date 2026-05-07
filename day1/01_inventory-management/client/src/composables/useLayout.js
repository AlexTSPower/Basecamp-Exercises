import { ref, watch } from 'vue'

const STORAGE_COLLAPSED = 'app:sidebarCollapsed'
const COLLAPSE_BREAKPOINT_PX = 900

function loadCollapsed() {
  if (typeof window === 'undefined') return false
  if (window.innerWidth < COLLAPSE_BREAKPOINT_PX) return true
  return localStorage.getItem(STORAGE_COLLAPSED) === '1'
}

const collapsed = ref(loadCollapsed())

watch(collapsed, (next) => {
  // why: only persist when above the breakpoint — otherwise the user's
  // narrow-window auto-collapse would stick when they open the app on
  // a wider screen later.
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
