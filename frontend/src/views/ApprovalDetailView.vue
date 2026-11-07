<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Clock3, X } from 'lucide-vue-next'
import api from '../api'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'
import { formatDate, formatDateTime, formatMoney } from '../utils/format'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const approval = ref(null)
const remarks = ref('')
const loading = ref(true)
const saving = ref(false)
const generating = ref(false)
const error = ref('')
const actionMessage = ref('')

const steps = computed(() => approval.value?.steps || [])
const status = computed(() => String(approval.value?.status || '').toLowerCase())
const canGeneratePo = computed(() => (
  ['admin', 'officer'].includes(auth.role)
  && status.value === 'approved'
  && !approval.value?.po_id
))
const quotation = computed(() => approval.value?.quotation || approval.value?.selected_quotation || {})
const vendorName = computed(() => (
  approval.value?.vendor_name
  || approval.value?.vendor?.name
  || quotation.value.vendor_name
  || quotation.value.vendor?.name
  || '—'
))
const rfqTitle = computed(() => approval.value?.rfq_title || approval.value?.rfq?.title || '—')

const workflowSteps = [
  { label: 'Submitted', key: 'submitted' },
  { label: 'L1 Review', key: 'l1' },
  { label: 'L2 Approval', key: 'l2' },
  { label: 'Generate PO', key: 'po' },
]

function stepText(step) {
  return String(step?.name || step?.title || step?.level || step?.step || '').toLowerCase()
}

function stepRecord(key) {
  if (key === 'submitted' || key === 'po') return null
  return steps.value.find((step) => {
    const text = stepText(step)
    return key === 'l1' ? /l1|level.?1|first/.test(text) : /l2|level.?2|second/.test(text)
  })
}

function stepState(key) {
  if (key === 'submitted') return 'done'
  if (key === 'po') {
    if (approval.value?.po_id) return 'done'
    return status.value === 'approved' ? 'current' : 'upcoming'
  }
  const record = stepRecord(key)
  const decision = String(record?.decision || record?.status || '').toLowerCase()
  if (['approved', 'complete', 'completed', 'done'].includes(decision)) return 'done'
  if (['rejected', 'declined'].includes(decision)) return 'rejected'
  if (
    record?.is_current
    || String(approval.value?.current_step || '').toLowerCase().includes(key)
    || (decision === 'pending' && !record?.waiting_for_previous)
  ) return 'current'
  return 'upcoming'
}

function decidedBy(step) {
  const person = step.decided_by || step.approver || step.user || {}
  if (typeof person === 'string') return person
  return person.name || [person.first_name, person.last_name].filter(Boolean).join(' ') || person.email || '—'
}

function stepStatus(step) {
  return String(step.decision || step.status || '').toLowerCase()
}

function isStepDecided(step) {
  return ['approved', 'rejected', 'declined'].includes(stepStatus(step)) || Boolean(step.decided_at)
}

function stepIcon(step) {
  const decision = stepStatus(step)
  if (['approved', 'complete', 'completed', 'done'].includes(decision)) return Check
  if (['rejected', 'declined'].includes(decision)) return X
  return Clock3
}

function stepRole(step) {
  const person = step.decided_by || step.approver || step.user || {}
  return step.role || person.role || step.approver_role || ''
}

function ratingText() {
  const rating = quotation.value.vendor_rating ?? quotation.value.rating ?? approval.value.vendor_rating
  if (rating === undefined || rating === null || rating === '') return 'No rating'
  return String(rating).includes('/') ? String(rating) : `${rating}/5`
}

async function loadApproval() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/approvals/${route.params.id}/`)
    approval.value = response.data
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load this approval.')
  } finally {
    loading.value = false
  }
}

async function decide(decision) {
  if (decision === 'rejected' && !remarks.value.trim()) {
    error.value = 'Add remarks before rejecting this approval.'
    return
  }
  const verb = decision === 'approved' ? 'approve' : 'reject'
  if (!window.confirm(`Are you sure you want to ${verb} this approval?`)) return

  saving.value = true
  error.value = ''
  actionMessage.value = ''
  try {
    await api.post(`/approvals/${route.params.id}/decide/`, {
      decision,
      remarks: remarks.value.trim(),
    })
    actionMessage.value = `Approval ${decision}.`
    await loadApproval()
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to update this approval.')
  } finally {
    saving.value = false
  }
}

async function generatePurchaseOrder() {
  if (!window.confirm('Generate a purchase order for this approval?')) return
  generating.value = true
  error.value = ''
  try {
    const response = await api.post('/purchase-orders/', { approval_id: approval.value.id })
    const id = response.data?.id || response.data?.purchase_order?.id
    if (!id) {
      error.value = 'The purchase order was created, but its ID was not returned.'
      return
    }
    await router.push(`/purchase-orders/${id}`)
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to generate a purchase order.')
  } finally {
    generating.value = false
  }
}

onMounted(loadApproval)
</script>

<template>
  <section class="page approval-detail-page">
    <p v-if="loading" class="loading-message" role="status">Loading approval…</p>
    <template v-else-if="approval">
      <div class="page-heading">
        <div>
          <h1>Approval Workflow</h1>
          <p class="muted">RFQ: {{ rfqTitle }} - Vendor: {{ vendorName }} - {{ formatMoney(approval.grand_total ?? quotation.grand_total) }}</p>
        </div>
        <StatusBadge :status="String(approval.status || 'pending')" />
      </div>

      <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
      <p v-if="actionMessage" class="success-message page-alert" role="status">{{ actionMessage }}</p>

      <section class="panel approval-stepper" aria-label="Approval progress">
        <div v-for="(step, index) in workflowSteps" :key="step.key" class="approval-step" :class="`step-${stepState(step.key)}`">
          <span class="approval-step-number">{{ stepState(step.key) === 'done' ? '✓' : index + 1 }}</span>
          <span class="approval-step-label">{{ step.label }}</span>
        </div>
      </section>

      <div class="approval-detail-grid">
        <div class="approval-detail-main">
          <section class="panel">
            <div class="panel-heading"><h2>Approval Chain</h2></div>
            <div v-if="steps.length" class="approval-chain">
              <article v-for="(step, index) in steps" :key="step.id || index" class="approval-chain-item">
                <span class="approval-chain-icon" :class="`chain-${stepStatus(step) || 'pending'}`">
                  <component :is="stepIcon(step)" :size="16" aria-hidden="true" />
                </span>
                <div>
                  <strong>{{ decidedBy(step) }}<span v-if="stepRole(step)"> ({{ stepRole(step) }})</span></strong>
                  <p class="muted">{{ isStepDecided(step) ? formatDateTime(step.decided_at || step.updated_at || step.created_at) : (step.waiting_for_previous || stepStatus(step) === 'waiting' ? 'Waiting for previous level' : 'Awaiting') }}</p>
                  <p v-if="isStepDecided(step) && step.remarks" class="approval-step-remarks">{{ step.remarks }}</p>
                </div>
              </article>
            </div>
            <EmptyState v-else message="No approval steps available" />
          </section>

          <section class="panel">
            <div class="panel-heading"><h2>Timeline</h2></div>
            <ol v-if="approval.timeline?.length" class="approval-timeline">
              <li v-for="(item, index) in approval.timeline" :key="item.id || index">
                <strong>{{ item.title || item.event || item.action || 'Update' }}</strong>
                <span class="muted">{{ formatDateTime(item.created_at || item.timestamp || item.date) }}</span>
                <p v-if="item.description || item.remarks">{{ item.description || item.remarks }}</p>
              </li>
            </ol>
            <EmptyState v-else message="No timeline events" />
          </section>

          <section v-if="approval.can_decide" class="panel">
            <label class="form-field">
              <span>Approval Remarks</span>
              <textarea v-model="remarks" placeholder="Add your comments or conditions…"></textarea>
            </label>
            <div class="approval-actions">
              <button class="button button-primary" type="button" :disabled="saving" @click="decide('approved')">
                {{ saving ? 'Saving…' : 'Approve' }}
              </button>
              <button class="button button-danger" type="button" :disabled="saving" @click="decide('rejected')">
                Reject
              </button>
            </div>
          </section>
        </div>

        <aside class="approval-detail-side">
          <section class="panel">
            <div class="panel-heading"><h2>Quotation Summary</h2></div>
            <dl class="approval-summary">
              <div><dt>Vendor</dt><dd>{{ vendorName }}</dd></div>
              <div><dt>Total</dt><dd>{{ formatMoney(approval.grand_total ?? quotation.grand_total) }}</dd></div>
              <div><dt>Delivery</dt><dd>{{ quotation.delivery_days ?? approval.delivery_days ?? '—' }}<span v-if="quotation.delivery_days ?? approval.delivery_days"> days</span></dd></div>
              <div><dt>Rating</dt><dd>{{ ratingText() }}</dd></div>
            </dl>
          </section>
          <section v-if="approval.po_id || canGeneratePo" class="panel approval-po-panel">
            <RouterLink v-if="approval.po_id" class="button button-secondary" :to="`/purchase-orders/${approval.po_id}`">View Purchase Order</RouterLink>
            <button v-else class="button button-primary" type="button" :disabled="generating" @click="generatePurchaseOrder">
              {{ generating ? 'Generating…' : 'Generate Purchase Order' }}
            </button>
          </section>
        </aside>
      </div>
    </template>
    <EmptyState v-else message="Approval could not be loaded" />
  </section>
</template>

<style scoped>
.approval-stepper {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.approval-step {
  display: grid;
  justify-items: center;
  gap: 9px;
  color: var(--muted);
  text-align: center;
}

.approval-step-number,
.approval-chain-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
}

.step-done .approval-step-number {
  border-color: var(--green);
  background: var(--green-soft);
  color: var(--green-dark);
}

.step-current .approval-step-number {
  border-color: var(--amber);
  background: var(--amber-soft);
  color: var(--amber);
}

.approval-step-label {
  font-size: 11px;
}

.step-current .approval-step-label {
  color: var(--green-dark);
  font-weight: 600;
}

.approval-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(260px, 1fr);
  align-items: start;
  gap: 18px;
}

.approval-detail-main,
.approval-detail-side {
  min-width: 0;
}

.approval-chain {
  display: grid;
  gap: 16px;
}

.approval-chain-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.approval-chain-item strong {
  font-size: 12px;
}

.approval-chain-item p {
  margin: 4px 0 0;
  font-size: 11px;
}

.chain-approved {
  color: var(--green);
}

.chain-rejected {
  color: var(--red);
}

.chain-pending {
  color: var(--amber);
}

.approval-step-remarks {
  color: var(--text);
}

.approval-summary {
  display: grid;
  gap: 12px;
  margin: 0;
}

.approval-summary div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.approval-summary dt {
  color: var(--muted);
}

.approval-summary dd {
  margin: 0;
  text-align: right;
}

.approval-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.approval-po-panel .button {
  width: 100%;
}

.approval-timeline {
  display: grid;
  gap: 14px;
  padding-left: 20px;
  margin: 0;
}

.approval-timeline li {
  padding-left: 3px;
}

.approval-timeline span {
  display: block;
  margin-top: 4px;
}

.approval-timeline p {
  margin: 6px 0 0;
}

@media (max-width: 760px) {
  .approval-detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
