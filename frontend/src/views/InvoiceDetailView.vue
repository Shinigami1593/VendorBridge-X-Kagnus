<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatDateTime, formatMoney } from '../utils/format'

const auth = useAuth()
const route = useRoute()
const invoice = ref(null)
const loading = ref(true)
const pdfLoading = ref(false)
const paying = ref(false)
const emailSending = ref(false)
const emailModal = ref(false)
const emailAddress = ref('')
const error = ref('')
const emailError = ref('')
const success = ref('')

const canManage = computed(() => ['admin', 'officer'].includes(auth.role))
const status = computed(() => String(invoice.value?.status || '').toLowerCase())
const isPaid = computed(() => status.value === 'paid')
const items = computed(() => invoice.value?.items || invoice.value?.line_items || [])
const vendor = computed(() => invoice.value?.vendor || invoice.value?.purchase_order?.vendor || {})
const purchaseOrder = computed(() => invoice.value?.purchase_order || {})
const invoiceNumber = computed(() => invoice.value?.invoice_number || invoice.value?.number || `INV-${invoice.value?.id}`)
const emailHistory = computed(() => invoice.value?.email_history || invoice.value?.email_logs || [])
const vendorEmail = computed(() => (
  invoice.value?.vendor_email
  || vendor.value.contact_email
  || vendor.value.email
  || vendor.value.contact?.email
  || ''
))

function statusLabel(value) {
  if (String(value).toLowerCase() === 'pending_payment') return 'Pending Payment'
  if (String(value).toLowerCase() === 'paid') return 'Paid'
  return value || 'unknown'
}

function addressText(value) {
  if (typeof value === 'string') return value
  if (!value) return '—'
  return [value.address || value.street, value.city, value.state, value.postal_code || value.zip]
    .filter(Boolean)
    .join(', ') || '—'
}

async function loadInvoice() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/invoices/${route.params.id}/`)
    invoice.value = response.data
    if (!emailAddress.value) emailAddress.value = vendorEmail.value
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load this invoice.')
  } finally {
    loading.value = false
  }
}

async function downloadPdf() {
  pdfLoading.value = true
  error.value = ''
  try {
    const response = await api.get(`/invoices/${route.params.id}/pdf/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${invoiceNumber.value}.pdf`
    document.body.append(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (err) {
    const responseData = err.response?.data
    let message = getErrorMessage(err, 'Unable to download the invoice PDF.')
    if (responseData instanceof Blob) {
      const text = await responseData.text()
      try {
        const data = JSON.parse(text)
        message = data.error || data.detail || message
      } catch {
        if (text) message = text
      }
    }
    error.value = message
  } finally {
    pdfLoading.value = false
  }
}

function printInvoice() {
  window.print()
}

async function markPaid() {
  if (!window.confirm('Mark this invoice as paid?')) return
  paying.value = true
  error.value = ''
  success.value = ''
  try {
    await api.post(`/invoices/${route.params.id}/mark-paid/`)
    success.value = 'Invoice marked as paid.'
    await loadInvoice()
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to mark this invoice as paid.')
  } finally {
    paying.value = false
  }
}

function openEmailModal() {
  emailError.value = ''
  success.value = ''
  emailAddress.value = vendorEmail.value
  emailModal.value = true
}

async function sendEmail() {
  const address = emailAddress.value.trim()
  if (!address || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) {
    emailError.value = 'Enter a valid email address.'
    return
  }

  emailSending.value = true
  emailError.value = ''
  error.value = ''
  success.value = ''
  try {
    await api.post(`/invoices/${route.params.id}/send-email/`, { to_email: address })
    success.value = `Invoice sent to ${address}`
    emailModal.value = false
    await loadInvoice()
  } catch (err) {
    emailError.value = getErrorMessage(err, 'Unable to send the invoice email.')
    try {
      const response = await api.get(`/invoices/${route.params.id}/`)
      invoice.value = response.data
    } catch (refreshError) {
      error.value = getErrorMessage(refreshError, 'Unable to refresh invoice email history.')
    }
  } finally {
    emailSending.value = false
  }
}

onMounted(loadInvoice)
</script>

<template>
  <section class="page invoice-detail-page">
    <p v-if="loading" class="loading-message" role="status">Loading invoice…</p>
    <template v-else-if="invoice">
      <div class="page-heading invoice-page-heading">
        <div>
          <h1>Purchase Order &amp; Invoice</h1>
          <p class="muted">{{ invoiceNumber }}</p>
        </div>
        <div class="invoice-actions">
          <button class="button button-secondary" type="button" :disabled="pdfLoading" @click="downloadPdf">
            {{ pdfLoading ? 'Downloading…' : 'Download PDF' }}
          </button>
          <button class="button button-secondary" type="button" @click="printInvoice">Print</button>
          <button v-if="canManage" class="button button-secondary" type="button" @click="openEmailModal">Email invoice</button>
        </div>
      </div>

      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <p v-if="success" class="success-message page-alert" role="status">{{ success }}</p>

      <section class="panel invoice-parties">
        <div>
          <h2>Bill to</h2>
          <strong>{{ invoice.bill_to?.name || invoice.bill_to?.organization_name || invoice.bill_to_name || '—' }}</strong>
          <p>{{ addressText(invoice.bill_to) }}</p>
          <p>GSTIN: {{ invoice.bill_to?.gstin || invoice.bill_to_gstin || '—' }}</p>
        </div>
        <div>
          <h2>Vendor</h2>
          <strong>{{ vendor.name || vendor.company_name || invoice.vendor_name || '—' }}</strong>
          <p>{{ addressText(vendor.address || invoice.vendor_address) }}</p>
          <p>GSTIN: {{ vendor.gstin || invoice.vendor_gstin || '—' }}</p>
        </div>
        <div class="invoice-meta">
          <span>PO Number</span><strong>{{ purchaseOrder.po_number || invoice.po_number || '—' }}</strong>
          <span>PO Date</span><strong>{{ formatDate(purchaseOrder.po_date || invoice.po_date) }}</strong>
          <span>Invoice Date</span><strong>{{ formatDate(invoice.invoice_date || invoice.date) }}</strong>
          <span>Due Date</span><strong>{{ formatDate(invoice.due_date) }}</strong>
        </div>
      </section>

      <section class="panel invoice-items">
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
              <tr><th colspan="3">Subtotal</th><td>{{ formatMoney(invoice.subtotal) }}</td></tr>
              <tr>
                <th colspan="3">CGST ({{ invoice.cgst_percent ?? invoice.cgst_rate ?? '—' }}%)</th>
                <td>{{ formatMoney(invoice.cgst_amount ?? invoice.cgst) }}</td>
              </tr>
              <tr>
                <th colspan="3">SGST ({{ invoice.sgst_percent ?? invoice.sgst_rate ?? '—' }}%)</th>
                <td>{{ formatMoney(invoice.sgst_amount ?? invoice.sgst) }}</td>
              </tr>
              <tr><th colspan="3">Grand total</th><td>{{ formatMoney(invoice.grand_total ?? invoice.total) }}</td></tr>
            </tfoot>
          </table>
        </div>
        <EmptyState v-else message="No invoice items" />
      </section>

      <div class="invoice-status-line">
        <span>Status:</span>
        <StatusBadge :status="statusLabel(invoice.status)" :class="{ 'invoice-paid': isPaid, 'invoice-pending': !isPaid }" />
        <button
          v-if="canManage && status === 'pending_payment'"
          class="text-link invoice-paid-action"
          type="button"
          :disabled="paying"
          @click="markPaid"
        >
          {{ paying ? 'Updating…' : 'Mark as Paid' }}
        </button>
      </div>

      <section class="panel invoice-email-history">
        <div class="panel-heading"><h2>Email history</h2></div>
        <div v-if="emailHistory.length" class="table-wrap">
          <table>
            <thead><tr><th>To</th><th>Status</th><th>Time</th><th>Error</th></tr></thead>
            <tbody>
              <tr v-for="(entry, index) in emailHistory" :key="entry.id || index">
                <td>{{ entry.to || entry.to_email || '—' }}</td>
                <td>{{ entry.status || '—' }}</td>
                <td>{{ formatDateTime(entry.sent_at || entry.created_at || entry.timestamp) }}</td>
                <td>{{ entry.error || entry.error_message || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else message="No invoice emails sent yet" />
      </section>
    </template>
    <template v-else>
      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <EmptyState message="This invoice could not be found." />
      <button class="button button-secondary" type="button" @click="loadInvoice">Try again</button>
    </template>

    <BaseModal v-if="emailModal" title="Email invoice" @close="emailModal = false">
      <form class="form-stack invoice-email-form" @submit.prevent="sendEmail">
        <label class="form-field">
          <span>Email address</span>
          <input v-model="emailAddress" type="email" required autocomplete="email" :disabled="emailSending">
        </label>
        <p v-if="emailError" class="form-error" role="alert">{{ emailError }}</p>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" :disabled="emailSending" @click="emailModal = false">Cancel</button>
          <button class="button button-primary" type="submit" :disabled="emailSending">
            {{ emailSending ? 'Sending…' : 'Send invoice' }}
          </button>
        </div>
      </form>
    </BaseModal>
  </section>
</template>

<style scoped>
.invoice-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.invoice-parties {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
}

.invoice-parties h2 {
  margin: 0 0 12px;
  font-size: 13px;
}

.invoice-parties strong,
.invoice-parties p {
  display: block;
  margin: 0 0 6px;
  font-size: 11px;
  line-height: 1.5;
}

.invoice-parties p {
  color: var(--muted);
}

.invoice-meta {
  display: grid;
  grid-template-columns: auto 1fr;
  align-content: start;
  gap: 9px 14px;
}

.invoice-meta span {
  color: var(--muted);
}

.invoice-status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 18px;
}

.invoice-pending {
  background: var(--amber-soft);
  color: var(--amber);
}

.invoice-paid {
  background: var(--green-soft);
  color: var(--green-dark);
}

.invoice-paid-action {
  border: 0;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
}

.invoice-paid-action:disabled {
  opacity: 0.6;
}

.invoice-email-form {
  gap: 14px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
}

.invoice-items tfoot th,
.invoice-items tfoot td {
  border-bottom: 0;
  text-align: right;
}

.invoice-items tfoot tr:last-child th,
.invoice-items tfoot tr:last-child td {
  color: var(--text);
  font-weight: 700;
}

@media (max-width: 720px) {
  .invoice-parties {
    grid-template-columns: 1fr;
  }

  .invoice-page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .invoice-actions {
    justify-content: flex-start;
  }
}

@media print {
  :global(body),
  :global(#app),
  :global(.app-shell),
  :global(.app-body),
  :global(.page-content) {
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    background: #fff !important;
    color: #000 !important;
  }

  :global(.sidebar),
  :global(.topbar),
  .invoice-actions,
  .invoice-email-history,
  .invoice-paid-action {
    display: none !important;
  }

  .invoice-detail-page {
    width: 100% !important;
    color: #000 !important;
  }

  .invoice-detail-page :deep(.panel) {
    border: 1px solid #bbb !important;
    border-radius: 0 !important;
    background: #fff !important;
    box-shadow: none !important;
    color: #000 !important;
    break-inside: avoid;
  }

  .invoice-detail-page :deep(*) {
    color: #000 !important;
  }

  .invoice-detail-page :deep(.status-badge) {
    border: 1px solid #777;
    background: #fff !important;
  }
}
</style>
