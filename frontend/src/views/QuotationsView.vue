<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { formatDate, formatMoney } from '../utils/format'
import { getErrorMessage } from '../utils/errors'

const auth = useAuth()
const rows = ref([])
const loading = ref(true)
const error = ref('')
const isVendor = computed(() => auth.role === 'vendor')

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function loadQuotations() {
  loading.value = true
  error.value = ''
  try {
    if (isVendor.value) {
      const response = await api.get('/my-quotations/')
      rows.value = getRows(response.data)
    } else {
      const response = await api.get('/rfqs/')
      rows.value = getRows(response.data).filter((rfq) => {
        const count = rfq.quotation_count ?? rfq.quotations_count ?? rfq.quotations?.length ?? 0
        return Number(count) > 0
      })
    }
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load quotations.')
  } finally {
    loading.value = false
  }
}

function rfqFor(row) {
  return row.rfq && typeof row.rfq === 'object' ? row.rfq : row
}

function rfqId(row) {
  return row.rfq_id || rfqFor(row).id
}

function quotationStatus(row) {
  return row.display_status || row.status || 'unknown'
}

onMounted(loadQuotations)
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>{{ isVendor ? 'My Quotations' : 'Quotations' }}</h1>
        <p class="muted">{{ isVendor ? 'View and manage your submitted quotations' : 'RFQs with received quotations' }}</p>
      </div>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <section class="panel">
      <p v-if="loading" class="loading-message" role="status">Loading quotations…</p>
      <div v-else-if="rows.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>RFQ Number</th>
              <th>Title</th>
              <th>Deadline</th>
              <th>Status</th>
              <th v-if="isVendor">Grand total</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id || rfqId(row)">
              <td>{{ rfqFor(row).rfq_number || rfqFor(row).number || `RFQ-${rfqId(row)}` }}</td>
              <td>{{ rfqFor(row).title || row.rfq_title || row.title || '—' }}</td>
              <td>{{ formatDate(rfqFor(row).deadline || row.deadline) }}</td>
              <td><StatusBadge :status="String(quotationStatus(row))" /></td>
              <td v-if="isVendor">{{ formatMoney(row.grand_total ?? row.total) }}</td>
              <td>
                <RouterLink
                  v-if="isVendor"
                  class="button button-small button-secondary"
                  :to="`/rfqs/${rfqId(row)}/quote`"
                >
                  Open / Edit
                </RouterLink>
                <div v-else class="quotation-admin-actions">
                  <RouterLink class="button button-small button-secondary" :to="`/rfqs/${rfqId(row)}`">Open</RouterLink>
                  <RouterLink class="button button-small button-primary" :to="`/rfqs/${rfqId(row)}/compare`">Compare</RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :message="error ? 'Unable to display quotations.' : 'No quotations found'" />
      <button v-if="error" class="button button-secondary" type="button" @click="loadQuotations">Try again</button>
    </section>
  </section>
</template>

<style scoped>
.quotation-admin-actions {
  display: flex;
  gap: 7px;
}
</style>
