<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  BarChart3,
  Bell,
  CheckCheck,
  ClipboardList,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageCheck,
  ReceiptText,
  Search,
  Store,
  X,
} from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'
import { useAuth } from '../stores/auth'
import { useNotifications } from '../stores/notifications'
import { getErrorMessage } from '../utils/errors'
import { timeAgo } from '../utils/format'

const auth = useAuth()
const notifications = useNotifications()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const notificationOpen = ref(false)
const notificationLoading = ref(false)
const notificationError = ref('')
const notificationDropdown = ref(null)
const notificationButton = ref(null)
const logoutConfirm = ref(false)
const logoutLoading = ref(false)
let unreadTimer
const reportRoles = ['admin', 'officer', 'manager']
const roleLabels = {
  admin: 'Admin',
  officer: 'Procurement Officer',
  manager: 'Manager/Approver',
  vendor: 'Vendor',
}
const user = computed(() => auth.user || {})
const userName = computed(() => {
  const current = user.value
  return current.name || [current.first_name, current.last_name].filter(Boolean).join(' ') || current.email || 'User'
})
const initials = computed(() => userName.value.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase())
const photo = computed(() => user.value.photo || user.value.photo_url || user.value.avatar || '')
const roleLabel = computed(() => roleLabels[auth.role] || auth.role || 'User')
const items = computed(() => [
  { label: 'Dashboard', to: '/', name: 'dashboard', icon: LayoutDashboard },
  { label: 'Vendors', to: '/vendors', name: 'vendors', icon: Store },
  { label: "RFQ's", to: '/rfqs', name: 'rfqs', icon: ClipboardList },
  { label: 'Quotations', to: '/quotations', name: 'quotations', icon: FileText },
  { label: 'Approvals', to: '/approvals', name: 'approvals', icon: CheckCheck },
  { label: 'Purchase orders', to: '/purchase-orders', name: 'purchase-orders', icon: PackageCheck },
  { label: 'Invoices', to: '/invoices', name: 'invoices', icon: ReceiptText },
  { label: 'Reports', to: '/reports', name: 'reports', icon: BarChart3 },
  { label: 'Activity', to: '/activity', name: 'activity', icon: Activity },
].filter((item) => (
  (!['reports', 'activity'].includes(item.name) || reportRoles.includes(auth.role))
  && (auth.role !== 'vendor' || ['rfqs', 'quotations', 'purchase-orders', 'invoices'].includes(item.name))
)))

function isActive(item) {
  return route.name === item.name || (item.to !== '/' && route.path.startsWith(`${item.to}/`))
}

function askToLogout() {
  menuOpen.value = false
  notificationOpen.value = false
  logoutConfirm.value = true
}

async function refreshUnreadCount() {
  try {
    await notifications.fetchUnreadCount()
    notificationError.value = ''
  } catch (error) {
    notificationError.value = getErrorMessage(error, 'Unable to refresh notifications.')
  }
}

function stopUnreadRefresh() {
  if (unreadTimer) {
    clearInterval(unreadTimer)
    unreadTimer = undefined
  }
}

function startUnreadRefresh() {
  stopUnreadRefresh()
  if (!auth.isLoggedIn) return
  refreshUnreadCount()
  unreadTimer = setInterval(refreshUnreadCount, 60000)
}

async function toggleNotifications() {
  notificationOpen.value = !notificationOpen.value
  notificationError.value = ''
  if (!notificationOpen.value) return
  notificationLoading.value = true
  try {
    await Promise.all([notifications.fetchLatest(), notifications.fetchUnreadCount()])
  } catch (error) {
    notificationError.value = getErrorMessage(error, 'Unable to load notifications.')
  } finally {
    notificationLoading.value = false
  }
}

async function openNotification(item) {
  notificationError.value = ''
  try {
    if (!item.is_read) await notifications.markRead(item.id)
    notificationOpen.value = false
    await router.push(item.link || '/notifications')
  } catch (error) {
    notificationError.value = getErrorMessage(error, 'Unable to open this notification.')
  }
}

async function markAllNotificationsRead() {
  notificationError.value = ''
  try {
    await notifications.markAllRead()
  } catch (error) {
    notificationError.value = getErrorMessage(error, 'Unable to mark notifications as read.')
  }
}

function handleOutsideClick(event) {
  if (!notificationDropdown.value?.contains(event.target)) notificationOpen.value = false
}

function handleEscape(event) {
  if (event.key === 'Escape' && notificationOpen.value) {
    notificationOpen.value = false
    notificationButton.value?.focus()
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible' && auth.isLoggedIn) refreshUnreadCount()
}

async function confirmLogout() {
  logoutLoading.value = true
  let notice = ''
  try {
    await auth.logout()
  } catch (err) {
    notice = getErrorMessage(err, 'You have been signed out, but the server could not confirm the logout.')
  } finally {
    logoutConfirm.value = false
    logoutLoading.value = false
  }
  await router.replace({ path: '/login', query: notice ? { notice } : {} })
}

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    startUnreadRefresh()
  } else {
    stopUnreadRefresh()
    notificationOpen.value = false
    notifications.unreadCount = 0
    notifications.items = []
  }
})

onMounted(() => {
  startUnreadRefresh()
  document.addEventListener('pointerdown', handleOutsideClick)
  document.addEventListener('keydown', handleEscape)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopUnreadRefresh()
  document.removeEventListener('pointerdown', handleOutsideClick)
  document.removeEventListener('keydown', handleEscape)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <button class="menu-toggle" type="button" aria-label="Toggle navigation" @click="menuOpen = !menuOpen">
        <X v-if="menuOpen" :size="19" />
        <Menu v-else :size="19" />
      </button>
      <label class="top-search">
        <Search :size="17" aria-hidden="true" />
        <input type="search" placeholder="Search" aria-label="Search">
      </label>
      <div class="topbar-user">
        <div ref="notificationDropdown" class="notification-menu">
          <button
            ref="notificationButton"
            class="notification-bell"
            type="button"
            :aria-label="`Notifications${notifications.unreadCount ? `, ${notifications.unreadCount} unread` : ''}`"
            aria-haspopup="true"
            :aria-expanded="notificationOpen"
            aria-controls="notification-dropdown"
            @click="toggleNotifications"
          >
            <Bell :size="19" aria-hidden="true" />
            <span v-if="notifications.unreadCount" class="notification-count">
              {{ notifications.unreadCount > 9 ? '9+' : notifications.unreadCount }}
            </span>
          </button>
          <section
            v-if="notificationOpen"
            id="notification-dropdown"
            class="notification-dropdown"
            aria-label="Latest notifications"
          >
            <div class="notification-dropdown-heading">
              <strong>Notifications</strong>
              <button
                type="button"
                class="notification-mark-all"
                :disabled="!notifications.unreadCount"
                @click="markAllNotificationsRead"
              >
                Mark all as read
              </button>
            </div>
            <p v-if="notificationLoading" class="notification-feedback" role="status">Loading notifications…</p>
            <p v-else-if="notificationError" class="form-error notification-feedback" role="alert">{{ notificationError }}</p>
            <ul v-else-if="notifications.items.length" class="notification-latest-list">
              <li v-for="item in notifications.items" :key="item.id">
                <button
                  type="button"
                  class="notification-latest-item"
                  :class="{ 'notification-unread': !item.is_read }"
                  @click="openNotification(item)"
                >
                  <span class="notification-unread-dot" :class="{ 'notification-dot-hidden': item.is_read }"></span>
                  <span class="notification-latest-copy">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.message }}</span>
                    <small>{{ timeAgo(item.created_at) }}</small>
                  </span>
                </button>
              </li>
            </ul>
            <p v-else class="notification-feedback">No notifications yet.</p>
            <RouterLink class="notification-view-all" to="/notifications" @click="notificationOpen = false">
              View all
            </RouterLink>
          </section>
        </div>
        <img v-if="photo" class="user-avatar" :src="photo" :alt="userName">
        <span v-else class="user-avatar user-initials">{{ initials }}</span>
        <div class="user-details">
          <strong>{{ userName }}</strong>
          <span>{{ user.email || roleLabel }}</span>
        </div>
      </div>
    </header>
    <div class="app-body">
      <div v-if="menuOpen" class="mobile-overlay" @click="menuOpen = false"></div>
      <aside class="sidebar" :class="{ 'sidebar-open': menuOpen }">
        <RouterLink class="brand" to="/" @click="menuOpen = false">VendorBridge</RouterLink>
        <nav aria-label="Main navigation">
          <span class="nav-group-title">Menu</span>
          <RouterLink
            v-for="item in items"
            :key="item.name"
            :to="item.to"
            class="nav-item"
            :class="{ 'nav-active': isActive(item) }"
            @click="menuOpen = false"
          >
            <component :is="item.icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
        <div class="sidebar-general">
          <span class="nav-group-title">General</span>
          <button class="nav-item nav-logout" type="button" @click="askToLogout">
            <LogOut :size="17" :stroke-width="1.8" aria-hidden="true" />
            <span>Logout</span>
          </button>
        </div>
      </aside>
      <main class="page-content">
        <router-view />
      </main>
    </div>
    <BaseModal v-if="logoutConfirm" title="Log out?" @close="logoutConfirm = false">
      <p class="logout-confirm-copy">Are you sure you want to log out of your account?</p>
      <div class="modal-actions logout-confirm-actions">
        <button
          class="button button-secondary"
          type="button"
          :disabled="logoutLoading"
          @click="logoutConfirm = false"
        >
          Cancel
        </button>
        <button
          class="button button-primary"
          type="button"
          :disabled="logoutLoading"
          @click="confirmLogout"
        >
          {{ logoutLoading ? 'Logging out…' : 'Logout' }}
        </button>
      </div>
    </BaseModal>
  </div>
</template>
