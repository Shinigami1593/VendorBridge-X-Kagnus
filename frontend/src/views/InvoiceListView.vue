<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatMoney } from '../utils/format'

const router = useRouter()
const invoices = ref([])
const search = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
const tabs = [
  { label: 'All', value: '' },
  { label: 'Pending Payment', value: 'pending_payment' },
  { label: 'Paid', value: 'paid' },
]
let searchTimer

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function loadInvoices() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/invoices/', {
      params: { status: status.value, search: search.value.trim() },
    })
    invoices.value = getRows(response.data)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load invoices.')
  } finally {
    loading.value = false
  }
}

function openInvoice(invoice) {
  router.push(`/invoices/${invoice.id}`)
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadInvoices, 300)
})
watch(status, loadInvoices)
onMounted(loadInvoices)
onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>Invoices</h1>
        <p class="muted">Track invoice payment status and due dates</p>
      </div>
    </div>

    <div class="panel invoice-search-panel">
      <label class="search-field">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input v-model="search" type="search" placeholder="Search invoices..." aria-label="Search invoices">
      </label>
    </div>
    <div class="status-tabs" role="tablist" aria-label="Filter invoices">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="status-tab"
        :class="{ 'status-tab-active': status === tab.value }"
        type="button"
        role="tab"
        :aria-selected="status === tab.value"
        @click="status = tab.value"
      >
        {{ tab.label }}
      </button>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <section class="panel">
      <p v-if="loading" class="loading-message" role="status">Loading invoices…</p>
      <div v-else-if="invoices.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Invoice Number</th>
              <th>PO Number</th>
              <th>Vendor</th>
              <th>Grand Total</th>
              <th>Due Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="invoice in invoices"
              :key="invoice.id"
              class="invoice-clickable-row"
              tabindex="0"
              @click="openInvoice(invoice)"
              @keydown.enter="openInvoice(invoice)"
            >
              <td>{{ invoice.invoice_number || invoice.number || `INV-${invoice.id}` }}</td>
              <td>{{ invoice.po_number || invoice.purchase_order?.po_number || '—' }}</td>
              <td>{{ invoice.vendor_name || invoice.vendor?.name || '—' }}</td>
              <td>{{ formatMoney(invoice.grand_total ?? invoice.total) }}</td>
              <td>{{ formatDate(invoice.due_date) }}</td>
              <td><StatusBadge :status="String(invoice.status || 'unknown')" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :message="error ? 'Unable to display invoices.' : 'No invoices found'" />
      <button v-if="error" class="button button-secondary" type="button" @click="loadInvoices">Try again</button>
    </section>
  </section>
</template>

<style scoped>
.invoice-search-panel {
  padding: 11px;
  margin-bottom: 12px;
}

.invoice-search-panel .search-field {
  border-color: transparent;
  background: #f7f8f7;
}

.invoice-clickable-row {
  cursor: pointer;
}

.invoice-clickable-row:focus-visible {
  outline: 2px solid var(--green-light);
  outline-offset: -2px;
}

</style>
