import { defineStore } from 'pinia'
import api from '../api'

export const useAuth = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    role: (state) => (state.user ? state.user.role : ''),
  },

  actions: {
    save(data) {
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },

    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    async login(email, password) {
      const res = await api.post('/auth/login/', { email, password })
      this.save(res.data)
    },

    async register(formData) {
      const res = await api.post('/auth/register/', formData)
      this.save(res.data)
    },

    async logout() {
      try {
        await api.post('/auth/logout/')
      } finally {
        this.clear()
      }
    },
  },
})