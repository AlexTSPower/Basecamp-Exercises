<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <aside class="sidebar" :aria-expanded="!collapsed">
      <div class="sidebar-brand" :title="collapsed ? t('nav.companyName') : null">
        <span class="brand-mark" aria-hidden="true">&#9670;</span>
        <span class="brand-text" v-if="!collapsed">{{ t('nav.companyName') }}</span>
      </div>

      <nav class="sidebar-nav" aria-label="Primary">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: $route.path === item.to }"
          :title="collapsed ? t(item.labelKey) : null"
        >
          <span class="nav-icon" aria-hidden="true" v-html="item.icon" />
          <span class="nav-label" v-if="!collapsed">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="icon-btn" @click="toggleTheme" :aria-label="t('actions.toggleTheme')" :title="t('actions.toggleTheme')">
          <span aria-hidden="true">{{ theme === 'dark' ? '&#9790;' : '&#9728;' }}</span>
        </button>
        <button class="icon-btn" @click="toggleCollapsed" :aria-label="t('actions.toggleSidebar')" :title="t('actions.toggleSidebar')">
          <span aria-hidden="true">{{ collapsed ? '&#8250;' : '&#8249;' }}</span>
        </button>
      </div>
    </aside>

    <!-- why: real element backdrop so tap-to-close works on mobile without
         relying on ::before pseudo-elements, which cannot receive click events. -->
    <div
      v-if="!collapsed"
      class="sidebar-backdrop"
      @click="toggleCollapsed"
    />

    <div class="content-wrap">
      <header class="topbar">
        <button
          class="hamburger-btn icon-btn"
          @click="toggleCollapsed"
          :aria-label="t('actions.toggleSidebar')"
        >
          <span aria-hidden="true">&#9776;</span>
        </button>
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <router-link to="/" class="crumb">{{ t('nav.overview') }}</router-link>
          <span v-if="currentCrumb" class="crumb-sep" aria-hidden="true">/</span>
          <span v-if="currentCrumb" class="crumb current">{{ currentCrumb }}</span>
        </nav>

        <div class="topbar-actions">
          <FilterBar />
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { useTheme } from './composables/useTheme'
import { useLayout } from './composables/useLayout'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

// Inline SVG icon strings — avoids external deps while keeping the template readable.
const ICON = {
  overview:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="11" y="3" width="6" height="6" rx="1.5"/><rect x="3" y="11" width="6" height="6" rx="1.5"/><rect x="11" y="11" width="6" height="6" rx="1.5"/></svg>',
  inventory:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 6l7-3 7 3v8l-7 3-7-3V6z"/><path d="M3 6l7 3 7-3"/><path d="M10 9v9"/></svg>',
  orders:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 4h10l1 4H4l1-4z"/><path d="M4 8h12v8H4z"/></svg>',
  finance:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 17V7"/><path d="M8 17V11"/><path d="M13 17V4"/><path d="M18 17V9"/></svg>',
  demand:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 14l4-4 3 3 7-7"/><path d="M13 6h4v4"/></svg>',
  // Downward arrow into a box — represents restocking / inbound stock movement.
  restocking:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="12" width="14" height="5" rx="1"/><path d="M10 3v9"/><path d="M7 9l3 3 3-3"/></svg>',
  reports:
    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="3" width="12" height="14" rx="1.5"/><path d="M7 7h6"/><path d="M7 10h6"/><path d="M7 13h4"/></svg>',
}

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { theme, toggleTheme } = useTheme()
    const { collapsed, toggleCollapsed } = useLayout()
    const route = useRoute()

    // Ordered nav items — icons are inline SVG strings, labels resolved via i18n.
    const navItems = [
      { to: '/',           labelKey: 'nav.overview',       icon: ICON.overview },
      { to: '/inventory',  labelKey: 'nav.inventory',      icon: ICON.inventory },
      { to: '/orders',     labelKey: 'nav.orders',         icon: ICON.orders },
      { to: '/spending',   labelKey: 'nav.finance',        icon: ICON.finance },
      { to: '/demand',     labelKey: 'nav.demandForecast', icon: ICON.demand },
      { to: '/restocking', labelKey: 'nav.restocking',     icon: ICON.restocking },
      { to: '/reports',    labelKey: 'nav.reports',        icon: ICON.reports },
    ]

    // Map from route paths to i18n keys so breadcrumbs are data-driven.
    const breadcrumbForPath = {
      '/':           '',
      '/inventory':  'nav.inventory',
      '/orders':     'nav.orders',
      '/spending':   'nav.finance',
      '/demand':     'nav.demandForecast',
      '/restocking': 'nav.restocking',
      '/reports':    'nav.reports',
    }

    const currentCrumb = computed(() => {
      const key = breadcrumbForPath[route.path]
      return key ? t(key) : ''
    })

    // Keyboard shortcut: [ and ] toggle the sidebar.
    // why: listener is on window, not the shell element, so it fires even
    // when focus is inside a form field inside the main content area.
    const onKeydown = (e) => {
      if (e.target.matches('input, textarea, [contenteditable="true"]')) return
      if (e.key === '[' || e.key === ']') toggleCollapsed()
    }
    onMounted(() => window.addEventListener('keydown', onKeydown))
    onUnmounted(() => window.removeEventListener('keydown', onKeydown))

    // Task management — unchanged from the original App.vue.
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)
        if (isMockTask) {
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) currentUser.value.tasks.splice(index, 1)
        } else {
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)
        if (mockTask) {
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) apiTasks.value[index] = updatedTask
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      theme, toggleTheme,
      collapsed, toggleCollapsed,
      navItems, currentCrumb,
      showProfileDetails, showTasks, tasks,
      addTask, deleteTask, toggleTask,
    }
  },
}
</script>

<style>
/* Non-scoped — these are global layout and utility styles.
   tokens.css (imported in main.js) provides: .card, .card-header, .card-title,
   .btn, .btn-primary, .btn-ghost, .btn-danger, .badge (+variants), .table (.num).
   This block owns: shell layout, preserved view helpers, and tokenized utilities. */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ===== SHELL LAYOUT ===== */

.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: 100vh;
  background: var(--color-bg);
  transition: grid-template-columns var(--duration-base) var(--ease-out);
}

.app-shell.sidebar-collapsed {
  grid-template-columns: var(--sidebar-width-collapsed) 1fr;
}

.sidebar {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5);
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  border-bottom: 1px solid var(--color-border);
}

.brand-mark {
  font-size: 18px;
  color: var(--color-accent);
  flex-shrink: 0;
}

.brand-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: var(--space-3);
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  border-left: 2px solid transparent;
  text-decoration: none;
  transition:
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.nav-item:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.nav-item.active {
  background: var(--color-accent-soft);
  color: var(--color-accent-text);
  border-left-color: var(--color-accent);
}

.nav-icon {
  display: inline-flex;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
}

.icon-btn:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.icon-btn:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.content-wrap {
  display: flex;
  flex-direction: column;
  min-width: 0; /* prevents tables from overflowing the grid cell */
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--content-padding-x);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 5;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

.crumb {
  color: var(--color-text-muted);
  text-decoration: none;
}

.crumb.current {
  color: var(--color-text);
  font-weight: var(--weight-semibold);
}

.crumb-sep {
  color: var(--color-text-faint);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.content {
  padding: var(--space-8) var(--content-padding-x);
  max-width: var(--content-max-width);
  width: 100%;
  margin: 0 auto;
}

/* ===== VIEW HELPERS (kept from old App.vue, tokenized) ===== */

/* Page header used by most views */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

/* KPI / stat cards grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: box-shadow var(--duration-fast) var(--ease-out);
}

.stat-card:hover {
  box-shadow: var(--shadow-sm);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 2.25rem;
  font-weight: var(--weight-bold);
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value { color: var(--color-warning); }
.stat-card.success .stat-value { color: var(--color-success); }
.stat-card.danger  .stat-value { color: var(--color-danger); }
.stat-card.info    .stat-value { color: var(--color-info); }

/* Table scroll wrapper */
.table-container {
  overflow-x: auto;
}

/* Badge variants not in tokens.css (trend / priority semantics) */
.badge.increasing {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.badge.decreasing {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.badge.stable {
  background: var(--color-info-soft);
  color: var(--color-info);
}

.badge.high {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.badge.medium {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.badge.low {
  background: var(--color-info-soft);
  color: var(--color-info);
}

/* Loading / error states */
.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-muted);
}

.error {
  background: var(--color-danger-soft);
  border: 1px solid var(--color-danger);
  color: var(--color-danger);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
}

/* === Collapsed-mode layout overrides === */

/* why: in 64px width the icon needs to center; the regular nav-item padding
   leaves the icon left-aligned and the active border-left looks like a thin
   stripe pinned to the wrong edge. Switch to centered icon and a right-edge
   accent bar instead. */
.app-shell.sidebar-collapsed .sidebar-brand {
  justify-content: center;
  padding: var(--space-5) 0;
}

.app-shell.sidebar-collapsed .nav-item {
  justify-content: center;
  padding: var(--space-3) 0;
  border-left-color: transparent !important;
  position: relative;
}

.app-shell.sidebar-collapsed .nav-item.active::after {
  content: '';
  position: absolute;
  right: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: var(--radius-pill) 0 0 var(--radius-pill);
  background: var(--color-accent);
}

/* why: two icon-btns won't fit side by side at 64px (2*32 + gap + padding > 64),
   stack them vertically so both stay reachable. */
.app-shell.sidebar-collapsed .sidebar-footer {
  flex-direction: column;
  align-items: center;
}

/* === Mobile overlay (<640px) === */

/* Backdrop: hidden by default, shown only on mobile when sidebar is open. */
.sidebar-backdrop { display: none; }

/* why: hamburger lives in the topbar so the user can re-open the drawer once
   the sidebar slides offscreen on phones. Hidden above the mobile breakpoint. */
.hamburger-btn { display: none; }

@media (max-width: 640px) {
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: var(--color-overlay);
    z-index: 20;
    cursor: pointer;
  }

  .hamburger-btn {
    display: inline-flex;
    margin-right: var(--space-2);
  }
}

@media (max-width: 640px) {
  /* why: at phone widths a 64px column still steals ~17% of the viewport.
     Instead, lift the sidebar out of the grid so content gets the full row;
     the sidebar overlays from the left and the user can dismiss it by
     tapping the backdrop or pressing the toggle. */
  .app-shell {
    grid-template-columns: 1fr !important;
  }
  .app-shell.sidebar-collapsed { grid-template-columns: 1fr !important; }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: var(--sidebar-width);
    z-index: 30;
    transform: translateX(-100%);
    transition: transform var(--duration-base) var(--ease-out);
    box-shadow: var(--shadow-lg);
  }

  /* On mobile, the `collapsed` state inverts: collapsed = drawer hidden,
     expanded = drawer visible. Above 640px collapsed means icons-only. */
  .app-shell:not(.sidebar-collapsed) .sidebar {
    transform: translateX(0);
  }

  .app-shell:not(.sidebar-collapsed) .sidebar .nav-label,
  .app-shell:not(.sidebar-collapsed) .sidebar .brand-text {
    display: inline;
  }
}
</style>
