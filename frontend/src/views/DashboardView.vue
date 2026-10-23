<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import SummaryCard from '../components/SummaryCard.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'

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
const trends = computed(() => data.value?.spending_trends || [])
const summaryCards = computed(() => [
  { label: "Active RFQ's", value: cards.value.active_rfqs, featured: true },
  { label: 'Pending Approvals', value: cards.value.pending_approvals },
  { label: "PO's this month", value: cards.value.pos_this_month },
  { label: 'Overdue invoices', value: cards.value.overdue_invoices },
])
const vendorCards = computed(() => [
  { label: 'Total vendors', value: cards.value.total_vendors },
  { label: 'Active vendors', value: cards.value.active_vendors },
])

function getValue(row, keys, fallback = '—') {
  for (const key of keys) {
    if (row?.[key] !== undefined && row[key] !== null) return row[key]
  }
  return fallback
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
        <RouterLink class="button button-secondary" to="/rfqs">+ New RFQ</RouterLink>
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
          caption="Latest snapshot"
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
                <tr v-for="(order, index) in purchaseOrders" :key="order.id || index">
                  <td>{{ getValue(order, ['po_number', 'number', 'id']) }}</td>
                  <td>{{ getValue(order, ['vendor_name', 'vendor']) }}</td>
                  <td>{{ getValue(order, ['amount', 'total']) }}</td>
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
          <div v-if="trends.length" class="trend-list">
            <div v-for="(trend, index) in trends" :key="trend.month || trend.label || index" class="trend-row">
              <span>{{ getValue(trend, ['month', 'label']) }}</span>
              <strong>{{ getValue(trend, ['amount', 'total', 'spend'], 0) }}</strong>
            </div>
          </div>
          <EmptyState v-else message="No data yet" />
        </section>
      </div>
    </template>
  </section>
</template>
