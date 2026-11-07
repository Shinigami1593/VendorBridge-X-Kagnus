<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatMoney } from '../utils/format'

const router = useRouter()
const orders = ref([])
const search = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
let searchTimer

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function loadOrders() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/purchase-orders/', {
      params: { status: status.value, search: search.value.trim() },
    })
    orders.value = getRows(response.data)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load purchase orders.')
  } finally {
    loading.value = false
  }
}

function openOrder(order) {
  router.push(`/purchase-orders/${order.id}`)
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadOrders, 300)
})
watch(status, loadOrders)
onMounted(loadOrders)
onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>Purchase orders</h1>
        <p class="muted">View issued and invoiced purchase orders</p>
      </div>
    </div>

    <div class="panel vendor-search-panel">
      <label class="search-field">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input v-model="search" type="search" placeholder="Search purchase orders..." aria-label="Search purchase orders">
      </label>
      <label class="form-field po-status-filter">
        <span>Status</span>
        <select v-model="status" aria-label="Filter purchase orders by status">
          <option value="">All statuses</option>
          <option value="issued">Issued</option>
          <option value="invoiced">Invoiced</option>
        </select>
      </label>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <section class="panel">
      <p v-if="loading" class="loading-message" role="status">Loading purchase orders…</p>
      <div v-else-if="orders.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>PO Number</th>
              <th>RFQ Number</th>
              <th>Vendor</th>
              <th>Grand Total</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="order in orders"
              :key="order.id"
              class="po-clickable-row"
              tabindex="0"
              @click="openOrder(order)"
              @keydown.enter="openOrder(order)"
            >
              <td>{{ order.po_number || order.number || `PO-${order.id}` }}</td>
              <td>{{ order.rfq_number || order.rfq?.rfq_number || '—' }}</td>
              <td>{{ order.vendor_name || order.vendor?.name || '—' }}</td>
              <td>{{ formatMoney(order.grand_total ?? order.total) }}</td>
              <td><StatusBadge :status="String(order.status || 'unknown')" /></td>
              <td>{{ formatDate(order.po_date || order.created_at || order.date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :message="error ? 'Unable to display purchase orders.' : 'No purchase orders found'" />
      <button v-if="error" class="button button-secondary" type="button" @click="loadOrders">Try again</button>
    </section>
  </section>
</template>

<style scoped>
.po-status-filter {
  width: min(190px, 35%);
}

.po-status-filter select {
  min-height: 45px;
}

.po-clickable-row {
  cursor: pointer;
}

.po-clickable-row:focus-visible {
  outline: 2px solid var(--green-light);
  outline-offset: -2px;
}

@media (max-width: 600px) {
  .vendor-search-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .po-status-filter {
    width: 100%;
  }
}
</style>
