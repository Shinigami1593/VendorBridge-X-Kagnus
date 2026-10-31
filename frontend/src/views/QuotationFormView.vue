<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import { formatDate, formatMoney } from '../utils/format'
import { getErrorMessage, getFieldErrors } from '../utils/errors'

const route = useRoute()
const rfq = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const fieldErrors = ref({})
const serverTotals = ref(null)
const savedSnapshot = ref('')
const form = reactive({
  taxPercent: 18,
  paymentTerms: '',
  notes: '',
  items: [],
})

const deadlinePassed = computed(() => {
  const deadline = rfq.value?.deadline ? new Date(rfq.value.deadline).getTime() : 0
  return deadline > 0 && deadline < Date.now()
})
const subtotalPreview = computed(() => form.items.reduce(
  (sum, item) => sum + (Number(item.unitPrice) || 0) * (Number(item.quantity) || 0),
  0,
))
const gstPreview = computed(() => subtotalPreview.value * (Number(form.taxPercent) || 0) / 100)
const grandTotalPreview = computed(() => subtotalPreview.value + gstPreview.value)
const snapshot = computed(() => JSON.stringify(form))
const hasUnsavedChanges = computed(() => snapshot.value !== savedSnapshot.value)
const displayedTotals = computed(() => serverTotals.value && !hasUnsavedChanges.value
  ? serverTotals.value
  : { subtotal: subtotalPreview.value, gst: gstPreview.value, grandTotal: grandTotalPreview.value })

function totalFromServer(data) {
  return {
    subtotal: data.subtotal ?? null,
    gst: data.gst_amount ?? data.tax_amount ?? data.gst ?? null,
    grandTotal: data.grand_total ?? data.total ?? null,
  }
}

function quotationData(data) {
  const quotation = data?.quotation || data
  form.taxPercent = quotation.tax_percent ?? 18
  form.paymentTerms = quotation.payment_terms || ''
  form.notes = quotation.notes || ''
  const quoteItems = quotation.items || []
  form.items = (rfq.value?.items || []).map((rfqItem) => {
    const savedItem = quoteItems.find((item) => {
      const itemId = typeof item.rfq_item === 'object' ? item.rfq_item.id : item.rfq_item
      return String(itemId) === String(rfqItem.id)
    })
    return {
      rfqItem: rfqItem.id,
      name: rfqItem.name,
      quantity: rfqItem.quantity,
      unit: rfqItem.unit,
      unitPrice: savedItem?.unit_price ?? '',
      deliveryDays: savedItem?.delivery_days ?? '',
    }
  })
  const totalFields = ['subtotal', 'gst_amount', 'tax_amount', 'gst', 'grand_total', 'total']
  serverTotals.value = totalFields.some((key) => quotation[key] !== undefined && quotation[key] !== null)
    ? totalFromServer(quotation)
    : null
  savedSnapshot.value = JSON.stringify(form)
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/rfqs/${route.params.id}/`)
    rfq.value = response.data
    try {
      const quotationResponse = await api.get(`/rfqs/${route.params.id}/my-quotation/`)
      quotationData(quotationResponse.data)
    } catch (err) {
      if (err.response?.status !== 404) throw err
      quotationData({})
    }
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load this quotation.')
  } finally {
    loading.value = false
  }
}

function itemTotal(item) {
  return (Number(item.unitPrice) || 0) * (Number(item.quantity) || 0)
}

async function save(submit) {
  error.value = ''
  success.value = ''
  fieldErrors.value = {}
  if (submit && !form.paymentTerms.trim()) {
    fieldErrors.value.payment_terms = 'Payment terms are required to submit.'
    return
  }
  saving.value = true
  try {
    const body = {
      tax_percent: Number(form.taxPercent),
      payment_terms: form.paymentTerms.trim(),
      notes: form.notes,
      submit,
      items: form.items.map((item) => ({
        rfq_item: item.rfqItem,
        unit_price: Number(item.unitPrice),
        delivery_days: Number(item.deliveryDays),
      })),
    }
    const response = await api.put(`/rfqs/${route.params.id}/my-quotation/`, body)
    const data = response.data?.quotation || response.data
    serverTotals.value = totalFromServer(data)
    savedSnapshot.value = JSON.stringify(form)
    success.value = submit ? 'Quotation submitted successfully.' : 'Quotation draft saved.'
  } catch (err) {
    fieldErrors.value = getFieldErrors(err)
    error.value = getErrorMessage(err, 'Unable to save the quotation.')
  } finally {
    saving.value = false
  }
}

onMounted(loadPage)
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>Submit Quotations</h1>
        <p v-if="rfq" class="muted">RFQ: {{ rfq.title }} - deadline {{ formatDate(rfq.deadline) }}</p>
      </div>
    </div>

    <p v-if="loading" class="loading-message" role="status">Loading quotation…</p>
    <template v-else-if="rfq">
      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <p v-if="success" class="success-message page-alert" role="status">{{ success }}</p>
      <p v-if="deadlinePassed" class="form-error page-alert">Deadline has passed. Quotation changes are disabled.</p>

      <section class="panel quotation-summary">
        <div class="panel-heading"><h2>RFQ Summary</h2></div>
        <dl class="quotation-summary-grid">
          <div><dt>RFQ number</dt><dd>{{ rfq.rfq_number || rfq.number || `RFQ-${rfq.id}` }}</dd></div>
          <div><dt>Category</dt><dd>{{ rfq.category || '—' }}</dd></div>
          <div><dt>Deadline</dt><dd>{{ formatDate(rfq.deadline) }}</dd></div>
          <div class="quotation-summary-wide"><dt>Description</dt><dd>{{ rfq.description || 'No description provided.' }}</dd></div>
        </dl>
      </section>

      <form class="quotation-form" @submit.prevent="save(true)">
        <section class="panel">
          <div class="panel-heading"><h2>Your Quotation</h2></div>
          <p v-if="!form.items.length" class="muted">This RFQ has no line items.</p>
          <div v-else class="table-wrap">
            <table>
              <thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Total</th><th>Delivery (days)</th></tr></thead>
              <tbody>
                <tr v-for="item in form.items" :key="item.rfqItem">
                  <td>{{ item.name }}</td>
                  <td>{{ item.quantity }} {{ item.unit }}</td>
                  <td>
                    <input
                      v-model="item.unitPrice"
                      type="number"
                      min="0"
                      step="0.01"
                      aria-label="Unit price"
                      :disabled="deadlinePassed || saving"
                    >
                    <small v-if="fieldErrors.items" class="field-error">{{ fieldErrors.items }}</small>
                  </td>
                  <td>{{ formatMoney(itemTotal(item)) }}</td>
                  <td>
                    <input
                      v-model="item.deliveryDays"
                      type="number"
                      min="0"
                      step="1"
                      aria-label="Delivery days"
                      :disabled="deadlinePassed || saving"
                    >
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <div class="quotation-lower-grid">
          <section class="panel quotation-terms">
            <label class="form-field">
              <span>Tax / GST %</span>
              <input v-model="form.taxPercent" type="number" min="0" step="0.01" :disabled="deadlinePassed || saving">
              <small v-if="fieldErrors.tax_percent" class="field-error">{{ fieldErrors.tax_percent }}</small>
            </label>
            <label class="form-field">
              <span>Payment terms</span>
              <input v-model="form.paymentTerms" type="text" :disabled="deadlinePassed || saving" :aria-invalid="Boolean(fieldErrors.payment_terms)">
              <small v-if="fieldErrors.payment_terms" class="field-error">{{ fieldErrors.payment_terms }}</small>
            </label>
            <label class="form-field">
              <span>Notes</span>
              <textarea v-model="form.notes" rows="4" :disabled="deadlinePassed || saving"></textarea>
              <small v-if="fieldErrors.notes" class="field-error">{{ fieldErrors.notes }}</small>
            </label>
          </section>

          <section class="panel quotation-totals">
            <h2>Totals</h2>
            <div><span>Subtotal</span><strong>{{ displayedTotals.subtotal === null ? '—' : formatMoney(displayedTotals.subtotal) }}</strong></div>
            <div><span>GST</span><strong>{{ displayedTotals.gst === null ? '—' : formatMoney(displayedTotals.gst) }}</strong></div>
            <div class="quotation-grand-total"><span>Grand total</span><strong>{{ displayedTotals.grandTotal === null ? '—' : formatMoney(displayedTotals.grandTotal) }}</strong></div>
          </section>
        </div>

        <div class="quotation-actions">
          <button class="button button-secondary" type="button" :disabled="deadlinePassed || saving" @click="save(false)">
            {{ saving ? 'Saving…' : 'Save Draft' }}
          </button>
          <button class="button button-primary" type="submit" :disabled="deadlinePassed || saving || !form.items.length">
            {{ saving ? 'Saving…' : 'Submit Quotation' }}
          </button>
        </div>
      </form>
    </template>
    <template v-else>
      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <EmptyState message="This RFQ could not be found." />
    </template>
  </section>
</template>

<style scoped>
.quotation-summary {
  margin-bottom: 16px;
}

.quotation-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 0;
}

.quotation-summary-grid div {
  display: grid;
  gap: 5px;
}

.quotation-summary-grid dt {
  color: var(--muted);
  font-size: 10px;
}

.quotation-summary-grid dd {
  margin: 0;
  color: var(--text);
  font-size: 11px;
}

.quotation-summary-wide {
  grid-column: 1 / -1;
}

.quotation-form {
  display: grid;
  gap: 16px;
}

.quotation-form td input {
  width: 110px;
  min-height: 34px;
  padding: 7px 8px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  font-size: 11px;
}

.quotation-form td small {
  display: block;
  max-width: 150px;
  white-space: normal;
}

.quotation-lower-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(230px, 0.8fr);
  align-items: start;
  gap: 16px;
}

.quotation-terms {
  display: grid;
  gap: 15px;
}

.quotation-totals {
  display: grid;
  gap: 13px;
}

.quotation-totals h2 {
  margin: 0 0 4px;
  font-size: 14px;
}

.quotation-totals div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 11px;
}

.quotation-totals strong {
  color: var(--text);
  font-weight: 600;
}

.quotation-totals .quotation-grand-total {
  padding-top: 12px;
  border-top: 1px solid var(--border);
  color: var(--text);
  font-weight: 600;
}

.quotation-grand-total strong {
  color: var(--green-dark);
  font-size: 14px;
}

.quotation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 720px) {
  .quotation-lower-grid,
  .quotation-summary-grid {
    grid-template-columns: 1fr;
  }

  .quotation-summary-wide {
    grid-column: auto;
  }
}
</style>
