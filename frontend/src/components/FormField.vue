<script setup>
defineProps({
  label: { type: String, required: true },
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  error: { type: String, default: '' },
  autocomplete: { type: String, default: undefined },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <label class="form-field">
    <span>{{ label }}</span>
    <input
      :type="type"
      :value="modelValue"
      :autocomplete="autocomplete"
      :aria-invalid="Boolean(error)"
      @input="$emit('update:modelValue', $event.target.value)"
      v-bind="$attrs"
    >
    <small v-if="error" class="field-error">{{ error }}</small>
  </label>
</template>
