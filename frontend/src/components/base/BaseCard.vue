<script setup>
defineProps({
  description: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <article class="base-card">
    <header v-if="title || description" class="card-header">
      <h2 v-if="title" class="card-title">
        {{ title }}
      </h2>

      <p v-if="description" class="muted">
        {{ description }}
      </p>
    </header>

    <div class="card-content">
      <slot />
    </div>
  </article>
</template>

<style scoped>
.base-card {
  position: relative;
  display: grid;
  gap: var(--space-5);
  min-width: 0;
  padding: clamp(1.4rem, 3vw, 1.8rem);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 247, 243, 0.9));
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(24px);
  overflow: hidden;
  isolation: isolate;
}

.card-header {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  position: relative;
  z-index: 1;
}

.card-title {
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 0.92;
  overflow-wrap: anywhere;
}

.card-content {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  position: relative;
  z-index: 1;
}

@media (max-width: 767px) {
  .base-card {
    gap: var(--space-4);
    padding: 1.15rem;
    border-radius: 1.6rem;
  }

  .card-title {
    font-size: clamp(1.65rem, 8.8vw, 2.1rem);
    line-height: 0.96;
  }
}
</style>
