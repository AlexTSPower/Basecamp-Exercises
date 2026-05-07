<!--
  Reference shell for the redesigned App.vue.

  This is a TEMPLATE — adapt the route list, labels, icons, and any
  feature mounts (filter bar, modals, language switcher) to the target app.

  Hard requirements:
   - Sidebar fixed on the left (<aside>), full-height, persists collapsed
     state via useLayout / localStorage.
   - Each nav item: icon + label, active state via :class binding.
   - Top of sidebar: app logo. Bottom: theme toggle + user avatar (sticky).
   - Right column: <header class="topbar"> with breadcrumbs +
     <main class="content"> with the router view.
   - On viewport < 900px the sidebar should auto-collapse — handle that
     in useLayout, not in the template.
-->
<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <aside class="sidebar" :aria-expanded="!collapsed">
      <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true">◆</span>
        <span class="brand-text" v-if="!collapsed">{{ t('nav.companyName') }}</span>
      </div>

      <nav class="sidebar-nav" aria-label="Primary">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: $route.path === item.to }"
        >
          <span class="nav-icon" aria-hidden="true" v-html="item.icon" />
          <span class="nav-label" v-if="!collapsed">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="icon-btn" @click="toggleTheme" :aria-label="t('actions.toggleTheme')">
          <span aria-hidden="true">{{ theme === 'dark' ? '☾' : '☀' }}</span>
        </button>
        <button class="icon-btn" @click="toggleCollapsed" :aria-label="t('actions.toggleSidebar')">
          <span aria-hidden="true">{{ collapsed ? '›' : '‹' }}</span>
        </button>
      </div>
    </aside>

    <div class="content-wrap">
      <header class="topbar">
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <router-link to="/" class="crumb">{{ t('nav.overview') }}</router-link>
          <span v-if="currentCrumb" class="crumb-sep" aria-hidden="true">/</span>
          <span v-if="currentCrumb" class="crumb current">{{ currentCrumb }}</span>
        </nav>

        <div class="topbar-actions">
          <!-- The FilterBar belongs here if it is global; remove if filters are per-page. -->
          <FilterBar v-if="hasGlobalFilters" />
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

    <!-- Modals stay at the shell level so any view can trigger them. -->
    <ProfileDetailsModal :is-open="showProfileDetails" @close="showProfileDetails = false" />
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
import { useI18n } from './composables/useI18n'
import { useTheme } from './composables/useTheme'
import { useLayout } from './composables/useLayout'

import FilterBar from './components/FilterBar.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'

// Inline SVG strings keep the template clean while avoiding emoji per project rules.
// Adapt the d-paths to whichever route set the target app uses.
const ICON = {
  overview:   '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="11" y="3" width="6" height="6" rx="1.5"/><rect x="3" y="11" width="6" height="6" rx="1.5"/><rect x="11" y="11" width="6" height="6" rx="1.5"/></svg>',
  inventory:  '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 6l7-3 7 3v8l-7 3-7-3V6z"/><path d="M3 6l7 3 7-3"/><path d="M10 9v9"/></svg>',
  orders:     '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 4h10l1 4H4l1-4z"/><path d="M4 8h12v8H4z"/></svg>',
  finance:    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 17V7"/><path d="M8 17V11"/><path d="M13 17V4"/><path d="M18 17V9"/></svg>',
  demand:     '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 14l4-4 3 3 7-7"/><path d="M13 6h4v4"/></svg>',
  reports:    '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="3" width="12" height="14" rx="1.5"/><path d="M7 7h6"/><path d="M7 10h6"/><path d="M7 13h4"/></svg>',
}

export default {
  name: 'AppShell',
  components: { FilterBar, LanguageSwitcher, ProfileMenu, ProfileDetailsModal, TasksModal },
  setup() {
    const { t } = useI18n()
    const { theme, toggleTheme } = useTheme()
    const { collapsed, toggleCollapsed } = useLayout()
    const route = useRoute()

    // Source of truth for the sidebar — adapt to the target app's routes.
    const navItems = [
      { to: '/',           labelKey: 'nav.overview',        icon: ICON.overview },
      { to: '/inventory',  labelKey: 'nav.inventory',       icon: ICON.inventory },
      { to: '/orders',     labelKey: 'nav.orders',          icon: ICON.orders },
      { to: '/spending',   labelKey: 'nav.finance',         icon: ICON.finance },
      { to: '/demand',     labelKey: 'nav.demandForecast',  icon: ICON.demand },
      { to: '/reports',    labelKey: 'nav.reports',         icon: ICON.reports },
    ]

    const breadcrumbForPath = {
      '/':           '',
      '/inventory':  'nav.inventory',
      '/orders':     'nav.orders',
      '/spending':   'nav.finance',
      '/demand':     'nav.demandForecast',
      '/reports':    'nav.reports',
    }

    const currentCrumb = computed(() => {
      const key = breadcrumbForPath[route.path]
      return key ? t(key) : ''
    })

    // Allow [ and ] to toggle the sidebar — fast keyboard for power users.
    // why: explicit listener instead of @keydown on the shell so it works
    // even when focus is inside an input field.
    const onKeydown = (e) => {
      if (e.target.matches('input, textarea, [contenteditable="true"]')) return
      if (e.key === '[' || e.key === ']') toggleCollapsed()
    }
    onMounted(() => window.addEventListener('keydown', onKeydown))
    onUnmounted(() => window.removeEventListener('keydown', onKeydown))

    const hasGlobalFilters = true
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const tasks = ref([])

    return {
      t,
      theme, toggleTheme,
      collapsed, toggleCollapsed,
      navItems, currentCrumb,
      hasGlobalFilters,
      showProfileDetails, showTasks, tasks,
    }
  }
}
</script>

<style>
/* Non-scoped on purpose — these styles describe the shell layout itself.
   Per-component styles inside views remain scoped. */

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
  padding: var(--space-5) var(--space-5);
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  border-bottom: 1px solid var(--color-border);
}
.brand-mark {
  font-size: 18px;
  color: var(--color-accent);
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
  min-width: 0; /* lets tables shrink instead of overflowing */
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
.crumb { color: var(--color-text-muted); }
.crumb.current {
  color: var(--color-text);
  font-weight: var(--weight-semibold);
}
.crumb-sep { color: var(--color-text-faint); }

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
</style>
