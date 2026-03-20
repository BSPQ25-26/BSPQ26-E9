<script setup>
import { computed, ref } from 'vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import { getRecentProducts } from '@/services/product.service'

const recentProducts = ref(getRecentProducts())
const createProductRoute = {
  name: 'product-create',
  params: {
    id: 'new',
  },
}

const currencyFormatter = new Intl.NumberFormat('en-US', {
  currency: 'USD',
  style: 'currency',
})

const hasRecentProducts = computed(() => recentProducts.value.length > 0)
const recentProductsLabel = computed(() =>
  `${recentProducts.value.length} recent ${recentProducts.value.length === 1 ? 'item' : 'items'}`,
)
const primaryActionCard = computed(() =>
  hasRecentProducts.value
    ? {
        title: 'Create a new listing',
        description: 'Add the basic details and publish your item in one short form.',
        buttonLabel: 'New item',
        toneClass: 'action-card',
      }
    : {
        title: 'Your first listing starts here',
        description: 'Once you post an item, it will appear on this page.',
        buttonLabel: 'Create your first item',
        toneClass: 'empty-card',
      },
)
</script>

<template>
  <section class="page-shell">
    <div class="page-hero">
      <h1>Sell without the noise.</h1>
      <p class="muted">
        Create a listing, keep track of your recent posts, and skip the demo content.
      </p>
    </div>

    <div class="card-grid intro-grid">
      <BaseCard
        :class="['primary-action-card', primaryActionCard.toneClass]"
        :title="primaryActionCard.title"
        :description="primaryActionCard.description"
      >
        <BaseButton :to="createProductRoute" variant="secondary">
          {{ primaryActionCard.buttonLabel }}
        </BaseButton>
      </BaseCard>
    </div>

    <BaseCard
      v-if="hasRecentProducts"
      class="recent-card"
      :title="recentProductsLabel"
      description="These are the latest listings created from this browser."
    >
      <ul class="recent-products">
        <li v-for="product in recentProducts" :key="product.id || product.title" class="recent-product">
          <div class="recent-product__copy">
            <p class="recent-product__title">
              {{ product.title }}
            </p>
            <p class="muted">
              {{ product.category }} · {{ product.condition }}
            </p>
          </div>

          <div class="recent-product__meta">
            <span>{{ currencyFormatter.format(product.price) }}</span>
            <span class="recent-product__state">
              {{ product.state }}
            </span>
          </div>
        </li>
      </ul>
    </BaseCard>
  </section>
</template>

<style scoped>
.intro-grid {
  align-items: stretch;
}

.primary-action-card,
.action-card,
.recent-card,
.empty-card {
  min-height: 100%;
}

.primary-action-card :deep(.card-title),
.recent-card :deep(.card-title) {
  min-width: 0;
  text-wrap: pretty;
}

.primary-action-card :deep(.base-button) {
  width: 100%;
}

.action-card {
  background: linear-gradient(180deg, rgba(26, 26, 26, 0.96), rgba(42, 42, 42, 0.93));
  border-color: rgba(17, 17, 17, 0.9);
  color: #f7f6f2;
}

.action-card :deep(.card-title),
.action-card :deep(.muted) {
  color: #f7f6f2;
}

.action-card :deep(.muted) {
  font-size: 0.98rem;
  line-height: 1.55;
}

.recent-products {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-4);
}

.recent-product {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: 1rem 1.05rem;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 1.35rem;
  background: rgba(255, 255, 255, 0.62);
}

.recent-product:last-child {
  margin-bottom: 0;
}

.recent-product__copy,
.recent-product__meta {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
}

.recent-product__title {
  font-family: var(--font-heading);
  font-size: 1.6rem;
  font-weight: 600;
  line-height: 0.95;
  overflow-wrap: anywhere;
}

.recent-product__meta {
  justify-items: end;
  text-align: right;
  color: var(--color-text-muted);
}

.recent-product__state {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--color-text-muted);
}

@media (min-width: 768px) {
  .intro-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .primary-action-card :deep(.card-title) {
    max-width: 11ch;
    font-size: clamp(1.85rem, 9vw, 2.2rem);
    line-height: 0.98;
  }

  .recent-product {
    flex-direction: column;
    align-items: flex-start;
  }

  .recent-product__meta {
    justify-items: start;
    text-align: left;
  }

  .recent-product__title {
    font-size: 1.35rem;
  }
}
</style>
