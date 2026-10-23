<script setup>
import { ref } from 'vue'
import FormField from '../components/FormField.vue'
import api from '../api'
import { getErrorMessage } from '../utils/errors'

const email = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  message.value = ''
  loading.value = true
  try {
    await api.post('/auth/forgot-password/', { email: email.value })
    message.value = 'If an account exists for this email, password reset instructions have been sent.'
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <RouterLink class="auth-brand" to="/">VendorBridge</RouterLink>
      <span class="auth-mark" aria-hidden="true"></span>
      <h1>Forgot password?</h1>
      <p class="muted auth-intro">Enter your email address and we'll send reset instructions.</p>
      <form class="form-stack" @submit.prevent="submit">
        <FormField v-model="email" label="Email" type="email" autocomplete="email" required />
        <p v-if="message" class="success-message" role="status">{{ message }}</p>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button-primary button-full" type="submit" :disabled="loading">
          {{ loading ? 'Sending…' : 'Send reset link' }}
        </button>
      </form>
      <p class="auth-footer"><RouterLink to="/login">Back to login</RouterLink></p>
    </section>
  </main>
</template>
