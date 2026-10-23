<script setup>
import { ArrowUpRight } from 'lucide-vue-next'

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  caption: { type: String, default: 'Current period' },
  featured: { type: Boolean, default: false },
})
</script>

<template>
  <article class="summary-card" :class="{ 'summary-featured': featured }">
    <div class="summary-card-top">
      <span class="summary-label">{{ label }}</span>
      <span class="summary-arrow" aria-hidden="true"><ArrowUpRight :size="15" /></span>
    </div>
    <span class="summary-value">{{ value }}</span>
    <span class="summary-caption">{{ caption }}</span>
  </article>
</template>
