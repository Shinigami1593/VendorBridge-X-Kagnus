<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const labels = {
  pending_payment: 'Pending Payment',
  in_review: 'In Review',
  partially_fulfilled: 'Partially Fulfilled',
}
const normalized = computed(() => String(props.status).trim().toLowerCase().replace(/[\s-]+/g, '_'))
const label = computed(() => labels[normalized.value] || normalized.value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()))
const statusClass = computed(() => `status-${normalized.value.replaceAll('_', '-')}`)
</script>

<template>
  <span class="status-badge" :class="statusClass">{{ label }}</span>
</template>
