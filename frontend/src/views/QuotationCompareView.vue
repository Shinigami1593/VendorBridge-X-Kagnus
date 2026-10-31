<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { formatMoney } from '../utils/format'
import { getErrorMessage } from '../utils/errors'

const auth = useAuth()
const route = useRoute()
const rfq = ref(null)
const quotations = ref([])
const loading = ref(true)
const selectingId = ref(null)
const error = ref('')
const success = ref('')
const sort = ref('price')
const maxDelivery = ref('')
const minRating = ref('')
let filterTimer

const canSelect = computed(() => ['admin', 'officer'].includes(auth.role))
const selectedId = computed(() => rfq.value?.selected_quotation_id || rfq.value?.selected_quotation?.id || rfq.value?.selected_quotation || null)

function getRows(data) {
  if (Array.isArray(data)) return data
  return data?.quotations || data?.vendors || data?.results || []
}

function isSelected(quotation) {
  return quotation.is_selected || quotation.selected || String(selectedId.value) === String(quotation.id)
}

function vendorName(quotation) {
  return quotation.vendor_name || quotation.vendor?.name || quotation.vendor?.company_name || quotation.vendor || 'Vendor'
}

function ratingText(quotation) {
  const value = quotation.vendor_rating ?? quotation.rating ?? quotation.vendor?.rating
  if (value === undefined || value === null || value === '') return 'No rating'
  return String(value).includes('/') ? String(value) : `${value}/5`
}

function itemRows(quotation) {
  return quotation.items || quotation.line_items || quotation.breakdown || []
}

async function loadComparison() {
  loading.value = true
  error.value = ''
  try {
    const [rfqResponse, comparisonResponse] = await Promise.all([
      api.get(`/rfqs/${route.params.id}/`),
      api.get(`/rfqs/${route.params.id}/comparison/`, {
        params: {
          sort: sort.value,
          max_delivery: maxDelivery.value || undefined,
          min_rating: minRating.value || undefined,
        },
      }),
    ])
    rfq.value = rfqResponse.data
    quotations.value = getRows(comparisonResponse.data)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load the quotation comparison.')
  } finally {
    loading.value = false
  }
}

function scheduleLoad() {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(loadComparison, 250)
}

async function selectQuotation(quotation) {
  if (!canSelect.value || isSelected(quotation)) return
  if (!window.confirm(`Select the quotation from ${vendorName(quotation)}?`)) return
  selectingId.value = quotation.id
  error.value = ''
  success.value = ''
  try {
    await api.post(`/rfqs/${route.params.id}/select-quotation/`, { quotation_id: quotation.id })
    success.value = 'Quotation selected.'
    await loadComparison()
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to select this quotation.')
  } finally {
    selectingId.value = null
  }
}

watch([sort, maxDelivery, minRating], scheduleLoad)
onMounted(loadComparison)
onUnmounted(() => clearTimeout(filterTimer))
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>Quotation Comparison</h1>
        <p v-if="rfq" class="muted">RFQ: {{ rfq.title }} - {{ quotations.length }} quotations received</p>
      </div>
    </div>

    <div class="panel comparison-controls">
      <label class="form-field">
        <span>Sort by</span>
        <select v-model="sort">
          <option value="price">Price</option>
          <option value="delivery">Delivery</option>
          <option value="rating">Rating</option>
        </select>
      </label>
      <label class="form-field">
        <span>Max delivery days</span>
        <input v-model="maxDelivery" type="number" min="0">
      </label>
      <label class="form-field">
        <span>Min rating</span>
        <input v-model="minRating" type="number" min="0" max="5" step="0.1">
      </label>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <p v-if="success" class="success-message page-alert" role="status">{{ success }}</p>
    <p v-if="loading" class="loading-message" role="status">Loading comparison…</p>
    <section v-else-if="quotations.length" class="panel quotation-comparison-panel">
      <div class="table-wrap">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>Criteria</th>
              <th
                v-for="quotation in quotations"
                :key="quotation.id"
                :class="{ 'comparison-lowest': quotation.is_lowest }"
              >
                {{ vendorName(quotation) }}
                <span v-if="quotation.is_lowest" class="lowest-label">(Lowest)</span>
                <StatusBadge v-if="isSelected(quotation)" status="Selected" />
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>Grand total</th>
              <td v-for="quotation in quotations" :key="`total-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                {{ formatMoney(quotation.grand_total ?? quotation.total) }}
              </td>
            </tr>
            <tr>
              <th>GST %</th>
              <td v-for="quotation in quotations" :key="`gst-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                {{ quotation.tax_percent ?? quotation.gst_percent ?? '—' }}%
              </td>
            </tr>
            <tr>
              <th>Delivery (days)</th>
              <td v-for="quotation in quotations" :key="`delivery-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                {{ quotation.delivery_days ?? '—' }}
              </td>
            </tr>
            <tr>
              <th>Vendor rating</th>
              <td v-for="quotation in quotations" :key="`rating-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                {{ ratingText(quotation) }}
              </td>
            </tr>
            <tr>
              <th>Payment terms</th>
              <td v-for="quotation in quotations" :key="`terms-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                {{ quotation.payment_terms || '—' }}
              </td>
            </tr>
            <tr>
              <th>Line item breakdown</th>
              <td v-for="quotation in quotations" :key="`items-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                <details>
                  <summary>View items</summary>
                  <div v-if="itemRows(quotation).length" class="table-wrap comparison-breakdown">
                    <table>
                      <thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Total</th></tr></thead>
                      <tbody>
                        <tr v-for="(item, index) in itemRows(quotation)" :key="item.id || index">
                          <td>{{ item.name || item.rfq_item?.name || '—' }}</td>
                          <td>{{ item.quantity ?? item.rfq_item?.quantity ?? '—' }}</td>
                          <td>{{ formatMoney(item.unit_price) }}</td>
                          <td>{{ formatMoney(item.total ?? item.line_total) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <span v-else class="muted">No item details</span>
                </details>
              </td>
            </tr>
            <tr v-if="canSelect">
              <th>Decision</th>
              <td v-for="quotation in quotations" :key="`select-${quotation.id}`" :class="{ 'comparison-lowest': quotation.is_lowest }">
                <StatusBadge v-if="isSelected(quotation)" status="Selected" />
                <button
                  v-else
                  class="button button-small button-secondary"
                  type="button"
                  :disabled="selectingId !== null"
                  @click="selectQuotation(quotation)"
                >
                  {{ selectingId === quotation.id ? 'Selecting…' : 'Select' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="comparison-note">Green = lowest price among complete quotations.</p>
    </section>
    <EmptyState v-else-if="!loading" :message="error ? 'Unable to display quotations.' : 'No quotations received yet'" />
  </section>
</template>

<style scoped>
.comparison-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.comparison-table th,
.comparison-table td {
  vertical-align: top;
}

.comparison-table thead th:not(:first-child) {
  min-width: 180px;
  white-space: normal;
}

.comparison-table tbody th {
  min-width: 150px;
}

.comparison-lowest {
  background: #e9f5ed;
}

.lowest-label {
  display: block;
  margin-top: 5px;
  color: var(--green-dark);
  font-size: 10px;
  font-weight: 600;
}

.comparison-breakdown {
  min-width: 350px;
  margin-top: 8px;
  background: white;
}

.comparison-breakdown th,
.comparison-breakdown td {
  padding: 7px;
}

.comparison-note {
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 10px;
}

@media (max-width: 650px) {
  .comparison-controls {
    grid-template-columns: 1fr;
  }
}
</style>
