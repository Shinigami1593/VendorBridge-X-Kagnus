<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  BarChart3,
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

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const logoutConfirm = ref(false)
const logoutLoading = ref(false)
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
].filter((item) => auth.role !== 'vendor' || !['dashboard', 'vendors'].includes(item.name)))

function askToLogout() {
  menuOpen.value = false
  logoutConfirm.value = true
}

async function confirmLogout() {
  logoutLoading.value = true
  let notice = ''
  try {
    await auth.logout()
  } catch (err) {
    notice = err.response?.data?.error || 'You have been signed out, but the server could not confirm the logout.'
  } finally {
    logoutConfirm.value = false
    logoutLoading.value = false
  }
  await router.replace({ path: '/login', query: notice ? { notice } : {} })
}
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
            :class="{ 'nav-active': route.name === item.name }"
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
