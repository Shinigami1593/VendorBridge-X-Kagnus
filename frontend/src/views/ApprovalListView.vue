<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatMoney } from '../utils/format'

const router = useRouter()
const approvals = ref([])
const status = ref('')
const loading = ref(false)
const error = ref('')
const tabs = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
]

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function loadApprovals() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/approvals/', { params: { status: status.value } })
    approvals.value = getRows(response.data)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load approvals.')
  } finally {
    loading.value = false
  }
}

function openApproval(approval) {
  router.push(`/approvals/${approval.id}`)
}

function currentStep(approval) {
  return approval.current_step || approval.current_step_label || approval.step || '—'
}

watch(status, loadApprovals)
onMounted(loadApprovals)
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>Approvals</h1>
        <p class="muted">Review quotation approvals and their current status</p>
      </div>
    </div>

    <div class="status-tabs" role="tablist" aria-label="Filter approvals">
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
      <p v-if="loading" class="loading-message" role="status">Loading approvals…</p>
      <div v-else-if="approvals.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>RFQ Number</th>
              <th>RFQ Title</th>
              <th>Vendor</th>
              <th>Grand Total</th>
              <th>Current Step</th>
              <th>Status</th>
              <th>Requested Date</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="approval in approvals"
              :key="approval.id"
              class="approval-row"
              tabindex="0"
              @click="openApproval(approval)"
              @keydown.enter="openApproval(approval)"
            >
              <td>{{ approval.rfq_number || approval.rfq?.rfq_number || '—' }}</td>
              <td>{{ approval.rfq_title || approval.rfq?.title || approval.title || '—' }}</td>
              <td>{{ approval.vendor_name || approval.vendor?.name || '—' }}</td>
              <td>{{ formatMoney(approval.grand_total ?? approval.total) }}</td>
              <td>{{ currentStep(approval) }}</td>
              <td><StatusBadge :status="String(approval.status || 'pending')" /></td>
              <td>{{ formatDate(approval.requested_at || approval.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :message="error ? 'Unable to display approvals.' : 'No approvals found'" />
      <button v-if="error" class="button button-secondary" type="button" @click="loadApprovals">Try again</button>
    </section>
  </section>
</template>

<style scoped>
.approval-row {
  cursor: pointer;
}

.approval-row:focus-visible {
  outline: 2px solid var(--green-light);
  outline-offset: -2px;
}
</style>
