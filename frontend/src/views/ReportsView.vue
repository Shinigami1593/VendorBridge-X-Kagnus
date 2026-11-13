<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import { getErrorMessage } from '../utils/errors'
import { formatCompactMoney, formatMoney } from '../utils/format'

const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const data = ref(null)
const loading = ref(false)
const error = ref('')
const exportError = ref('')
const exporting = ref('')
const exportMenuOpen = ref(false)
const exportMenu = ref(null)
const exportButton = ref(null)
const sortBy = ref('vendor')
const sortDirection = ref(1)
let requestId = 0

const cards = computed(() => data.value?.cards || {})
const stats = computed(() => data.value?.stats || {})
const spendByCategory = computed(() => data.value?.spend_by_category || [])
const topVendors = computed(() => data.value?.top_vendors || [])
const monthlyTrend = computed(() => data.value?.monthly_trend || [])
const vendorPerformance = computed(() => {
  const rows = [...(data.value?.vendor_performance || [])]
  return rows.sort((a, b) => {
    const first = a[sortBy.value]
    const second = b[sortBy.value]
    if (first === null || first === undefined) return second === null || second === undefined ? 0 : 1
    if (second === null || second === undefined) return -1
    const comparison = typeof first === 'number' && typeof second === 'number'
      ? first - second
      : String(first).localeCompare(String(second), undefined, { numeric: true, sensitivity: 'base' })
    return comparison * sortDirection.value
  })
})
const hasPurchaseOrders = computed(() => Number(stats.value.pos_count) > 0)
const maxTrendSpend = computed(() => Math.max(0, ...monthlyTrend.value.map((row) => Number(row.total_spend) || 0)))
const exportOptions = [
  { type: 'spend_by_category', label: 'Spend by category' },
  { type: 'vendors', label: 'Vendors' },
  { type: 'purchase_orders', label: 'Purchase orders' },
  { type: 'invoices', label: 'Invoices' },
]
const statisticCards = computed(() => [
  { label: 'RFQs created', value: stats.value.rfqs_created },
  { label: 'RFQs open', value: stats.value.rfqs_open },
  { label: 'Quotations received', value: stats.value.quotations_received },
  { label: 'Approvals pending', value: stats.value.approvals_pending },
  { label: 'Approvals approved', value: stats.value.approvals_approved },
  { label: 'Approvals rejected', value: stats.value.approvals_rejected },
  { label: 'Purchase orders', value: stats.value.pos_count },
  { label: 'Invoices', value: stats.value.invoices_count },
  { label: 'Invoices paid', value: stats.value.invoices_paid },
  { label: 'Amount invoiced', value: formatMoney(stats.value.amount_invoiced) },
  { label: 'Amount paid', value: formatMoney(stats.value.amount_paid) },
  { label: 'Outstanding', value: formatMoney(stats.value.amount_outstanding) },
])
const performanceColumns = [
  { label: 'Vendor', key: 'vendor' },
  { label: 'Rating', key: 'rating' },
  { label: 'RFQs invited', key: 'rfqs_invited' },
  { label: 'Quotations submitted', key: 'quotations_submitted' },
  { label: 'Response rate %', key: 'response_rate_percent' },
  { label: 'Times selected', key: 'times_selected' },
  { label: 'Win rate %', key: 'win_rate_percent' },
  { label: 'POs', key: 'po_count' },
  { label: 'Spend', key: 'spend' },
  { label: 'Avg quoted delivery (days)', key: 'avg_quoted_delivery_days' },
  { label: 'Fulfillment %', key: 'fulfillment_percent' },
]

async function loadReport() {
  const currentRequest = ++requestId
  loading.value = true
  error.value = ''
  data.value = null
  try {
    const response = await api.get('/reports/summary/', { params: { month: month.value } })
    if (currentRequest === requestId) data.value = response.data
  } catch (requestError) {
    if (currentRequest === requestId) error.value = getErrorMessage(requestError, 'Unable to load reports.')
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

function sortColumn(key) {
  if (sortBy.value === key) sortDirection.value *= -1
  else {
    sortBy.value = key
    sortDirection.value = 1
  }
}

function trendStyle(row) {
  const value = Number(row.total_spend) || 0
  return { height: `${maxTrendSpend.value ? (value / maxTrendSpend.value) * 100 : 0}%` }
}

function categoryStyle(row) {
  return { width: `${Number(row.percent) || 0}%` }
}

function ratingLabel(value) {
  return value === null || value === undefined || value === '' ? 'N/A' : `${value}/5`
}

function handleOutsideClick(event) {
  if (!exportMenu.value?.contains(event.target)) exportMenuOpen.value = false
}

function handleEscape(event) {
  if (event.key === 'Escape' && exportMenuOpen.value) {
    exportMenuOpen.value = false
    exportButton.value?.focus()
  }
}

async function exportReport(type) {
  exportError.value = ''
  exporting.value = type
  exportMenuOpen.value = false
  try {
    const response = await api.get('/reports/export/', {
      params: { type, month: month.value },
      responseType: 'blob',
    })
    const contentDisposition = response.headers['content-disposition'] || ''
    const filenameMatch = contentDisposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i)
    const filename = filenameMatch
      ? decodeURIComponent(filenameMatch[1].replaceAll('"', ''))
      : `vendorbridge-${type}-${month.value}.csv`
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.append(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (requestError) {
    exportError.value = getErrorMessage(requestError, 'Unable to export this report.')
  } finally {
    exporting.value = ''
  }
}

watch(month, loadReport)
onMounted(() => {
  loadReport()
  document.addEventListener('pointerdown', handleOutsideClick)
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => {
  requestId += 1
  document.removeEventListener('pointerdown', handleOutsideClick)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <section class="page reports-page">
    <div class="page-heading reports-heading">
      <div>
        <h1>Reports &amp; analytics</h1>
        <p class="muted">Procurement Insights - {{ data?.period?.label || month }}</p>
      </div>
      <div class="report-actions">
        <label class="report-month">
          <span>Month</span>
          <input v-model="month" type="month">
        </label>
        <div ref="exportMenu" class="report-export">
          <button
            ref="exportButton"
            class="button button-primary"
            type="button"
            aria-haspopup="true"
            :aria-expanded="exportMenuOpen"
            @click="exportMenuOpen = !exportMenuOpen"
          >
            {{ exporting ? 'Exporting…' : 'Export' }}
          </button>
          <div v-if="exportMenuOpen" class="report-export-menu">
            <button
              v-for="option in exportOptions"
              :key="option.type"
              type="button"
              :disabled="Boolean(exporting)"
              @click="exportReport(option.type)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <p v-if="exportError" class="form-error report-export-error" role="alert">{{ exportError }}</p>
    <p v-if="loading && !data" class="loading-message" role="status">Loading report…</p>
    <div v-else-if="error" class="report-error">
      <p class="form-error" role="alert">{{ error }}</p>
      <button class="button button-secondary" type="button" :disabled="loading" @click="loadReport">Retry</button>
    </div>
    <EmptyState v-else-if="data && !hasPurchaseOrders" message="No procurement data for this period" />

    <template v-else-if="data && hasPurchaseOrders">
      <div class="summary-grid report-summary-grid">
        <article class="summary-card report-summary-card">
          <div class="summary-card-top">
            <span class="summary-label">Total spend</span>
          </div>
          <span class="summary-value" :title="formatMoney(cards.total_spend)">
            {{ formatCompactMoney(cards.total_spend) }}
          </span>
          <span class="summary-caption">Purchase orders in this period</span>
        </article>
        <article class="summary-card report-summary-card">
          <div class="summary-card-top"><span class="summary-label">Active vendors</span></div>
          <span class="summary-value">{{ cards.active_vendors }}</span>
          <span class="summary-caption">Current active vendors</span>
        </article>
        <article class="summary-card report-summary-card">
          <div class="summary-card-top"><span class="summary-label">PO Fulfillment</span></div>
          <span class="summary-value">{{ cards.po_fulfillment_percent }}%</span>
          <span class="summary-caption">Paid purchase orders</span>
        </article>
        <article class="summary-card report-summary-card">
          <div class="summary-card-top"><span class="summary-label">Overdue invoices</span></div>
          <span class="summary-value">{{ cards.overdue_invoices }}</span>
          <span class="summary-caption">Unpaid and past due</span>
        </article>
      </div>

      <div class="report-chart-grid">
        <section class="panel report-panel">
          <div class="panel-heading"><h2>Spend by Category</h2></div>
          <EmptyState v-if="!spendByCategory.length" message="No category spend for this period" />
          <div v-else class="category-bars">
            <div v-for="row in spendByCategory" :key="row.category" class="category-bar-row">
              <div class="category-bar-heading">
                <strong>{{ row.category || 'Uncategorized' }}</strong>
                <span>{{ formatMoney(row.total) }} <small>{{ row.percent }}%</small></span>
              </div>
              <div class="category-bar-track" aria-hidden="true">
                <span :style="categoryStyle(row)"></span>
              </div>
            </div>
          </div>
        </section>

        <section class="panel report-panel">
          <div class="panel-heading"><h2>Top Vendors by Spend</h2></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Vendor</th><th>Spend</th><th>POs</th></tr></thead>
              <tbody>
                <tr v-for="vendor in topVendors" :key="vendor.vendor_id">
                  <td>{{ vendor.vendor }}</td>
                  <td>{{ formatMoney(vendor.spend) }}</td>
                  <td>{{ vendor.po_count }}</td>
                </tr>
                <tr v-if="!topVendors.length"><td colspan="3">No vendor spend for this period</td></tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section class="panel report-panel">
        <div class="panel-heading"><h2>Monthly Trend</h2></div>
        <div class="trend-chart">
          <div v-for="row in monthlyTrend" :key="row.month" class="trend-month">
            <div class="trend-plot">
              <div
                class="trend-bar"
                :class="{ 'trend-bar-selected': row.month === month }"
                :style="trendStyle(row)"
                :title="`${formatMoney(row.total_spend)} · ${row.po_count} POs`"
                :aria-label="`${row.label}: ${formatMoney(row.total_spend)}, ${row.po_count} POs`"
              ></div>
            </div>
            <span :class="{ 'trend-label-selected': row.month === month }">{{ row.label }}</span>
          </div>
        </div>
      </section>

      <section class="panel report-panel">
        <div class="panel-heading"><h2>Procurement Statistics</h2></div>
        <div class="statistics-grid">
          <article v-for="card in statisticCards" :key="card.label" class="statistic-card">
            <span>{{ card.label }}</span>
            <strong>{{ card.value ?? 0 }}</strong>
          </article>
        </div>
      </section>

      <section class="panel report-panel">
        <div class="panel-heading"><h2>Vendor Performance</h2></div>
        <div class="table-wrap performance-table-wrap">
          <table class="performance-table">
            <thead>
              <tr>
                <th
                  v-for="column in performanceColumns"
                  :key="column.key"
                  :aria-sort="sortBy === column.key ? (sortDirection > 0 ? 'ascending' : 'descending') : 'none'"
                >
                  <button type="button" @click="sortColumn(column.key)">{{ column.label }}</button>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="vendor in vendorPerformance" :key="vendor.vendor_id">
                <td>{{ vendor.vendor }}</td>
                <td>{{ ratingLabel(vendor.rating) }}</td>
                <td>{{ vendor.rfqs_invited }}</td>
                <td>{{ vendor.quotations_submitted }}</td>
                <td>{{ vendor.response_rate_percent }}%</td>
                <td>{{ vendor.times_selected }}</td>
                <td>{{ vendor.win_rate_percent }}%</td>
                <td>{{ vendor.po_count }}</td>
                <td>{{ formatMoney(vendor.spend) }}</td>
                <td>{{ vendor.avg_quoted_delivery_days ?? 'N/A' }}</td>
                <td>{{ vendor.fulfillment_percent }}%</td>
              </tr>
              <tr v-if="!vendorPerformance.length"><td colspan="11">No vendor performance data</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <details class="panel report-methodology">
        <summary>How these numbers are calculated</summary>
        <ul>
          <li>Total spend = sum of purchase order totals created in the period.</li>
          <li>PO Fulfillment = purchase orders whose invoice is marked Paid, divided by all purchase orders in the period.</li>
          <li>Overdue invoices = unpaid invoices past their due date (as of today).</li>
          <li>Response rate = quotations submitted divided by RFQs the vendor was invited to.</li>
          <li>Win rate = times selected divided by quotations submitted.</li>
        </ul>
      </details>
    </template>
  </section>
</template>

<style scoped>
.reports-heading {
  align-items: flex-end;
}

.report-actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.report-month {
  display: grid;
  gap: 5px;
  color: #3f4a42;
  font-size: 10px;
  font-weight: 600;
}

.report-month input {
  min-height: 38px;
  padding: 7px 10px;
  border: 1px solid #e1e7e2;
  border-radius: 9px;
  background: #fff;
  color: var(--text);
}

.report-export {
  position: relative;
}

.report-export-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 7px);
  right: 0;
  display: grid;
  width: 190px;
  overflow: hidden;
  padding: 5px;
  border: 1px solid var(--border);
  border-radius: 11px;
  background: #fff;
  box-shadow: var(--shadow-soft);
}

.report-export-menu button {
  padding: 10px;
  border: 0;
  border-radius: 7px;
  background: #fff;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  font-size: 11px;
}

.report-export-menu button:hover {
  background: var(--surface-hover);
}

.report-export-error {
  margin: -10px 0 15px;
}

.report-error {
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 16px 0;
}

.report-summary-grid {
  margin-bottom: 14px;
}

.report-summary-card {
  min-height: 122px;
}

.report-chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.report-panel {
  min-width: 0;
}

.category-bars {
  display: grid;
  gap: 17px;
}

.category-bar-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #3d4740;
  font-size: 11px;
}

.category-bar-heading span {
  white-space: nowrap;
}

.category-bar-heading small {
  margin-left: 5px;
  color: var(--muted);
}

.category-bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2ee;
}

.category-bar-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--green);
}

.trend-chart {
  display: grid;
  height: 210px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 15px;
  padding: 10px 4px 0;
}

.trend-month {
  display: grid;
  min-width: 0;
  grid-template-rows: 1fr auto;
  justify-items: center;
  gap: 9px;
  color: var(--muted);
  font-size: 10px;
}

.trend-plot {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: flex-end;
  justify-content: center;
  border-bottom: 1px solid #edf0ed;
}

.trend-bar {
  width: min(100%, 42px);
  min-height: 0;
  border-radius: 6px 6px 0 0;
  background: #78bd96;
}

.trend-bar-selected {
  background: var(--green-dark);
}

.trend-label-selected {
  color: var(--green-dark);
  font-weight: 700;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}

.statistic-card {
  display: grid;
  min-height: 72px;
  align-content: space-between;
  gap: 8px;
  padding: 12px;
  border: 1px solid #edf0ed;
  border-radius: 11px;
  background: #fbfcfb;
}

.statistic-card span {
  color: var(--muted);
  font-size: 10px;
}

.statistic-card strong {
  color: #26362b;
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.performance-table-wrap {
  overflow-x: auto;
}

.performance-table {
  min-width: 1300px;
}

.performance-table th button {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  text-transform: inherit;
}

.report-methodology summary {
  color: #303a33;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.report-methodology ul {
  display: grid;
  gap: 8px;
  padding-left: 18px;
  margin-bottom: 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

@media (max-width: 850px) {
  .report-chart-grid {
    grid-template-columns: 1fr;
  }

  .statistics-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .reports-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .report-actions {
    justify-content: space-between;
  }

  .report-summary-grid {
    grid-template-columns: 1fr;
  }

  .statistics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
