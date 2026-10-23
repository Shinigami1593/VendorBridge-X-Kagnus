<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const statusClass = computed(() => `status-${props.status.toLowerCase()}`)
</script>

<template>
  <span class="status-badge" :class="statusClass">{{ status }}</span>
</template>
