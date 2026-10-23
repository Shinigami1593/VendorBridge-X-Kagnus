<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
})
const emit = defineEmits(['close'])

function closeOnEscape(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', closeOnEscape))
onUnmounted(() => window.removeEventListener('keydown', closeOnEscape))
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true" :aria-label="props.title">
      <header class="modal-header">
        <h2>{{ props.title }}</h2>
        <button class="icon-button" type="button" aria-label="Close" @click="emit('close')">×</button>
      </header>
      <div class="modal-content"><slot /></div>
      <footer v-if="$slots.footer" class="modal-footer"><slot name="footer" /></footer>
    </section>
  </div>
</template>
