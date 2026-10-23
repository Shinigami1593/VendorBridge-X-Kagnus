<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FormField from '../components/FormField.vue'
import api from '../api'
import { getErrorMessage } from '../utils/errors'

const route = useRoute()
const router = useRouter()
const password = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  message.value = ''
  loading.value = true
  try {
    await api.post('/auth/reset-password/', {
      uid: route.params.uid,
      token: route.params.token,
      password: password.value,
    })
    message.value = 'Your password has been updated.'
    await router.replace('/login')
  } catch (err) {
    error.value = getErrorMessage(err, 'The reset link may be invalid or expired.')
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
      <h1>Set a new password</h1>
      <p class="muted auth-intro">Choose a new password for your account.</p>
      <form class="form-stack" @submit.prevent="submit">
        <FormField v-model="password" label="New password" type="password" autocomplete="new-password" required />
        <p v-if="message" class="success-message" role="status">{{ message }}</p>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button-primary button-full" type="submit" :disabled="loading">
          {{ loading ? 'Updating…' : 'Reset password' }}
        </button>
      </form>
      <p class="auth-footer"><RouterLink to="/login">Back to login</RouterLink></p>
    </section>
  </main>
</template>
