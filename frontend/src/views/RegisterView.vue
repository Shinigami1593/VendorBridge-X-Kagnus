<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import FormField from '../components/FormField.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage, getFieldErrors } from '../utils/errors'

const auth = useAuth()
const router = useRouter()
const form = ref({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  role: 'officer',
  country: '',
  info: '',
  password: '',
})
const photo = ref(null)
const photoName = ref('')
const errors = ref({})
const error = ref('')
const loading = ref(false)

function choosePhoto(event) {
  photo.value = event.target.files?.[0] || null
  photoName.value = photo.value?.name || ''
}

async function submit() {
  errors.value = {}
  error.value = ''
  loading.value = true
  const data = new FormData()
  Object.entries(form.value).forEach(([key, value]) => data.append(key, value))
  if (photo.value) data.append('photo', photo.value)
  try {
    await auth.register(data)
    await router.replace('/')
  } catch (err) {
    errors.value = getFieldErrors(err)
    error.value = getErrorMessage(err, 'Please review the form and try again.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page register-page">
    <section class="auth-card register-card">
      <RouterLink class="auth-brand" to="/">VendorBridge</RouterLink>
      <span class="auth-mark" aria-hidden="true"></span>
      <h1>Create your account</h1>
      <p class="muted auth-intro">Join the VendorBridge procurement network</p>
      <form class="form-stack" @submit.prevent="submit">
        <label class="photo-picker">
          <span class="photo-circle" aria-hidden="true">{{ photoName ? '✓' : '+' }}</span>
          <span>{{ photoName || 'Upload a profile photo' }}</span>
          <input type="file" accept="image/*" @change="choosePhoto">
        </label>
        <small v-if="errors.photo" class="field-error centered-error">{{ errors.photo }}</small>
        <div class="form-grid">
          <FormField v-model="form.first_name" label="First name" autocomplete="given-name" :error="errors.first_name" required />
          <FormField v-model="form.last_name" label="Last name" autocomplete="family-name" :error="errors.last_name" required />
          <FormField v-model="form.email" label="Email address" type="email" autocomplete="email" :error="errors.email" required />
          <FormField v-model="form.phone" label="Phone number" type="tel" autocomplete="tel" :error="errors.phone" required />
          <label class="form-field">
            <span>Role</span>
            <select v-model="form.role" :aria-invalid="Boolean(errors.role)" required>
              <option value="officer">Procurement Officer</option>
              <option value="manager">Manager/Approver</option>
              <option value="vendor">Vendor</option>
            </select>
            <small v-if="errors.role" class="field-error">{{ errors.role }}</small>
          </label>
          <FormField v-model="form.country" label="Country" autocomplete="country-name" :error="errors.country" required />
        </div>
        <label class="form-field">
          <span>Additional information</span>
          <textarea v-model="form.info" rows="3" :aria-invalid="Boolean(errors.info)"></textarea>
          <small v-if="errors.info" class="field-error">{{ errors.info }}</small>
        </label>
        <FormField v-model="form.password" label="Password" type="password" autocomplete="new-password" :error="errors.password" required />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button-primary button-full" type="submit" :disabled="loading">
          {{ loading ? 'Creating account…' : 'Register' }}
        </button>
      </form>
      <p class="auth-footer">Already have an account? <RouterLink to="/login">Login</RouterLink></p>
    </section>
  </main>
</template>
