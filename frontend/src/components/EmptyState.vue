<script setup>
defineProps({
  message: { type: String, default: 'Nothing to show yet.' },
})
</script>

<template>
  <div class="empty-state">
    <span class="empty-illustration" aria-hidden="true">
      <span></span><span></span><span></span>
    </span>
    <p>{{ message }}</p>
  </div>
</template>
