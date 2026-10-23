<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import FormField from '../components/FormField.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage, getFieldErrors } from '../utils/errors'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const vendors = ref([])
const stats = ref({ all: 0, active: 0, pending: 0, blocked: 0 })
const search = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
const modalError = ref('')
const modalLoading = ref(false)
const selected = ref(null)
const formOpen = ref(false)
const editing = ref(false)
const fieldErrors = ref({})
const editingId = ref(null)
let searchTimer

const isAdmin = computed(() => auth.role === 'admin')
const canManage = computed(() => isAdmin.value || auth.role === 'officer')
const tabs = computed(() => [
  { label: 'All', value: '', count: stats.value.all },
  { label: 'Active', value: 'active', count: stats.value.active },
  { label: 'Pending', value: 'pending', count: stats.value.pending },
  { label: 'Blocked', value: 'blocked', count: stats.value.blocked },
])
const form = reactive({
  name: '',
  category: '',
  gst_number: '',
  contact_person: '',
  contact_email: '',
  contact_phone: '',
  address: '',
  status: 'pending',
})

function resetForm() {
  Object.assign(form, {
    name: '',
    category: '',
    gst_number: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    status: 'pending',
  })
  fieldErrors.value = {}
  modalError.value = ''
}

async function loadVendors() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/vendors/', {
      params: {
        search: search.value.trim(),
        status: status.value,
        category: '',
      },
    })
    vendors.value = Array.isArray(response.data) ? response.data : response.data.results || []
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load vendors.')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await api.get('/vendors/stats/')
    stats.value = { ...stats.value, ...response.data }
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load vendor counts.')
  }
}

function setStatus(value) {
  status.value = value
}

function openAdd() {
  selected.value = null
  editing.value = false
  editingId.value = null
  resetForm()
  formOpen.value = true
}

function openEdit() {
  if (!selected.value || !canManage.value) return
  editingId.value = selected.value.id
  Object.assign(form, {
    name: selected.value.name || '',
    category: selected.value.category || '',
    gst_number: selected.value.gst_number || '',
    contact_person: selected.value.contact_person || '',
    contact_email: selected.value.contact_email || '',
    contact_phone: selected.value.contact_phone || '',
    address: selected.value.address || '',
    status: selected.value.status || 'pending',
  })
  fieldErrors.value = {}
  modalError.value = ''
  editing.value = true
  selected.value = null
  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
}

async function saveVendor() {
  fieldErrors.value = {}
  modalError.value = ''
  modalLoading.value = true
  try {
    if (editing.value && editingId.value) {
      await api.put(`/vendors/${editingId.value}/`, { ...form })
    } else {
      await api.post('/vendors/', { ...form })
    }
    formOpen.value = false
    await Promise.all([loadVendors(), loadStats()])
  } catch (err) {
    fieldErrors.value = getFieldErrors(err)
    modalError.value = getErrorMessage(err, 'Unable to save vendor details.')
  } finally {
    modalLoading.value = false
  }
}

async function deleteVendor() {
  if (!selected.value || !isAdmin.value) return
  const name = selected.value.name || 'this vendor'
  if (!window.confirm(`Delete ${name}? This action cannot be undone.`)) return
  try {
    await api.delete(`/vendors/${selected.value.id}/`)
    selected.value = null
    await Promise.all([loadVendors(), loadStats()])
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to delete vendor.')
  }
}

function openQueryForm(value) {
  if (value === '1' && canManage.value && !formOpen.value) openAdd()
  if (value === '1') router.replace({ query: { ...route.query, add: undefined } })
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadVendors, 300)
})
watch(status, loadVendors)
watch(() => route.query.add, openQueryForm)

onMounted(() => {
  loadVendors()
  loadStats()
  openQueryForm(route.query.add)
})
onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="page vendors-page">
    <div class="page-heading">
      <div>
        <h1>Vendors</h1>
        <p class="muted">Manage supplier profiles and registrations</p>
      </div>
      <button v-if="canManage" class="button button-primary" type="button" @click="openAdd">+ Add Vendor</button>
    </div>

    <div class="panel vendor-search-panel">
      <label class="search-field">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input v-model="search" type="search" placeholder="Search by name, GST number, category..." aria-label="Search vendors">
      </label>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <div class="status-tabs" role="tablist" aria-label="Filter vendors by status">
      <button
        v-for="tab in tabs"
        :key="tab.value || 'all'"
        class="status-tab"
        :class="{ 'status-tab-active': status === tab.value }"
        type="button"
        role="tab"
        :aria-selected="status === tab.value"
        @click="setStatus(tab.value)"
      >
        {{ tab.label }} <span>{{ tab.count }}</span>
      </button>
    </div>

    <div class="panel vendor-table-panel">
      <p v-if="loading" class="loading-message">Loading vendors…</p>
      <div v-else-if="vendors.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Vendor Name</th>
              <th>Category</th>
              <th>GST no.</th>
              <th>Contact no.</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="vendor in vendors" :key="vendor.id">
              <td class="vendor-name">{{ vendor.name }}</td>
              <td>{{ vendor.category || '—' }}</td>
              <td>{{ vendor.gst_number || '—' }}</td>
              <td>{{ vendor.contact_phone || '—' }}</td>
              <td><StatusBadge :status="vendor.status" /></td>
              <td><button class="button button-small button-secondary" type="button" @click="selected = vendor">View</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else message="No vendors found" />
    </div>

    <BaseModal v-if="formOpen" :title="editing ? 'Edit Vendor' : 'Add Vendor'" @close="closeForm">
      <form class="form-stack" @submit.prevent="saveVendor">
        <div class="form-grid">
          <FormField v-model="form.name" label="Name" :error="fieldErrors.name" required />
          <FormField v-model="form.category" label="Category" :error="fieldErrors.category" required />
          <FormField v-model="form.gst_number" label="GST number" :error="fieldErrors.gst_number" required />
          <FormField v-model="form.contact_person" label="Contact person" :error="fieldErrors.contact_person" required />
          <FormField v-model="form.contact_email" label="Contact email" type="email" :error="fieldErrors.contact_email" required />
          <FormField v-model="form.contact_phone" label="Contact phone" type="tel" :error="fieldErrors.contact_phone" required />
        </div>
        <label class="form-field">
          <span>Address</span>
          <textarea v-model="form.address" rows="3" :aria-invalid="Boolean(fieldErrors.address)" required></textarea>
          <small v-if="fieldErrors.address" class="field-error">{{ fieldErrors.address }}</small>
        </label>
        <label class="form-field">
          <span>Status</span>
          <select v-model="form.status" :aria-invalid="Boolean(fieldErrors.status)">
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="blocked">Blocked</option>
          </select>
          <small v-if="fieldErrors.status" class="field-error">{{ fieldErrors.status }}</small>
        </label>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" @click="closeForm">Cancel</button>
          <button class="button button-primary" type="submit" :disabled="modalLoading">
            {{ modalLoading ? 'Saving…' : 'Save Vendor' }}
          </button>
        </div>
      </form>
    </BaseModal>

    <BaseModal v-if="selected" title="Vendor Details" @close="selected = null">
      <div class="detail-grid">
        <div><span>Vendor name</span><strong>{{ selected.name || '—' }}</strong></div>
        <div><span>Category</span><strong>{{ selected.category || '—' }}</strong></div>
        <div><span>GST number</span><strong>{{ selected.gst_number || '—' }}</strong></div>
        <div><span>Status</span><StatusBadge :status="selected.status" /></div>
        <div><span>Contact person</span><strong>{{ selected.contact_person || '—' }}</strong></div>
        <div><span>Contact email</span><strong>{{ selected.contact_email || '—' }}</strong></div>
        <div><span>Contact phone</span><strong>{{ selected.contact_phone || '—' }}</strong></div>
        <div class="detail-wide"><span>Address</span><strong>{{ selected.address || '—' }}</strong></div>
        <div v-if="selected.created_at" class="detail-wide"><span>Created</span><strong>{{ selected.created_at }}</strong></div>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <div class="modal-actions">
        <button v-if="canManage" class="button button-secondary" type="button" @click="openEdit">Edit</button>
        <button v-if="isAdmin" class="button button-danger" type="button" @click="deleteVendor">Delete</button>
      </div>
    </BaseModal>
  </section>
</template>
