<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { CheckCheck, ClipboardList, FileText, ReceiptText, Store } from 'lucide-vue-next'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import { getErrorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/format'

const tabs = [
  { label: 'All', value: 'all' },
  { label: 'RFQ', value: 'rfq' },
  { label: 'Approvals', value: 'approvals' },
  { label: 'Invoices', value: 'invoices' },
  { label: 'Vendors', value: 'vendors' },
]
const tab = ref('all')
const search = ref('')
const searchValue = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const items = ref([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const hasMore = ref(false)
let searchTimer
let requestId = 0

async function loadActivity({ append = false } = {}) {
  const currentRequest = ++requestId
  const requestedPage = append ? page.value + 1 : 1
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/activity/', {
      params: {
        tab: tab.value,
        search: searchValue.value.trim(),
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined,
        page: requestedPage,
        page_size: 20,
      },
    })
    if (currentRequest !== requestId) return
    const results = response.data.results || []
    items.value = append ? [...items.value, ...results] : results
    page.value = requestedPage
    hasMore.value = Boolean(response.data.next)
  } catch (requestError) {
    if (currentRequest === requestId) {
      error.value = getErrorMessage(requestError, 'Unable to load activity.')
    }
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

function retry() {
  loadActivity({ append: page.value > 1 && hasMore.value })
}

function iconFor(category) {
  if (category === 'approval') return CheckCheck
  if (category === 'invoice' || category === 'po') return ReceiptText
  if (category === 'vendor') return Store
  if (category === 'quotation' || category === 'rfq') return FileText
  return ClipboardList
}

watch([tab, dateFrom, dateTo], () => loadActivity())
watch(search, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    searchValue.value = value
    loadActivity()
  }, 300)
})

onMounted(() => loadActivity())
onUnmounted(() => {
  clearTimeout(searchTimer)
  requestId += 1
})
</script>

<template>
  <section class="page activity-page">
    <div class="page-heading">
      <div>
        <h1>Activity &amp; Logs</h1>
        <p class="muted">Procurement audit trail</p>
      </div>
    </div>

    <section class="panel activity-panel">
      <div class="activity-tabs" role="tablist" aria-label="Filter activity">
        <button
          v-for="item in tabs"
          :key="item.value"
          class="activity-tab"
          :class="{ 'activity-tab-active': tab === item.value }"
          type="button"
          role="tab"
          :aria-selected="tab === item.value"
          @click="tab = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="activity-filters">
        <label class="activity-search">
          <span>Search activity</span>
          <input v-model="search" type="search" placeholder="Search message or actor">
        </label>
        <label class="activity-date">
          <span>From</span>
          <input v-model="dateFrom" type="date">
        </label>
        <label class="activity-date">
          <span>To</span>
          <input v-model="dateTo" type="date">
        </label>
      </div>

      <p v-if="loading && !items.length" class="loading-message" role="status">Loading activity…</p>
      <div v-else-if="error" class="activity-error">
        <p class="form-error" role="alert">{{ error }}</p>
        <button class="button button-secondary" type="button" :disabled="loading" @click="retry">Retry</button>
      </div>
      <EmptyState v-else-if="!items.length" message="No activity yet" />
      <ol v-else class="activity-list">
        <li v-for="item in items" :key="item.id" class="activity-row">
          <span class="activity-icon" aria-hidden="true">
            <component :is="iconFor(item.category)" :size="17" :stroke-width="1.8" />
          </span>
          <div class="activity-copy">
            <p class="activity-message">{{ item.message }}</p>
            <p class="activity-byline">
              by {{ item.actor_name || 'System' }}<template v-if="item.actor_role"> ({{ item.actor_role }})</template>
            </p>
          </div>
          <time class="activity-time" :datetime="item.created_at">{{ formatDateTime(item.created_at) }}</time>
        </li>
      </ol>

      <div v-if="hasMore" class="activity-load-more">
        <button class="button button-secondary" type="button" :disabled="loading" @click="loadActivity({ append: true })">
          {{ loading ? 'Loading…' : 'Load more' }}
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.activity-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 18px;
}

.activity-tab {
  min-height: 34px;
  padding: 7px 15px;
  border: 1px solid #e5eae6;
  border-radius: 999px;
  background: #fff;
  color: #647068;
  cursor: pointer;
  font-size: 11px;
}

.activity-tab-active {
  border-color: var(--green-dark);
  background: var(--green-dark);
  color: #fff;
}

.activity-filters {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) repeat(2, minmax(145px, 190px));
  gap: 12px;
  margin-bottom: 18px;
}

.activity-filters label {
  display: grid;
  gap: 6px;
  color: #3f4a42;
  font-size: 10px;
  font-weight: 600;
}

.activity-filters input {
  width: 100%;
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid #e1e7e2;
  border-radius: 9px;
  background: #fff;
  color: var(--text);
  font-weight: 400;
}

.activity-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.activity-row {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  align-items: center;
  gap: 13px;
  padding: 15px 5px;
  border-bottom: 1px solid #edf0ed;
}

.activity-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: var(--green-soft);
  color: var(--green-dark);
}

.activity-copy {
  min-width: 0;
}

.activity-message,
.activity-byline {
  margin: 0;
}

.activity-message {
  color: #303a33;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.activity-byline,
.activity-time {
  margin-top: 5px;
  color: var(--muted);
  font-size: 10px;
}

.activity-time {
  white-space: nowrap;
}

.activity-error {
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 16px 0;
}

.activity-load-more {
  display: flex;
  justify-content: center;
  padding-top: 20px;
}

@media (max-width: 700px) {
  .activity-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .activity-search {
    grid-column: 1 / -1;
  }

  .activity-row {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .activity-time {
    grid-column: 2;
    margin-top: 0;
  }
}
</style>
