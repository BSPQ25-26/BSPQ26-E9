<script setup>
import { RouterView } from 'vue-router'
import AppToastStack from '@/components/feedback/AppToastStack.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <div class="app-shell">
    <AppHeader />

    <main class="app-main">
      <RouterView />
    </main>

    <AppFooter />
    <AppToastStack />
  </div>
</template>
