<script setup>
import { computed, ref } from 'vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'

defineProps({
  error: {
    type: String,
    default: '',
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
  sellerName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'submit'])

const stars = ref(0)
const reviewText = ref('')
const starOptions = [1, 2, 3, 4, 5]
const canSubmit = computed(() => stars.value >= 1)

const selectStars = (value) => {
  stars.value = value
}

const submitRating = () => {
  if (!canSubmit.value) {
    return
  }

  emit('submit', {
    reviewText: reviewText.value,
    stars: stars.value,
  })
}
</script>

<template>
  <div class="dialog-backdrop rating-backdrop" @click.self="emit('close')">
    <section
      class="rating-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="rating-dialog-title"
      aria-describedby="rating-dialog-description"
    >
      <div class="rating-dialog__copy">
        <p class="dialog-eyebrow">
          {{ $t('ratingModal.eyebrow') }}
        </p>
        <h2 id="rating-dialog-title">
          {{ $t('ratingModal.title') }}
        </h2>
        <p id="rating-dialog-description" class="muted">
          {{ $t('ratingModal.description', { seller: sellerName || $t('detail.unknownSeller') }) }}
        </p>
      </div>

      <fieldset class="star-selector">
        <legend>{{ $t('ratingModal.starsLabel') }}</legend>
        <div class="star-selector__buttons">
          <button
            v-for="star in starOptions"
            :key="star"
            class="star-selector__button"
            :class="{ 'is-selected': star <= stars }"
            type="button"
            :aria-label="$t('ratingModal.starAria', { count: star })"
            @click="selectStars(star)"
          >
            {{ star <= stars ? '★' : '☆' }}
          </button>
        </div>
      </fieldset>

      <BaseInput
        v-model="reviewText"
        :disabled="isSubmitting"
        :label="$t('ratingModal.reviewLabel')"
        multiline
        name="review_text"
        :placeholder="$t('ratingModal.reviewPlaceholder')"
        :rows="4"
      />

      <p v-if="error" class="status-message error">
        {{ error }}
      </p>

      <div class="dialog-actions">
        <BaseButton
          :disabled="isSubmitting"
          type="button"
          variant="secondary"
          @click="emit('close')"
        >
          {{ $t('ratingModal.skip') }}
        </BaseButton>
        <BaseButton
          :disabled="isSubmitting || !canSubmit"
          type="button"
          @click="submitRating"
        >
          {{ isSubmitting ? $t('ratingModal.submitting') : $t('ratingModal.submit') }}
        </BaseButton>
      </div>
    </section>
  </div>
</template>

<style scoped>
.rating-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(17, 17, 17, 0.42);
}

.rating-dialog {
  display: grid;
  width: min(100%, 30rem);
  gap: var(--space-5);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  box-shadow: var(--shadow-lg);
}

.rating-dialog__copy {
  display: grid;
  gap: var(--space-3);
}

.dialog-eyebrow {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
}

.rating-dialog h2 {
  font-size: 2rem;
  line-height: 1;
  letter-spacing: 0;
}

.star-selector {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.star-selector legend {
  padding: 0;
  color: var(--color-text);
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
}

.star-selector__buttons {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.star-selector__button {
  display: grid;
  place-items: center;
  width: var(--tap-target-size);
  aspect-ratio: 1;
  border: 1px solid rgba(119, 89, 32, 0.22);
  border-radius: 0.5rem;
  background: #fffaf0;
  color: #775920;
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.star-selector__button:hover,
.star-selector__button.is-selected {
  border-color: rgba(166, 108, 0, 0.42);
  background: #f7ead1;
  transform: translateY(-1px);
}

.dialog-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-3);
}
</style>
