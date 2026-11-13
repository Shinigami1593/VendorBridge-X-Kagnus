import { defineStore } from 'pinia'
import api from '../api'

export const useNotifications = defineStore('notifications', {
  state: () => ({
    unreadCount: 0,
    items: [],
  }),

  actions: {
    async fetchUnreadCount() {
      const response = await api.get('/notifications/unread-count/')
      this.unreadCount = Number(response.data.count) || 0
      return this.unreadCount
    },

    async fetchLatest() {
      const response = await api.get('/notifications/', {
        params: { page: 1, page_size: 5 },
      })
      this.items = response.data.results || []
      return this.items
    },

    async markRead(id) {
      const response = await api.post(`/notifications/${id}/read/`)
      const index = this.items.findIndex((item) => item.id === id)
      if (index !== -1) this.items[index] = response.data
      await this.fetchUnreadCount()
      return response.data
    },

    async markAllRead() {
      await api.post('/notifications/read-all/')
      this.items = this.items.map((item) => ({ ...item, is_read: true }))
      this.unreadCount = 0
    },
  },
})
