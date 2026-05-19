<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  emptyLabel: {
    type: String,
    default: '',
  },
  max: {
    type: Number,
    default: 5,
  },
  showValue: {
    type: Boolean,
    default: true,
  },
  size: {
    type: String,
    default: 'md',
  },
  value: {
    type: [Number, String],
    default: null,
  },
})

const { t } = useI18n()

const normalizedValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') {
    return null
  }

  const numberValue = Number(props.value)

  if (!Number.isFinite(numberValue)) {
    return null
  }

  return Math.min(Math.max(numberValue, 0), props.max)
})
const hasRating = computed(() => normalizedValue.value !== null)
const filledStars = computed(() => (hasRating.value ? Math.round(normalizedValue.value) : 0))
const stars = computed(() => Array.from({ length: props.max }, (_entry, index) => index + 1))
const formattedValue = computed(() => {
  if (!hasRating.value) {
    return props.emptyLabel || t('rating.noRatings')
  }

  return normalizedValue.value.toFixed(normalizedValue.value % 1 === 0 ? 0 : 1)
})
const ariaLabel = computed(() => {
  if (!hasRating.value) {
    return props.emptyLabel || t('rating.noRatings')
  }

  return t('rating.ariaValue', {
    max: props.max,
    value: formattedValue.value,
  })
})
</script>

<template>
  <span
    class="star-rating"
    :class="[`star-rating--${size}`, { 'star-rating--empty': !hasRating }]"
    role="img"
    :aria-label="ariaLabel"
  >
    <span class="star-rating__stars" aria-hidden="true">
      <span
        v-for="star in stars"
        :key="star"
        class="star-rating__star"
        :class="{ 'is-filled': star <= filledStars }"
      >
        {{ star <= filledStars ? '★' : '☆' }}
      </span>
    </span>
    <span v-if="showValue" class="star-rating__value">
      {{ formattedValue }}
    </span>
  </span>
</template>

<style scoped>
.star-rating {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.45rem;
  color: #775920;
  font-weight: 800;
  line-height: 1.2;
}

.star-rating__stars {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 0.08rem;
  letter-spacing: 0;
}

.star-rating__star {
  color: #c8bba5;
}

.star-rating__star.is-filled {
  color: #a66c00;
}

.star-rating__value {
  min-width: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  overflow-wrap: anywhere;
}

.star-rating--sm {
  gap: 0.35rem;
  font-size: 0.92rem;
}

.star-rating--md {
  font-size: 1rem;
}

.star-rating--lg {
  gap: 0.55rem;
  font-size: 1.2rem;
}

.star-rating--empty {
  color: var(--color-text-muted);
}

.star-rating--empty .star-rating__star {
  color: #cfc9bf;
}
</style>
