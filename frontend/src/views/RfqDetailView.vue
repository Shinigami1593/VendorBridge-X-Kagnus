<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { formatDate, formatMoney } from '../utils/format'
import { getErrorMessage } from '../utils/errors'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const rfq = ref(null)
const loading = ref(true)
const sending = ref(false)
const error = ref('')
const actionMessage = ref('')

const canManage = computed(() => ['admin', 'officer'].includes(auth.role))
const canCompare = computed(() => ['admin', 'officer', 'manager'].includes(auth.role))
const isVendor = computed(() => auth.role === 'vendor')
const deadlineDate = computed(() => rfq.value?.deadline ? new Date(rfq.value.deadline) : null)
const deadlinePassed = computed(() => deadlineDate.value && deadlineDate.value.getTime() < Date.now())
const deadlineNote = computed(() => {
  if (
    !deadlineDate.value
    || Number.isNaN(deadlineDate.value.getTime())
    || deadlinePassed.value
    || ['closed', 'selected'].includes(String(rfq.value?.status || '').toLowerCase())
  ) return 'Closed'
  const days = Math.max(1, Math.ceil((deadlineDate.value.getTime() - Date.now()) / 86400000))
  return `${days} days left`
})
const canEdit = computed(() => canManage.value && ['draft', 'open'].includes(rfq.value?.status))
const quotationAction = computed(() => {
  const quoteStatus = String(rfq.value?.my_quotation_status || '').toLowerCase()
  return rfq.value?.my_quotation || (quoteStatus && !['not submitted', 'none'].includes(quoteStatus))
    ? 'Edit Quotation'
    : 'Submit Quotation'
})
const vendors = computed(() => (rfq.value?.vendors || []).map((vendor) => {
  if (typeof vendor === 'object') return vendor.name || vendor.vendor_name || vendor.company_name || `Vendor ${vendor.id}`
  return `Vendor ${vendor}`
}))
const quotations = computed(() => rfq.value?.quotations || rfq.value?.received_quotations || [])

async function loadRfq() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/rfqs/${route.params.id}/`)
    rfq.value = response.data
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load this RFQ.')
  } finally {
    loading.value = false
  }
}

async function publishRfq() {
  sending.value = true
  error.value = ''
  actionMessage.value = ''
  try {
    await api.post(`/rfqs/${route.params.id}/publish/`)
    actionMessage.value = 'RFQ sent to vendors.'
    await loadRfq()
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to send the RFQ to vendors.')
  } finally {
    sending.value = false
  }
}

function openQuote() {
  router.push(`/rfqs/${route.params.id}/quote`)
}

function attachmentUrl(attachment) {
  return attachment.url || attachment.file_url || attachment.download_url || '#'
}

onMounted(loadRfq)
</script>

<template>
  <section class="page">
    <p v-if="loading" class="loading-message" role="status">Loading RFQ…</p>
    <template v-else-if="rfq">
      <div class="page-heading rfq-detail-heading">
        <div>
          <p class="muted rfq-number">{{ rfq.rfq_number || rfq.number || `RFQ-${rfq.id}` }}</p>
          <h1>{{ rfq.title }}</h1>
          <div class="rfq-detail-status">
            <StatusBadge :status="String(rfq.display_status || rfq.status || 'unknown')" />
            <span class="muted">Deadline {{ formatDate(rfq.deadline) }} · {{ deadlineNote }}</span>
          </div>
        </div>
        <div class="rfq-detail-actions">
          <RouterLink v-if="canEdit" class="button button-secondary" :to="`/rfqs/${rfq.id}/edit`">Edit</RouterLink>
          <button v-if="canManage && rfq.status === 'draft'" class="button button-primary" type="button" :disabled="sending" @click="publishRfq">
            {{ sending ? 'Sending…' : 'Send to Vendors' }}
          </button>
          <RouterLink v-if="canCompare" class="button button-secondary" :to="`/rfqs/${rfq.id}/compare`">Compare Quotations</RouterLink>
          <button v-if="isVendor" class="button button-primary" type="button" :disabled="deadlinePassed" @click="openQuote">
            {{ quotationAction }}
          </button>
        </div>
      </div>

      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <p v-if="actionMessage" class="success-message page-alert" role="status">{{ actionMessage }}</p>
      <p v-if="isVendor && deadlinePassed" class="form-error page-alert">The deadline has passed. Quotations can no longer be submitted.</p>

      <div class="rfq-detail-grid">
        <section class="panel">
          <div class="panel-heading"><h2>RFQ Summary</h2></div>
          <dl class="rfq-detail-facts">
            <div><dt>Category</dt><dd>{{ rfq.category || '—' }}</dd></div>
            <div><dt>Deadline</dt><dd>{{ formatDate(rfq.deadline) }}</dd></div>
          </dl>
          <h3>Description</h3>
          <p class="rfq-description">{{ rfq.description || 'No description provided.' }}</p>
        </section>

        <section class="panel">
          <div class="panel-heading"><h2>Assigned Vendors</h2></div>
          <ul v-if="vendors.length" class="rfq-vendor-list">
            <li v-for="(vendor, index) in vendors" :key="`${vendor}-${index}`">{{ vendor }}</li>
          </ul>
          <EmptyState v-else message="No vendors assigned" />
        </section>
      </div>

      <section class="panel rfq-detail-section">
        <div class="panel-heading"><h2>Line items</h2></div>
        <div v-if="rfq.items?.length" class="table-wrap">
          <table>
            <thead><tr><th>Item</th><th>Quantity</th><th>Unit</th></tr></thead>
            <tbody>
              <tr v-for="item in rfq.items" :key="item.id">
                <td>{{ item.name }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ item.unit || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else message="No line items" />
      </section>

      <section class="panel rfq-detail-section">
        <div class="panel-heading"><h2>Attachments</h2></div>
        <ul v-if="rfq.attachments?.length" class="rfq-attachment-links">
          <li v-for="attachment in rfq.attachments" :key="attachment.id">
            <a :href="attachmentUrl(attachment)" target="_blank" rel="noopener noreferrer">
              {{ attachment.name || attachment.file_name || attachment.filename || 'Download attachment' }}
            </a>
          </li>
        </ul>
        <EmptyState v-else message="No attachments" />
      </section>

      <section v-if="!isVendor" class="panel rfq-detail-section">
        <div class="panel-heading"><h2>Received Quotations</h2></div>
        <div v-if="quotations.length" class="table-wrap">
          <table>
            <thead><tr><th>Vendor</th><th>Total</th><th>Delivery days</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="quotation in quotations" :key="quotation.id">
                <td>{{ quotation.vendor_name || quotation.vendor?.name || quotation.vendor || '—' }}</td>
                <td>{{ formatMoney(quotation.grand_total ?? quotation.total) }}</td>
                <td>{{ quotation.delivery_days ?? '—' }}</td>
                <td><StatusBadge :status="String(quotation.display_status || quotation.status || 'unknown')" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else message="No quotations received yet" />
      </section>
    </template>
    <template v-else>
      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <EmptyState message="This RFQ could not be found." />
      <button class="button button-secondary" type="button" @click="loadRfq">Try again</button>
    </template>
  </section>
</template>

<style scoped>
.rfq-number {
  margin: 0 0 5px;
  font-size: 11px;
}

.rfq-detail-heading {
  align-items: center;
}

.rfq-detail-status,
.rfq-detail-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 12px;
}

.rfq-detail-actions {
  justify-content: flex-end;
  margin-top: 0;
}

.rfq-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.rfq-detail-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 28px;
  margin: 0 0 17px;
}

.rfq-detail-facts div {
  display: grid;
  gap: 5px;
}

.rfq-detail-facts dt {
  color: var(--muted);
  font-size: 10px;
}

.rfq-detail-facts dd {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
}

.panel h3 {
  margin: 0 0 8px;
  font-size: 12px;
}

.rfq-description {
  margin: 0;
  color: #4b554e;
  line-height: 1.6;
  white-space: pre-wrap;
}

.rfq-vendor-list,
.rfq-attachment-links {
  display: grid;
  gap: 9px;
  margin: 0;
  padding-left: 18px;
  color: #4b554e;
  font-size: 11px;
}

.rfq-detail-section {
  margin-top: 16px;
}

@media (max-width: 720px) {
  .rfq-detail-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .rfq-detail-actions {
    justify-content: flex-start;
  }

  .rfq-detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
