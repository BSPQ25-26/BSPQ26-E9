<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useToastStore } from '@/stores/toast'
import { createProduct } from '@/services/product.service'
import { createFieldErrors, normalizeApiFormError } from '@/utils/api-errors'

const router = useRouter()
const toastStore = useToastStore()

const initialState = () => ({
  category: '',
  condition: '',
  description: '',
  price: '',
  title: '',
})

const form = reactive(initialState())
const fieldErrors = reactive(
  createFieldErrors(['title', 'description', 'category', 'price', 'condition']),
)
const formError = ref('')
const isSubmitting = ref(false)

const setFieldValue = (field, value) => {
  form[field] = value
  fieldErrors[field] = ''
  formError.value = ''
}

const validateField = (field) => {
  const value = typeof form[field] === 'string' ? form[field].trim() : form[field]

  if (field === 'price') {
    if (value === '' || value === null || value === undefined) {
      fieldErrors.price = 'Enter a price.'
      return false
    }

    if (Number.isNaN(Number(value)) || Number(value) <= 0) {
      fieldErrors.price = 'Enter a price above 0.'
      return false
    }

    fieldErrors.price = ''
    return true
  }

  if (!value) {
    const labels = {
      title: 'item name',
      description: 'details',
      category: 'category',
      condition: 'condition',
    }

    fieldErrors[field] = `Enter the ${labels[field] || field}.`
    return false
  }

  fieldErrors[field] = ''
  return true
}

const validateForm = () =>
  ['title', 'description', 'category', 'price', 'condition'].map(validateField).every(Boolean)

const handleSubmit = async () => {
  formError.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    await createProduct({
      title: form.title.trim(),
      description: form.description.trim(),
      category: form.category.trim(),
      price: Number(form.price),
      condition: form.condition.trim(),
    })

    toastStore.success('Your item is live.')
    await router.push('/products')
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      ['title', 'description', 'category', 'price', 'condition'],
      'We could not save your item. Please try again.',
    )

    Object.assign(fieldErrors, normalizedError.fieldErrors)
    formError.value = normalizedError.formError
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="page-shell create-shell">
    <div class="page-hero">
      <h1>Create a simple listing.</h1>
      <p class="muted">
        Add the essentials below. Clear details help people decide faster.
      </p>
    </div>

    <BaseCard
      class="create-card"
      title="What are you selling?"
      description="Keep it short, clear, and factual."
    >
      <form class="responsive-form responsive-form--desktop-two" novalidate @submit.prevent="handleSubmit">
        <BaseInput
          class="form-field form-field--full"
          :model-value="form.title"
          :error="fieldErrors.title"
          label="Item name"
          name="title"
          placeholder="Wooden side table"
          required
          @blur="validateField('title')"
          @update:model-value="setFieldValue('title', $event)"
        />

        <BaseInput
          class="form-field form-field--full"
          :model-value="form.description"
          :error="fieldErrors.description"
          label="Details"
          multiline
          name="description"
          placeholder="Size, condition, and what is included."
          required
          @blur="validateField('description')"
          @update:model-value="setFieldValue('description', $event)"
        />

        <BaseInput
          class="form-field"
          :model-value="form.category"
          :error="fieldErrors.category"
          label="Category"
          name="category"
          placeholder="Furniture"
          required
          @blur="validateField('category')"
          @update:model-value="setFieldValue('category', $event)"
        />

        <BaseInput
          class="form-field"
          :model-value="form.condition"
          :error="fieldErrors.condition"
          label="Condition"
          name="condition"
          placeholder="Used, good condition"
          required
          @blur="validateField('condition')"
          @update:model-value="setFieldValue('condition', $event)"
        />

        <BaseInput
          class="form-field form-field--full"
          :model-value="form.price"
          :error="fieldErrors.price"
          label="Price"
          min="0.01"
          name="price"
          placeholder="149.99"
          required
          step="0.01"
          type="number"
          @blur="validateField('price')"
          @update:model-value="setFieldValue('price', $event)"
        />

        <p v-if="formError" class="status-message error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <BaseButton :disabled="isSubmitting" block type="submit">
            {{ isSubmitting ? 'Posting item...' : 'Post item' }}
          </BaseButton>

          <BaseButton to="/products" variant="ghost">
            Back
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </section>
</template>

<style scoped>
.create-shell {
  align-items: start;
}

.create-card {
  margin-inline: auto;
}

.create-card :deep(.card-title) {
  max-width: 11ch;
}

@media (max-width: 767px) {
  .create-shell {
    gap: 0.4rem;
  }

  .create-shell .page-hero {
    width: 100%;
    padding-top: var(--space-2);
    padding-right: 2rem;
    padding-bottom: 2.8rem;
  }

  .create-shell .page-hero h1 {
    max-width: 8ch;
  }

  .create-card {
    width: 100%;
    margin-inline: auto;
    margin-top: -1.85rem;
    transform: none;
    position: relative;
    z-index: 1;
  }
}
</style>
