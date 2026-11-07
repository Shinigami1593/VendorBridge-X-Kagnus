<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatMoney } from '../utils/format'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const order = ref(null)
const loading = ref(true)
const generating = ref(false)
const error = ref('')
const canGenerateInvoice = computed(() => ['admin', 'officer'].includes(auth.role))
const items = computed(() => order.value?.items || order.value?.line_items || [])
const invoiceId = computed(() => order.value?.invoice_id || order.value?.invoice?.id)
const rfqId = computed(() => order.value?.rfq_id || order.value?.rfq?.id)
const approvalId = computed(() => order.value?.approval_id || order.value?.approval?.id)

function addressText(value) {
  if (typeof value === 'string') return value
  if (!value) return '—'
  return [value.address || value.street, value.city, value.state, value.postal_code || value.zip]
    .filter(Boolean)
    .join(', ') || '—'
}

async function loadOrder() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/purchase-orders/${route.params.id}/`)
    order.value = response.data
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load this purchase order.')
  } finally {
    loading.value = false
  }
}

async function generateInvoice() {
  if (!window.confirm('Generate an invoice for this purchase order?')) return
  generating.value = true
  error.value = ''
  try {
    const response = await api.post('/invoices/', { purchase_order_id: order.value.id })
    const id = response.data?.id || response.data?.invoice?.id
    if (!id) {
      error.value = 'The invoice was created, but its ID was not returned.'
      return
    }
    await router.push(`/invoices/${id}`)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to generate an invoice.')
  } finally {
    generating.value = false
  }
}

onMounted(loadOrder)
</script>

<template>
  <section class="page">
    <p v-if="loading" class="loading-message" role="status">Loading purchase order…</p>
    <template v-else-if="order">
      <div class="page-heading">
        <div>
          <h1>Purchase Order</h1>
          <p class="muted">{{ order.po_number || order.number || `PO-${order.id}` }}</p>
        </div>
        <div class="po-detail-actions">
          <RouterLink v-if="invoiceId" class="button button-primary" :to="`/invoices/${invoiceId}`">View Invoice</RouterLink>
          <button
            v-else-if="canGenerateInvoice"
            class="button button-primary"
            type="button"
            :disabled="generating"
            @click="generateInvoice"
          >
            {{ generating ? 'Generating…' : 'Generate Invoice' }}
          </button>
        </div>
      </div>

      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>

      <section class="panel po-parties">
        <div>
          <h2>Bill to</h2>
          <strong>{{ order.bill_to?.name || order.bill_to?.organization_name || order.bill_to_name || '—' }}</strong>
          <p>{{ addressText(order.bill_to) }}</p>
          <p v-if="order.bill_to?.gstin || order.bill_to_gstin">GSTIN: {{ order.bill_to?.gstin || order.bill_to_gstin }}</p>
        </div>
        <div>
          <h2>Vendor</h2>
          <strong>{{ order.vendor_name || order.vendor?.name || order.vendor?.company_name || '—' }}</strong>
          <p>{{ addressText(order.vendor?.address || order.vendor_address) }}</p>
          <p v-if="order.vendor?.gstin || order.vendor_gstin">GSTIN: {{ order.vendor?.gstin || order.vendor_gstin }}</p>
        </div>
        <div class="po-meta">
          <span>PO Number</span><strong>{{ order.po_number || order.number || `PO-${order.id}` }}</strong>
          <span>PO Date</span><strong>{{ formatDate(order.po_date || order.date || order.created_at) }}</strong>
          <span>Status</span><StatusBadge :status="String(order.status || 'unknown')" />
        </div>
      </section>

      <section class="panel">
        <div v-if="items.length" class="table-wrap">
          <table>
            <thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Total</th></tr></thead>
            <tbody>
              <tr v-for="(item, index) in items" :key="item.id || index">
                <td>{{ item.name || item.item_name || item.rfq_item?.name || '—' }}</td>
                <td>{{ item.quantity ?? item.qty ?? '—' }}</td>
                <td>{{ formatMoney(item.unit_price) }}</td>
                <td>{{ formatMoney(item.total ?? item.line_total) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr><th colspan="3">Subtotal</th><td>{{ formatMoney(order.subtotal) }}</td></tr>
              <tr><th colspan="3">Tax</th><td>{{ formatMoney(order.tax_amount ?? order.tax) }}</td></tr>
              <tr><th colspan="3">Grand total</th><td>{{ formatMoney(order.grand_total ?? order.total) }}</td></tr>
            </tfoot>
          </table>
        </div>
        <EmptyState v-else message="No purchase order items" />
      </section>

      <div class="po-detail-links">
        <RouterLink v-if="rfqId" class="text-link" :to="`/rfqs/${rfqId}`">View RFQ</RouterLink>
        <RouterLink v-if="approvalId" class="text-link" :to="`/approvals/${approvalId}`">View Approval</RouterLink>
      </div>
    </template>
    <template v-else>
      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <EmptyState message="This purchase order could not be found." />
      <button class="button button-secondary" type="button" @click="loadOrder">Try again</button>
    </template>
  </section>
</template>

<style scoped>
.po-detail-actions {
  display: flex;
  gap: 9px;
}

.po-parties {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
}

.po-parties h2 {
  margin: 0 0 12px;
  font-size: 13px;
}

.po-parties strong,
.po-parties p {
  display: block;
  margin: 0 0 6px;
  font-size: 11px;
  line-height: 1.5;
}

.po-parties p {
  color: var(--muted);
}

.po-meta {
  display: grid;
  grid-template-columns: auto 1fr;
  align-content: start;
  gap: 9px 14px;
}

.po-meta span {
  color: var(--muted);
}

.po-detail-links {
  display: flex;
  gap: 18px;
}

table tfoot th,
table tfoot td {
  border-bottom: 0;
  text-align: right;
}

table tfoot tr:last-child th,
table tfoot tr:last-child td {
  color: var(--text);
  font-weight: 700;
}

@media (max-width: 720px) {
  .po-parties {
    grid-template-columns: 1fr;
  }
}
</style>
