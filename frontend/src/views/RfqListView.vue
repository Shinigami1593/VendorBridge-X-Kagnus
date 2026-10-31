<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { formatDate } from '../utils/format'
import { getErrorMessage } from '../utils/errors'

const auth = useAuth()
const router = useRouter()
const rfqs = ref([])
const search = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
let searchTimer

const canCreate = ['admin', 'officer'].includes(auth.role)
const isVendor = auth.role === 'vendor'

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function loadRfqs() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/rfqs/', {
      params: { search: search.value.trim(), status: status.value },
    })
    rfqs.value = getRows(response.data)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load RFQs.')
  } finally {
    loading.value = false
  }
}

function openRfq(rfq) {
  router.push(`/rfqs/${rfq.id}`)
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadRfqs, 300)
})
watch(status, loadRfqs)
onMounted(loadRfqs)
onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>RFQ's</h1>
        <p class="muted">Review and manage requests for quotation</p>
      </div>
      <RouterLink v-if="canCreate" class="button button-primary rfq-new-button" to="/rfqs/new">+ New RFQ</RouterLink>
    </div>

    <div class="panel vendor-search-panel">
      <label class="search-field">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input v-model="search" type="search" placeholder="Search RFQs..." aria-label="Search RFQs">
      </label>
      <label class="form-field rfq-status-filter">
        <span>Status</span>
        <select v-model="status" aria-label="Filter RFQs by status">
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="selected">Selected</option>
        </select>
      </label>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <div class="panel vendor-table-panel">
      <p v-if="loading" class="loading-message" role="status">Loading RFQs…</p>
      <div v-else-if="rfqs.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>RFQ Number</th>
              <th>Title</th>
              <th>Category</th>
              <th>Deadline</th>
              <th>Status</th>
              <th>Quotation Count</th>
              <th v-if="isVendor">My Quotation</th>
              <th v-if="isVendor">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="rfq in rfqs"
              :key="rfq.id"
              class="rfq-clickable-row"
              tabindex="0"
              @click="openRfq(rfq)"
              @keydown.enter="openRfq(rfq)"
            >
              <td>{{ rfq.rfq_number || rfq.number || `RFQ-${rfq.id}` }}</td>
              <td>{{ rfq.title || '—' }}</td>
              <td>{{ rfq.category || '—' }}</td>
              <td>{{ formatDate(rfq.deadline) }}</td>
              <td><StatusBadge :status="String(rfq.display_status || 'unknown')" /></td>
              <td>{{ rfq.quotation_count ?? rfq.quotations_count ?? 0 }}</td>
              <td v-if="isVendor">{{ rfq.my_quotation_status || 'Not submitted' }}</td>
              <td v-if="isVendor">
                <RouterLink
                  class="button button-small button-secondary"
                  :to="`/rfqs/${rfq.id}/quote`"
                  @click.stop
                >
                  Submit Quotation
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :message="error ? 'Unable to display RFQs.' : 'No RFQs found'" />
      <button v-if="error" class="button button-secondary" type="button" @click="loadRfqs">Try again</button>
    </div>
  </section>
</template>

<style scoped>
.vendor-search-panel {
  display: flex;
  align-items: flex-end;
  gap: 14px;
}

.vendor-search-panel .search-field {
  flex: 1;
}

.rfq-status-filter select {
  min-height: 45px;
}

.rfq-status-filter {
  width: min(190px, 35%);
}

.rfq-new-button {
  min-height: 44px;
  padding: 11px 21px;
  font-size: 13px;
}

.rfq-clickable-row {
  cursor: pointer;
}

.rfq-clickable-row:focus-visible {
  outline: 2px solid var(--green-light);
  outline-offset: -2px;
}

@media (max-width: 600px) {
  .vendor-search-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .rfq-status-filter {
    width: 100%;
  }
}
</style>
