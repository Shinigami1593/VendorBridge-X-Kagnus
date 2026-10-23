<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FormField from '../components/FormField.vue'
import { useAuth } from '../stores/auth'
import { getErrorMessage } from '../utils/errors'

const auth = useAuth()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    await router.replace('/')
  } catch (err) {
    error.value = getErrorMessage(err, 'Email or password is incorrect.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card login-card">
      <RouterLink class="auth-brand" to="/">VendorBridge</RouterLink>
      <span class="auth-mark" aria-hidden="true"></span>
      <h1>Welcome back</h1>
      <p class="muted auth-intro">Sign in to your account</p>
      <p v-if="route.query.notice" class="success-message logout-notice" role="status">{{ route.query.notice }}</p>
      <form class="form-stack" @submit.prevent="submit">
        <FormField v-model="email" label="Email" type="email" autocomplete="email" required />
        <FormField v-model="password" label="Password" type="password" autocomplete="current-password" required />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button button-primary button-full" type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Login' }}
        </button>
      </form>
      <div class="auth-links">
        <RouterLink to="/forgot-password">Forgot password?</RouterLink>
        <span>New to VendorBridge? <RouterLink to="/register">Create an account</RouterLink></span>
      </div>
    </section>
  </main>
</template>
