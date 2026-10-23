<script setup>
import { useRoute } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'

const route = useRoute()
</script>

<template>
  <section class="page">
    <div class="page-heading">
      <div>
        <h1>{{ route.meta.title }}</h1>
        <p class="muted">This section is part of your procurement workspace.</p>
      </div>
    </div>
    <div class="panel coming-soon-panel">
      <EmptyState message="This module is coming in a later week" />
    </div>
  </section>
</template>
