<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import SummaryCard from '../components/SummaryCard.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'
import { formatMoney } from '../utils/format'

const auth = useAuth()
const router = useRouter()
const data = ref(null)
const loading = ref(true)
const error = ref('')
const roleLabels = {
  admin: 'Admin',
  officer: 'Procurement Officer',
  manager: 'Manager/Approver',
  vendor: 'Vendor',
}
const welcome = computed(() => data.value?.welcome_role || roleLabels[auth.role] || auth.role)
const cards = computed(() => data.value?.cards || {})
const purchaseOrders = computed(() => data.value?.recent_purchase_orders || [])
const trends = computed(() => (data.value?.spending_trends || []).slice(-6))
const summaryCards = computed(() => [
  { label: "Active RFQ's", value: cards.value.active_rfqs, featured: true },
  { label: 'Pending Approvals', value: cards.value.pending_approvals },
  { label: "PO's this month", value: cards.value.pos_this_month, caption: formatMoney(cards.value.pos_this_month_amount) },
  { label: 'Overdue invoices', value: cards.value.overdue_invoices },
])
const vendorCards = computed(() => [
  { label: 'Total vendors', value: cards.value.total_vendors },
  { label: 'Active vendors', value: cards.value.active_vendors },
])
const hasTrendValues = computed(() => trends.value.some((trend) => Number(getValue(trend, ['amount', 'total', 'spend'], 0)) > 0))
const trendMax = computed(() => Math.max(0, ...trends.value.map((trend) => Number(getValue(trend, ['amount', 'total', 'spend'], 0)) || 0)))

function trendAmount(trend) {
  return Number(getValue(trend, ['amount', 'total', 'spend'], 0)) || 0
}

function trendStyle(trend) {
  return { height: `${trendMax.value ? Math.max(4, trendAmount(trend) / trendMax.value * 100) : 0}%` }
}

function getValue(row, keys, fallback = '—') {
  for (const key of keys) {
    if (row?.[key] !== undefined && row[key] !== null) return row[key]
  }
  return fallback
}

function openPurchaseOrder(order) {
  if (order.id) router.push(`/purchase-orders/${order.id}`)
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/dashboard/')
    data.value = response.data
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load dashboard information.')
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page">
    <div class="page-heading dashboard-heading">
      <div>
        <h1>Dashboard</h1>
        <p class="muted">Welcome back, {{ welcome }} - Today's Overview</p>
      </div>
      <div class="quick-actions">
        <RouterLink v-if="auth.role !== 'manager'" class="button button-secondary" to="/rfqs/new">+ New RFQ</RouterLink>
        <RouterLink class="button button-primary" to="/vendors?add=1">Add Vendor</RouterLink>
        <RouterLink class="button button-secondary" to="/invoices">View Invoices</RouterLink>
      </div>
    </div>

    <p v-if="loading" class="loading-message" role="status">Loading dashboard…</p>
    <p v-else-if="error" class="form-error page-alert" role="alert">{{ error }}</p>

    <template v-if="data && !loading">
      <div class="summary-grid dashboard-summary-grid">
        <SummaryCard
          v-for="card in summaryCards"
          :key="card.label"
          :label="card.label"
          :value="card.value ?? 0"
          :featured="card.featured"
          :caption="card.caption || 'Latest snapshot'"
        />
      </div>
      <div class="extra-summary-grid">
        <SummaryCard
          v-for="card in vendorCards"
          :key="card.label"
          :label="card.label"
          :value="card.value ?? 0"
          caption="Vendor network"
        />
      </div>

      <div class="dashboard-panels">
        <section class="panel purchase-panel">
          <div class="panel-heading">
            <h2>Recent Purchase Orders</h2>
            <RouterLink class="text-link" to="/purchase-orders">View all</RouterLink>
          </div>
          <div v-if="purchaseOrders.length" class="table-wrap">
            <table>
              <thead>
                <tr><th>PO#</th><th>Vendor</th><th>Amount</th><th>Status</th></tr>
              </thead>
              <tbody>
                <tr
                  v-for="(order, index) in purchaseOrders"
                  :key="order.id || index"
                  class="dashboard-po-row"
                  :tabindex="order.id ? 0 : undefined"
                  @click="openPurchaseOrder(order)"
                  @keydown.enter="openPurchaseOrder(order)"
                >
                  <td>{{ getValue(order, ['po_number', 'number', 'id']) }}</td>
                  <td>{{ getValue(order, ['vendor_name', 'vendor']) }}</td>
                  <td>{{ formatMoney(getValue(order, ['grand_total', 'amount', 'total'], 0)) }}</td>
                  <td><StatusBadge :status="String(getValue(order, ['status'], 'Pending'))" /></td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else message="No data yet" />
        </section>

        <section class="panel trends-panel">
          <div class="panel-heading">
            <h2>Spending Trends (last 6 months)</h2>
          </div>
          <div v-if="trends.length && hasTrendValues" class="trend-chart">
            <div v-for="(trend, index) in trends" :key="trend.month || trend.label || index" class="trend-column">
              <span class="trend-amount" :title="formatMoney(trendAmount(trend))">{{ formatMoney(trendAmount(trend)) }}</span>
              <div class="trend-bar-track">
                <span class="trend-bar" :style="trendStyle(trend)" :title="formatMoney(trendAmount(trend))"></span>
              </div>
              <span class="trend-month">{{ getValue(trend, ['month', 'label']) }}</span>
            </div>
          </div>
          <EmptyState v-else message="No spending data yet" />
        </section>
      </div>
    </template>

  </section>
</template>

<style scoped>
.dashboard-po-row {
  cursor: pointer;
}

.dashboard-po-row:focus-visible {
  outline: 2px solid var(--green-light);
  outline-offset: -2px;
}

.trend-chart {
  display: grid;
  min-height: 160px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  align-items: end;
  gap: 10px;
  padding-top: 12px;
}

.trend-column {
  display: grid;
  height: 100%;
  min-width: 0;
  grid-template-rows: auto 1fr auto;
  justify-items: center;
  gap: 7px;
}

.trend-amount {
  max-width: 100%;
  overflow: hidden;
  color: var(--muted);
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trend-bar-track {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: flex-end;
  justify-content: center;
  border-bottom: 1px solid var(--border-strong);
}

.trend-bar {
  width: min(30px, 70%);
  min-height: 3px;
  border-radius: 6px 6px 0 0;
  background: var(--green);
}

.trend-month {
  color: var(--muted);
  font-size: 9px;
  text-align: center;
}

@media (max-width: 520px) {
  .trend-chart {
    gap: 4px;
  }

  .trend-amount {
    font-size: 7px;
  }
}
</style>
