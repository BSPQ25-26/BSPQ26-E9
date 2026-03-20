<script setup>
const appName = import.meta.env.VITE_APP_NAME || 'Wallabot'
</script>

<template>
  <footer class="app-footer">
    {{ appName }} TM
  </footer>
</template>

<style scoped>
.app-footer {
  padding: 0 0 var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
  font-size: 1rem;
  font-weight: 600;
}
</style>
