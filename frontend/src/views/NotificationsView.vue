<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import { useNotifications } from '../stores/notifications'
import { getErrorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/format'

const router = useRouter()
const notifications = useNotifications()
const items = ref([])
const loading = ref(false)
const error = ref('')
const unreadOnly = ref(false)
const category = ref('')
const nextPage = ref(1)
const hasMore = ref(false)
const categoryLabels = {
  rfq: 'RFQ',
  approval: 'Approval',
  invoice: 'Invoice',
  po: 'Purchase order',
}
const empty = computed(() => !loading.value && !error.value && items.value.length === 0)

async function loadPage(page = 1, append = false) {
  loading.value = true
  error.value = ''
  try {
    const params = { page }
    if (unreadOnly.value) params.unread = true
    if (category.value) params.category = category.value
    const response = await api.get('/notifications/', { params })
    const results = response.data.results || []
    items.value = append ? [...items.value, ...results] : results
    hasMore.value = Boolean(response.data.next)
    nextPage.value = page + 1
  } catch (requestError) {
    error.value = getErrorMessage(requestError, 'Unable to load notifications.')
  } finally {
    loading.value = false
  }
}

async function markRead(item) {
  try {
    const updated = await notifications.markRead(item.id)
    const index = items.value.findIndex((notification) => notification.id === item.id)
    if (index !== -1) items.value[index] = updated
    if (unreadOnly.value) items.value = items.value.filter((notification) => notification.id !== item.id)
  } catch (requestError) {
    error.value = getErrorMessage(requestError, 'Unable to mark this notification as read.')
  }
}

async function markAllRead() {
  error.value = ''
  try {
    await notifications.markAllRead()
    if (unreadOnly.value) {
      items.value = []
      hasMore.value = false
    } else {
      items.value = items.value.map((item) => ({ ...item, is_read: true }))
    }
  } catch (requestError) {
    error.value = getErrorMessage(requestError, 'Unable to mark notifications as read.')
  }
}

async function openNotification(item) {
  if (!item.is_read) await markRead(item)
  if (item.link) await router.push(item.link)
}

watch([unreadOnly, category], () => loadPage())
onMounted(() => loadPage())
</script>

<template>
  <section class="page notifications-page">
    <div class="page-heading">
      <div>
        <h1>Notifications</h1>
        <p class="muted">Updates about your procurement activity</p>
      </div>
      <button
        class="button button-secondary"
        type="button"
        :disabled="!notifications.unreadCount"
        @click="markAllRead"
      >
        Mark all as read
      </button>
    </div>

    <section class="panel">
      <div class="notification-filters">
        <div class="status-tabs notification-tabs" role="tablist" aria-label="Notification status">
          <button
            class="status-tab"
            :class="{ 'status-tab-active': !unreadOnly }"
            type="button"
            role="tab"
            :aria-selected="!unreadOnly"
            @click="unreadOnly = false"
          >
            All
          </button>
          <button
            class="status-tab"
            :class="{ 'status-tab-active': unreadOnly }"
            type="button"
            role="tab"
            :aria-selected="unreadOnly"
            @click="unreadOnly = true"
          >
            Unread
          </button>
        </div>
        <label class="form-field notification-category-filter">
          Category
          <select v-model="category">
            <option value="">All categories</option>
            <option value="rfq">RFQ</option>
            <option value="approval">Approval</option>
            <option value="invoice">Invoice</option>
            <option value="po">Purchase order</option>
          </select>
        </label>
      </div>

      <p v-if="loading && !items.length" class="loading-message" role="status">Loading notifications…</p>
      <div v-else-if="error" class="notification-error-state">
        <p class="form-error" role="alert">{{ error }}</p>
        <button class="button button-secondary" type="button" :disabled="loading" @click="loadPage()">
          Retry
        </button>
      </div>
      <EmptyState v-else-if="empty" message="No notifications yet" />
      <ul v-else class="notification-list">
        <li
          v-for="item in items"
          :key="item.id"
          class="notification-row"
          :class="{ 'notification-row-unread': !item.is_read }"
        >
          <button class="notification-row-content" type="button" @click="openNotification(item)">
            <span class="notification-row-title">{{ item.title }}</span>
            <span class="notification-row-message">{{ item.message }}</span>
            <span class="notification-row-meta">
              <span class="status-badge notification-category-badge" :class="`category-${item.category}`">
                {{ categoryLabels[item.category] || item.category }}
              </span>
              <time :datetime="item.created_at">{{ formatDateTime(item.created_at) }}</time>
            </span>
          </button>
          <button
            v-if="!item.is_read"
            class="notification-mark-read"
            type="button"
            :aria-label="`Mark ${item.title} as read`"
            @click="markRead(item)"
          >
            Mark as read
          </button>
          <span v-else class="notification-read-label">Read</span>
        </li>
      </ul>

      <div v-if="hasMore" class="notification-load-more">
        <button class="button button-secondary" type="button" :disabled="loading" @click="loadPage(nextPage, true)">
          {{ loading ? 'Loading…' : 'Load more' }}
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.notification-filters {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 15px;
}

.notification-tabs {
  margin: 0;
}

.notification-category-filter {
  width: min(100%, 220px);
}

.notification-category-filter select {
  min-height: 36px;
}

.notification-list {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

.notification-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 10px;
  border-bottom: 1px solid var(--border);
}

.notification-row-unread {
  background: #f8fbf8;
}

.notification-row-content {
  display: grid;
  min-width: 0;
  gap: 7px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.notification-row-title {
  font-weight: 600;
}

.notification-row-message {
  color: var(--muted);
  overflow-wrap: anywhere;
}

.notification-row-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 10px;
}

.notification-category-badge {
  background: #edf2ee;
  color: #3c5745;
}

.category-rfq {
  background: #e9f5ed;
  color: var(--green-dark);
}

.category-approval {
  background: var(--amber-soft);
  color: var(--amber);
}

.category-invoice,
.category-po {
  background: #edf1fa;
  color: #425b8c;
}

.notification-mark-read,
.notification-read-label {
  flex: 0 0 auto;
  padding: 5px;
  border: 0;
  background: transparent;
  color: var(--green-dark);
  font-size: 10px;
}

.notification-mark-read {
  cursor: pointer;
  font-weight: 600;
}

.notification-read-label {
  color: var(--muted);
}

.notification-error-state {
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 16px 0;
}

.notification-load-more {
  display: flex;
  justify-content: center;
  padding-top: 20px;
}

@media (max-width: 520px) {
  .notifications-page > .page-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .notification-filters {
    flex-direction: column;
    align-items: stretch;
  }

  .notification-category-filter {
    width: 100%;
  }

  .notification-row {
    align-items: flex-start;
  }
}
</style>
