<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import EmptyState from '../components/EmptyState.vue'
import { getErrorMessage, getFieldErrors } from '../utils/errors'

const route = useRoute()
const router = useRouter()
const rfqId = ref(route.params.id || '')
const status = ref('draft')
const quotationCount = ref(0)
const loading = ref(Boolean(route.params.id))
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})
const attachmentError = ref('')
const vendors = ref([])
const assignedVendors = ref([])
const attachments = ref([])
const vendorChoice = ref('')
const fileInput = ref(null)
const form = reactive({
  title: '',
  category: '',
  description: '',
  deadline: '',
  items: [],
})

const isEditing = computed(() => Boolean(route.params.id || rfqId.value))
const itemsEditable = computed(() => !isEditing.value || status.value === 'draft')
const progress = computed(() => {
  if (status.value === 'draft') return 1
  if (quotationCount.value > 0 || ['quotations_received', 'selected'].includes(status.value)) return 3
  return 2
})
const availableVendors = computed(() => vendors.value.filter(
  (vendor) => !assignedVendors.value.some((assigned) => String(assigned.id) === String(vendor.id)),
))

function getRows(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

function toLocalDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function vendorDetails(vendor) {
  if (vendor && typeof vendor === 'object') {
    return { id: vendor.id, name: vendor.name || vendor.vendor_name || vendor.company_name || `Vendor ${vendor.id}` }
  }
  const match = vendors.value.find((item) => String(item.id) === String(vendor))
  return match || { id: vendor, name: `Vendor ${vendor}` }
}

async function loadVendors() {
  const response = await api.get('/vendors/', { params: { status: 'active' } })
  vendors.value = getRows(response.data).filter((vendor) => vendor.status === 'active')
}

async function loadRfq() {
  if (!route.params.id) return
  const response = await api.get(`/rfqs/${route.params.id}/`)
  const rfq = response.data
  rfqId.value = rfq.id
  status.value = rfq.status || 'draft'
  quotationCount.value = rfq.quotation_count ?? rfq.quotations_count ?? 0
  Object.assign(form, {
    title: rfq.title || '',
    category: rfq.category || '',
    description: rfq.description || '',
    deadline: toLocalDateTime(rfq.deadline),
    items: Array.isArray(rfq.items) ? rfq.items.map((item) => ({
      id: item.id,
      name: item.name || '',
      quantity: item.quantity ?? '',
      unit: item.unit || '',
    })) : [],
  })
  assignedVendors.value = (rfq.vendors || []).map(vendorDetails)
  attachments.value = (rfq.attachments || []).map((attachment) => ({
    ...attachment,
    name: attachment.name || attachment.file_name || attachment.filename || 'Attachment',
    uploaded: true,
  }))
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    await loadVendors()
    await loadRfq()
    if (!form.items.length) form.items.push({ name: '', quantity: 1, unit: '' })
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to load the RFQ form.')
  } finally {
    loading.value = false
  }
}

function addItem() {
  form.items.push({ name: '', quantity: 1, unit: '' })
}

function removeItem(index) {
  form.items.splice(index, 1)
}

function addVendor() {
  if (!vendorChoice.value) return
  const vendor = vendors.value.find((item) => String(item.id) === String(vendorChoice.value))
  if (vendor) assignedVendors.value.push(vendorDetails(vendor))
  vendorChoice.value = ''
}

function removeVendor(id) {
  assignedVendors.value = assignedVendors.value.filter((vendor) => String(vendor.id) !== String(id))
}

function checkFiles(files) {
  attachmentError.value = ''
  const allowed = ['pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx']
  for (const file of files) {
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!extension || !allowed.includes(extension)) {
      attachmentError.value = 'Allowed file types: PDF, PNG, JPG, JPEG, DOCX and XLSX.'
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      attachmentError.value = 'Each attachment must be 5 MB or smaller.'
      return
    }
  }
  attachments.value.push(...files.map((file) => ({ file, name: file.name, size: file.size, uploaded: false })))
}

function handleFiles(event) {
  checkFiles(Array.from(event.target.files || []))
  event.target.value = ''
}

function handleDrop(event) {
  checkFiles(Array.from(event.dataTransfer?.files || []))
}

async function removeAttachment(index) {
  const attachment = attachments.value[index]
  if (attachment.uploaded && rfqId.value) {
    error.value = ''
    try {
      await api.delete(`/rfqs/${rfqId.value}/attachments/${attachment.id}/`)
    } catch (err) {
      error.value = getErrorMessage(err, 'Unable to remove the attachment.')
      return
    }
  }
  attachments.value.splice(index, 1)
}

function validate() {
  fieldErrors.value = {}
  if (!form.title.trim()) fieldErrors.value.title = 'Enter an RFQ title.'
  if (!form.deadline || Number.isNaN(new Date(form.deadline).getTime())) {
    fieldErrors.value.deadline = 'Choose a valid deadline.'
  }
  if (!form.items.length) fieldErrors.value.items = 'Add at least one line item.'
  form.items.forEach((item, index) => {
    if (!item.name.trim()) fieldErrors.value[`items.${index}.name`] = 'Enter an item name.'
    if (!item.quantity || Number(item.quantity) <= 0) fieldErrors.value[`items.${index}.quantity`] = 'Enter a quantity greater than zero.'
    if (!item.unit.trim()) fieldErrors.value[`items.${index}.unit`] = 'Enter a unit.'
  })
  return Object.keys(fieldErrors.value).length === 0
}

async function uploadAttachments() {
  for (let index = 0; index < attachments.value.length; index += 1) {
    const attachment = attachments.value[index]
    if (attachment.uploaded) continue
    const body = new FormData()
    body.append('file', attachment.file)
    const response = await api.post(`/rfqs/${rfqId.value}/attachments/`, body)
    attachments.value[index] = {
      ...response.data,
      id: response.data.id,
      name: response.data.name || response.data.file_name || attachment.name,
      uploaded: true,
    }
  }
}

async function save(send = false) {
  error.value = ''
  attachmentError.value = ''
  if (!validate()) return
  saving.value = true
  try {
    const body = {
      title: form.title.trim(),
      category: form.category,
      description: form.description,
      deadline: new Date(form.deadline).toISOString(),
      vendors: assignedVendors.value.map((vendor) => vendor.id),
      items: form.items.map(({ name, quantity, unit }) => ({ name: name.trim(), quantity, unit: unit.trim() })),
    }
    const response = rfqId.value
      ? await api.put(`/rfqs/${rfqId.value}/`, body)
      : await api.post('/rfqs/', body)
    rfqId.value = response.data.id || rfqId.value
    if (!rfqId.value) throw new Error('The saved RFQ did not include an ID.')
    await uploadAttachments()
    if (send) await api.post(`/rfqs/${rfqId.value}/publish/`)
    await router.push(`/rfqs/${rfqId.value}`)
  } catch (err) {
    fieldErrors.value = getFieldErrors(err)
    error.value = getErrorMessage(err, 'Unable to save the RFQ.')
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
        <h1>Create RFQ's</h1>
        <p class="muted">new request for quotation</p>
      </div>
    </div>

    <p v-if="error" class="form-error page-alert" role="alert">{{ error }}</p>
    <p v-if="loading" class="loading-message" role="status">Loading RFQ…</p>
    <EmptyState v-else-if="error && isEditing && !form.title" message="The RFQ could not be loaded." />
    <template v-else>
      <div class="rfq-stepper panel" aria-label="RFQ progress">
        <div v-for="(label, index) in ['Draft', 'Sent to vendors', 'Quotations received']" :key="label" class="rfq-step">
          <span class="rfq-step-number" :class="{ 'rfq-step-current': progress === index + 1, 'rfq-step-done': progress > index + 1 }">
            {{ index + 1 }}
          </span>
          <span>{{ label }}</span>
        </div>
      </div>

      <div class="rfq-form-layout">
        <div class="panel rfq-main-form">
          <div class="form-stack">
            <label class="form-field">
              <span>RFQ title *</span>
              <input v-model="form.title" type="text" :aria-invalid="Boolean(fieldErrors.title)">
              <small v-if="fieldErrors.title" class="field-error">{{ fieldErrors.title }}</small>
            </label>
            <label class="form-field">
              <span>Category</span>
              <input v-model="form.category" type="text" :aria-invalid="Boolean(fieldErrors.category)">
              <small v-if="fieldErrors.category" class="field-error">{{ fieldErrors.category }}</small>
            </label>
            <label class="form-field">
              <span>Deadline *</span>
              <input v-model="form.deadline" type="datetime-local" :aria-invalid="Boolean(fieldErrors.deadline)">
              <small v-if="fieldErrors.deadline" class="field-error">{{ fieldErrors.deadline }}</small>
            </label>
            <label class="form-field">
              <span>Description</span>
              <textarea v-model="form.description" rows="5" :aria-invalid="Boolean(fieldErrors.description)"></textarea>
              <small v-if="fieldErrors.description" class="field-error">{{ fieldErrors.description }}</small>
            </label>
          </div>

          <section class="rfq-form-section">
            <div class="panel-heading">
              <h2>Line items</h2>
              <button class="button button-small button-secondary" type="button" :disabled="!itemsEditable" @click="addItem">+ Add line item</button>
            </div>
            <p v-if="fieldErrors.items" class="field-error">{{ fieldErrors.items }}</p>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="(item, index) in form.items" :key="item.id || index">
                    <td>
                      <input v-model="item.name" type="text" aria-label="Item name" :disabled="!itemsEditable">
                      <small v-if="fieldErrors[`items.${index}.name`]" class="field-error">{{ fieldErrors[`items.${index}.name`] }}</small>
                    </td>
                    <td>
                      <input v-model="item.quantity" type="number" min="1" aria-label="Quantity" :disabled="!itemsEditable">
                      <small v-if="fieldErrors[`items.${index}.quantity`]" class="field-error">{{ fieldErrors[`items.${index}.quantity`] }}</small>
                    </td>
                    <td>
                      <input v-model="item.unit" type="text" aria-label="Unit" :disabled="!itemsEditable">
                      <small v-if="fieldErrors[`items.${index}.unit`]" class="field-error">{{ fieldErrors[`items.${index}.unit`] }}</small>
                    </td>
                    <td><button class="button button-small button-danger" type="button" :disabled="!itemsEditable" aria-label="Remove item" @click="removeItem(index)">Remove</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="rfq-form-section">
            <h2>Attachments</h2>
            <label
              class="rfq-dropzone"
              @dragover.prevent
              @drop.prevent="handleDrop"
            >
              <input
                ref="fileInput"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx"
                multiple
                @change="handleFiles"
              >
              <strong>Drop files here or click to upload</strong>
              <span>PDF, PNG, JPG, JPEG, DOCX or XLSX, up to 5 MB each</span>
            </label>
            <p v-if="attachmentError" class="field-error" role="alert">{{ attachmentError }}</p>
            <ul v-if="attachments.length" class="rfq-attachment-list">
              <li v-for="(attachment, index) in attachments" :key="attachment.id || `${attachment.name}-${index}`">
                <span>{{ attachment.name }}</span>
                <button class="button button-small button-quiet" type="button" @click="removeAttachment(index)">Remove</button>
              </li>
            </ul>
          </section>
        </div>

        <aside class="panel rfq-vendor-panel">
          <h2>ASSIGN VENDORS</h2>
          <ul v-if="assignedVendors.length" class="rfq-vendor-chips">
            <li v-for="vendor in assignedVendors" :key="vendor.id">
              <span>{{ vendor.name }}</span>
              <button type="button" :aria-label="`Remove ${vendor.name}`" @click="removeVendor(vendor.id)">×</button>
            </li>
          </ul>
          <EmptyState v-else message="No vendors assigned" />
          <label class="form-field">
            <span>Add active vendor</span>
            <select v-model="vendorChoice" @change="addVendor">
              <option value="">+ Add vendor</option>
              <option v-for="vendor in availableVendors" :key="vendor.id" :value="vendor.id">
                {{ vendor.name }}
              </option>
            </select>
          </label>
        </aside>
      </div>

      <div class="rfq-form-actions">
        <button class="button button-secondary" type="button" :disabled="saving" @click="save(false)">
          {{ saving ? 'Saving…' : 'Save as Draft' }}
        </button>
        <button class="button button-primary" type="button" :disabled="saving" @click="save(true)">
          {{ saving ? 'Saving…' : 'Save & Send to Vendors' }}
        </button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.rfq-stepper {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
  padding: 16px 20px;
}

.rfq-step {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--muted);
  font-size: 11px;
}

.rfq-step-number {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
}

.rfq-step-current,
.rfq-step-done {
  border-color: var(--green);
  background: var(--green);
  color: white;
}

.rfq-form-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(230px, 1fr);
  align-items: start;
  gap: 16px;
}

.rfq-main-form {
  display: grid;
  gap: 24px;
}

.rfq-form-section {
  display: grid;
  gap: 12px;
}

.rfq-form-section h2,
.rfq-vendor-panel h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.rfq-form-section .panel-heading {
  margin-bottom: 0;
}

.rfq-form-section td input {
  width: 100%;
  min-width: 85px;
  padding: 8px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  font-size: 11px;
}

.rfq-form-section td small {
  display: block;
  max-width: 150px;
  white-space: normal;
}

.rfq-dropzone {
  display: grid;
  min-height: 100px;
  place-content: center;
  gap: 7px;
  padding: 16px;
  border: 1px dashed var(--border-strong);
  border-radius: 12px;
  background: var(--surface-muted);
  color: var(--muted);
  cursor: pointer;
  font-size: 11px;
  text-align: center;
}

.rfq-dropzone input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.rfq-dropzone strong {
  color: var(--green-dark);
  font-size: 12px;
}

.rfq-attachment-list,
.rfq-vendor-chips {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rfq-attachment-list li,
.rfq-vendor-chips li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--text);
  font-size: 11px;
}

.rfq-vendor-panel {
  display: grid;
  gap: 16px;
}

.rfq-vendor-chips li {
  border-radius: 999px;
  background: var(--green-soft);
  color: var(--green-dark);
}

.rfq-vendor-chips button {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
}

.rfq-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

@media (max-width: 760px) {
  .rfq-form-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .rfq-stepper {
    align-items: flex-start;
    flex-direction: column;
  }

  .rfq-form-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
