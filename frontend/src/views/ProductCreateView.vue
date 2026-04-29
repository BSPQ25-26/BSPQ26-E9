<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useToastStore } from '@/stores/toast'
import {
  createProduct,
  deleteProduct,
  getProductById,
  updateProduct,
  uploadProductImage,
} from '@/services/product.service'
import { recommendProductPrice, suggestProductCategory } from '@/services/wallabot.service'
import { createFieldErrors, normalizeApiFormError } from '@/utils/api-errors'

const PRODUCT_FIELDS = ['title', 'description', 'category', 'price', 'condition']
const PRICE_RECOMMENDATION_FIELDS = ['title', 'description', 'condition']
const CATEGORY_OPTIONS = [
  'Books',
  'Books & Media',
  'Clothing & Accessories',
  'Collectibles',
  'Collectibles & Art',
  'Electronics',
  'Furniture',
  'Health & Beauty',
  'Home',
  'Home & Garden',
  'Sports & Outdoors',
  'Toys & Games',
  'Vehicles',
  'Other',
]
const CONDITION_OPTIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor']
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png']
const MAX_IMAGE_SIZE = 5 * 1024 * 1024
const MAX_PRODUCT_IMAGES = 8

const route = useRoute()
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
const fieldErrors = reactive(createFieldErrors(PRODUCT_FIELDS))
const formError = ref('')
const imageError = ref('')
const existingImageCount = ref(0)
const selectedImages = ref([])
const isDraggingImages = ref(false)
const isDeleting = ref(false)
const isLoadingProduct = ref(false)
const isRecommendingPrice = ref(false)
const isSuggestingCategory = ref(false)
const isSubmitting = ref(false)
const categorySuggestionContext = ref('')
const priceRecommendation = ref(null)
const imageInputAccept = ACCEPTED_IMAGE_TYPES.join(',')
const productId = computed(() => String(route.params.id || 'new'))
const isEditMode = computed(() => route.name === 'product-edit')
const selectedImageTotal = computed(() => existingImageCount.value + selectedImages.value.length)
const selectedImageCountLabel = computed(
  () => `${selectedImageTotal.value}/${MAX_PRODUCT_IMAGES} images`,
)
const heroTitle = computed(() =>
  isEditMode.value ? 'Edit this listing.' : 'Create a simple listing.',
)
const heroDescription = computed(() =>
  isEditMode.value
    ? 'Update the details buyers see before they decide.'
    : 'Add the essentials below. Clear details help people decide faster.',
)
const cardTitle = computed(() => (isEditMode.value ? 'Listing details' : 'What are you selling?'))
const cardDescription = computed(() =>
  isEditMode.value ? 'Keep the item accurate and current.' : 'Keep it short, clear, and factual.',
)
const submitLabel = computed(() => {
  if (isSubmitting.value) {
    return isEditMode.value ? 'Saving item...' : 'Posting item...'
  }

  return isEditMode.value ? 'Save changes' : 'Post item'
})
const categorySuggestionLabel = computed(() =>
  isSuggestingCategory.value ? 'Suggesting...' : 'Suggest with Wallabot',
)
const deleteLabel = computed(() => (isDeleting.value ? 'Deleting product...' : 'Delete product'))
const categoryOptions = computed(() => {
  const options = new Map()

  ;[...CATEGORY_OPTIONS, form.category].forEach((category) => {
    const label = String(category || '').trim()

    if (!label) {
      return
    }

    const key = label.toLowerCase()

    if (!options.has(key)) {
      options.set(key, label)
    }
  })

  return Array.from(options.values())
})
const priceFormatter = new Intl.NumberFormat('en-US', {
  currency: 'EUR',
  style: 'currency',
})
const hasPriceRecommendationRange = computed(() => {
  const min = priceRecommendation.value?.priceRangeMin
  const max = priceRecommendation.value?.priceRangeMax

  return Number.isFinite(min) && Number.isFinite(max) && min > 0 && max > 0
})
const priceRecommendationHelper = computed(() => {
  if (isRecommendingPrice.value) {
    return 'Checking recommended price range...'
  }

  if (!hasPriceRecommendationRange.value) {
    return ''
  }

  return `Recommended range: ${priceFormatter.format(
    priceRecommendation.value.priceRangeMin,
  )} - ${priceFormatter.format(priceRecommendation.value.priceRangeMax)}`
})
const backRoute = computed(() =>
  isEditMode.value
    ? {
        name: 'product-detail',
        params: {
          id: productId.value,
        },
      }
    : '/products',
)

let activePriceRecommendationRequestId = 0

const clearPriceRecommendation = () => {
  activePriceRecommendationRequestId += 1
  isRecommendingPrice.value = false
  priceRecommendation.value = null
}

const getPriceRecommendationPayload = () => ({
  condition: form.condition.trim(),
  description: form.description.trim(),
  title: form.title.trim(),
})

const getCategorySuggestionContext = () => `${form.title.trim()}\n${form.description.trim()}`
const hasPriceRecommendationInputs = (payload) =>
  Boolean(payload.title && payload.description && payload.condition)

const createPreviewUrl = (file) => {
  if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') {
    return ''
  }

  return URL.createObjectURL(file)
}

const revokePreviewUrl = (previewUrl) => {
  if (previewUrl && typeof URL !== 'undefined' && typeof URL.revokeObjectURL === 'function') {
    URL.revokeObjectURL(previewUrl)
  }
}

const clearSelectedImages = () => {
  selectedImages.value.forEach((image) => revokePreviewUrl(image.previewUrl))
  selectedImages.value = []
}

const formatFileSize = (size) => {
  if (!Number.isFinite(size)) {
    return ''
  }

  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

const createImageEntry = (file) => ({
  file,
  id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
  name: file.name || 'Product image',
  previewUrl: createPreviewUrl(file),
  size: file.size,
})

const getRemainingImageSlots = () =>
  Math.max(0, MAX_PRODUCT_IMAGES - existingImageCount.value - selectedImages.value.length)

const validateImageFile = (file) => {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    imageError.value = 'Upload JPEG or PNG images.'
    return false
  }

  if (file.size > MAX_IMAGE_SIZE) {
    imageError.value = 'Each image must be 5 MB or less.'
    return false
  }

  return true
}

const addImageFiles = (fileList) => {
  const files = Array.from(fileList || [])

  if (!files.length) {
    return
  }

  imageError.value = ''
  formError.value = ''

  const remainingSlots = getRemainingImageSlots()

  if (remainingSlots <= 0) {
    imageError.value = `You can add up to ${MAX_PRODUCT_IMAGES} images.`
    return
  }

  const acceptedFiles = []

  files.some((file) => {
    if (acceptedFiles.length >= remainingSlots) {
      imageError.value = `You can add up to ${MAX_PRODUCT_IMAGES} images.`
      return true
    }

    if (validateImageFile(file)) {
      acceptedFiles.push(file)
    }

    return false
  })

  if (acceptedFiles.length) {
    selectedImages.value = [
      ...selectedImages.value,
      ...acceptedFiles.map(createImageEntry),
    ]
  }
}

const removeSelectedImage = (imageId) => {
  const image = selectedImages.value.find((entry) => entry.id === imageId)

  revokePreviewUrl(image?.previewUrl)
  selectedImages.value = selectedImages.value.filter((entry) => entry.id !== imageId)
  imageError.value = ''
}

const handleImageInputChange = (event) => {
  addImageFiles(event.target.files)
  event.target.value = ''
}

const handleImageDragEnter = () => {
  isDraggingImages.value = true
}

const handleImageDragLeave = () => {
  isDraggingImages.value = false
}

const handleImageDrop = (event) => {
  isDraggingImages.value = false
  addImageFiles(event.dataTransfer?.files)
}

const uploadSelectedImages = async (savedProduct, savedProductId) => {
  if (!selectedImages.value.length) {
    return
  }

  if (!savedProductId) {
    throw new Error('We could not upload images for this item.')
  }

  try {
    const uploadCount = selectedImages.value.length

    await Promise.all(
      selectedImages.value.map((image) => uploadProductImage(savedProductId, image.file)),
    )
    clearSelectedImages()
    existingImageCount.value = Math.min(
      MAX_PRODUCT_IMAGES,
      (savedProduct?.images?.length || existingImageCount.value) + uploadCount,
    )
  } catch (error) {
    imageError.value =
      error?.response?.data?.detail || 'Your item was saved, but the images did not upload.'
    throw error
  }
}

const resetForm = () => {
  Object.assign(form, initialState())
  Object.assign(fieldErrors, createFieldErrors(PRODUCT_FIELDS))
  clearSelectedImages()
  clearPriceRecommendation()
  categorySuggestionContext.value = ''
  existingImageCount.value = 0
  imageError.value = ''
  isDraggingImages.value = false
  formError.value = ''
}

const populateForm = (product) => {
  clearSelectedImages()
  clearPriceRecommendation()
  categorySuggestionContext.value = ''
  existingImageCount.value = Array.isArray(product?.images) ? product.images.length : 0
  imageError.value = ''

  Object.assign(form, {
    category: product?.category || '',
    condition: product?.condition || '',
    description: product?.description || '',
    price: product?.price ? String(product.price) : '',
    title: product?.title || '',
  })
}

const loadProductForEdit = async () => {
  if (!isEditMode.value) {
    resetForm()
    return
  }

  isLoadingProduct.value = true
  formError.value = ''

  try {
    const product = await getProductById(productId.value)
    populateForm(product)
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      PRODUCT_FIELDS,
      'We could not load this item. Please try again.',
    )

    formError.value = normalizedError.formError
  } finally {
    isLoadingProduct.value = false
  }
}

watch(() => [route.name, route.params.id], loadProductForEdit, { immediate: true })

onBeforeUnmount(clearSelectedImages)

const setFieldValue = (field, value) => {
  form[field] = value
  fieldErrors[field] = ''
  formError.value = ''

  if (PRICE_RECOMMENDATION_FIELDS.includes(field)) {
    clearPriceRecommendation()
  }

  if (field === 'title' || field === 'description') {
    categorySuggestionContext.value = ''
  }

  if (
    field === 'condition' &&
    categorySuggestionContext.value &&
    categorySuggestionContext.value === getCategorySuggestionContext()
  ) {
    void handleRecommendPrice()
  }
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
  PRODUCT_FIELDS.map(validateField).every(Boolean)

const validateImages = () => {
  if (selectedImageTotal.value > MAX_PRODUCT_IMAGES) {
    imageError.value = `You can add up to ${MAX_PRODUCT_IMAGES} images.`
    return false
  }

  return !imageError.value
}

const validateCategorySuggestionInputs = () =>
  ['title', 'description'].map(validateField).every(Boolean)

const handleRecommendPrice = async () => {
  const payload = getPriceRecommendationPayload()

  if (!hasPriceRecommendationInputs(payload)) {
    clearPriceRecommendation()
    return
  }

  const requestId = ++activePriceRecommendationRequestId

  priceRecommendation.value = null
  isRecommendingPrice.value = true

  try {
    const recommendation = await recommendProductPrice(payload)

    if (requestId === activePriceRecommendationRequestId) {
      priceRecommendation.value = recommendation
    }
  } catch {
    if (requestId === activePriceRecommendationRequestId) {
      priceRecommendation.value = null
    }
  } finally {
    if (requestId === activePriceRecommendationRequestId) {
      isRecommendingPrice.value = false
    }
  }
}

const handleSuggestCategory = async () => {
  formError.value = ''

  if (!validateCategorySuggestionInputs()) {
    return
  }

  isSuggestingCategory.value = true

  try {
    const suggestion = await suggestProductCategory({
      availableCategories: categoryOptions.value,
      description: form.description.trim(),
      title: form.title.trim(),
    })
    const suggestedCategory = suggestion?.suggestedCategory?.trim()

    if (!suggestedCategory) {
      fieldErrors.category = 'Wallabot did not return a category. Please enter one.'
      return
    }

    setFieldValue('category', suggestedCategory)
    categorySuggestionContext.value = getCategorySuggestionContext()
    void handleRecommendPrice()
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      PRODUCT_FIELDS,
      'Wallabot could not suggest a category. Please try again.',
    )

    Object.entries(normalizedError.fieldErrors).forEach(([field, message]) => {
      if (message) {
        fieldErrors[field] = message
      }
    })
    formError.value = normalizedError.formError
  } finally {
    isSuggestingCategory.value = false
  }
}

const handleDeleteProduct = async () => {
  if (!isEditMode.value || isDeleting.value || isLoadingProduct.value || isSubmitting.value) {
    return
  }

  const confirmed =
    typeof window === 'undefined' ||
    window.confirm('Delete this product? This action cannot be undone.')

  if (!confirmed) {
    return
  }

  isDeleting.value = true
  formError.value = ''

  try {
    await deleteProduct(productId.value)
    toastStore.success('Your item was deleted.')
    await router.push('/products')
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      PRODUCT_FIELDS,
      'We could not delete your item. Please try again.',
    )

    formError.value = normalizedError.formError
  } finally {
    isDeleting.value = false
  }
}

const handleSubmit = async () => {
  if (isDeleting.value || isSubmitting.value) {
    return
  }

  formError.value = ''

  if (!validateForm() || !validateImages()) {
    return
  }

  isSubmitting.value = true
  let savedProduct = null

  try {
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      category: form.category.trim(),
      price: Number(form.price),
      condition: form.condition.trim(),
    }
    savedProduct = isEditMode.value
      ? await updateProduct(productId.value, payload)
      : await createProduct(payload)
    const savedProductId = savedProduct?.id || (isEditMode.value ? productId.value : '')

    await uploadSelectedImages(savedProduct, savedProductId)

    toastStore.success(isEditMode.value ? 'Your item was updated.' : 'Your item is live.')
    await router.push(
      isEditMode.value
        ? {
            name: 'product-detail',
            params: {
              id: savedProduct?.id || productId.value,
            },
          }
        : '/products',
    )
  } catch (error) {
    if (savedProduct && imageError.value) {
      toastStore.error(imageError.value)
      await router.push({
        name: 'product-detail',
        params: {
          id: savedProduct?.id || productId.value,
        },
      })
      return
    }

    const normalizedError = normalizeApiFormError(
      error,
      PRODUCT_FIELDS,
      'We could not save your item. Please try again.',
    )

    Object.assign(fieldErrors, normalizedError.fieldErrors)
    formError.value = imageError.value || normalizedError.formError
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="page-shell create-shell">
    <div class="page-hero">
      <h1>{{ heroTitle }}</h1>
      <p class="muted">
        {{ heroDescription }}
      </p>
    </div>

    <BaseCard
      class="create-card"
      :title="cardTitle"
      :description="cardDescription"
    >
      <form class="responsive-form responsive-form--desktop-two" novalidate @submit.prevent="handleSubmit">
        <p v-if="isLoadingProduct" class="status-message">
          Loading item details...
        </p>

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

        <div class="form-field form-field--full image-field">
          <div class="image-field__header">
            <span class="input-label">
              Images
            </span>
            <span class="image-field__count">
              {{ selectedImageCountLabel }}
            </span>
          </div>

          <label
            class="image-dropzone"
            :class="{ 'has-error': imageError, 'is-dragging': isDraggingImages }"
            for="product-images"
            @dragenter.prevent="handleImageDragEnter"
            @dragover.prevent="handleImageDragEnter"
            @dragleave.prevent="handleImageDragLeave"
            @drop.prevent="handleImageDrop"
          >
            <input
              id="product-images"
              :accept="imageInputAccept"
              class="image-input"
              multiple
              name="images"
              type="file"
              @change="handleImageInputChange"
            />
            <span class="image-dropzone__title">
              Drop images here or choose files
            </span>
            <span class="image-dropzone__meta">
              JPEG or PNG, 5 MB max
            </span>
          </label>

          <p v-if="imageError" class="input-error">
            {{ imageError }}
          </p>

          <p v-else-if="existingImageCount" class="form-hint">
            {{ existingImageCount }} existing image{{ existingImageCount === 1 ? '' : 's' }} attached.
          </p>

          <ul v-if="selectedImages.length" class="image-preview-list" aria-label="Selected images">
            <li v-for="image in selectedImages" :key="image.id" class="image-preview">
              <img
                v-if="image.previewUrl"
                :alt="`${image.name} preview`"
                class="image-preview__thumb"
                :src="image.previewUrl"
              />
              <span v-else class="image-preview__thumb image-preview__thumb--fallback">
                {{ image.name.trim().charAt(0).toUpperCase() || '?' }}
              </span>

              <span class="image-preview__copy">
                <span class="image-preview__name">
                  {{ image.name }}
                </span>
                <span class="image-preview__size">
                  {{ formatFileSize(image.size) }}
                </span>
              </span>

              <button
                class="image-preview__remove"
                type="button"
                :aria-label="`Remove ${image.name}`"
                @click="removeSelectedImage(image.id)"
              >
                Remove
              </button>
            </li>
          </ul>
        </div>

        <div class="form-field category-suggestion-field">
          <label class="select-wrapper" :class="{ 'has-error': fieldErrors.category }" for="category">
            <span class="input-label">
              Category
            </span>
            <select
              id="category"
              :aria-describedby="fieldErrors.category ? 'category-error' : undefined"
              :aria-invalid="fieldErrors.category ? 'true' : 'false'"
              class="select-control"
              name="category"
              required
              :value="form.category"
              @blur="validateField('category')"
              @change="setFieldValue('category', $event.target.value)"
            >
              <option disabled value="">
                Select category
              </option>
              <option v-for="category in categoryOptions" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <span v-if="fieldErrors.category" id="category-error" class="input-error">
              {{ fieldErrors.category }}
            </span>
          </label>

          <BaseButton
            class="category-suggestion-button"
            :disabled="isLoadingProduct || isDeleting || isSubmitting || isSuggestingCategory"
            type="button"
            variant="secondary"
            @click="handleSuggestCategory"
          >
            <span v-if="isSuggestingCategory" aria-hidden="true" class="button-spinner" />
            <span>{{ categorySuggestionLabel }}</span>
          </BaseButton>
        </div>

        <label class="form-field select-wrapper" :class="{ 'has-error': fieldErrors.condition }" for="condition">
          <span class="input-label">
            Condition
          </span>
          <select
            id="condition"
            :aria-describedby="fieldErrors.condition ? 'condition-error' : undefined"
            :aria-invalid="fieldErrors.condition ? 'true' : 'false'"
            class="select-control"
            name="condition"
            required
            :value="form.condition"
            @blur="validateField('condition')"
            @change="setFieldValue('condition', $event.target.value)"
          >
            <option disabled value="">
              Select condition
            </option>
            <option v-for="condition in CONDITION_OPTIONS" :key="condition" :value="condition">
              {{ condition }}
            </option>
          </select>
          <span v-if="fieldErrors.condition" id="condition-error" class="input-error">
            {{ fieldErrors.condition }}
          </span>
        </label>

        <div class="form-field form-field--full price-recommendation-field">
          <BaseInput
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

          <p
            v-if="priceRecommendationHelper"
            class="form-hint price-recommendation-helper"
            data-test="price-recommendation-helper"
          >
            {{ priceRecommendationHelper }}
          </p>
        </div>

        <p v-if="formError" class="status-message error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <BaseButton
            :disabled="isLoadingProduct || isDeleting || isSubmitting || isSuggestingCategory"
            block
            type="submit"
          >
            {{ submitLabel }}
          </BaseButton>

          <BaseButton
            v-if="isEditMode"
            class="delete-product-button"
            :disabled="isLoadingProduct || isDeleting || isSubmitting || isSuggestingCategory"
            type="button"
            variant="danger"
            @click="handleDeleteProduct"
          >
            {{ deleteLabel }}
          </BaseButton>

          <BaseButton :to="backRoute" variant="ghost">
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

.input-label {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-text);
}

.input-error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
}

.select-wrapper,
.image-field {
  display: grid;
  gap: 0.55rem;
}

.select-control {
  width: 100%;
  min-height: var(--tap-target-size);
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: var(--radius-md);
  background-color: rgba(255, 255, 255, 0.84);
  background-image:
    linear-gradient(45deg, transparent 50%, currentColor 50%),
    linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position:
    calc(100% - 1.3rem) 50%,
    calc(100% - 0.95rem) 50%;
  background-repeat: no-repeat;
  background-size: 0.36rem 0.36rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1.5;
  padding: 0.95rem 2.6rem 0.95rem 1rem;
  transition:
    border-color 0.24s ease,
    box-shadow 0.24s ease,
    background-color 0.24s ease;
  appearance: none;
}

.select-control:focus {
  outline: none;
  border-color: rgba(17, 17, 17, 0.3);
  box-shadow:
    0 0 0 4px rgba(17, 17, 17, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  background-color: #ffffff;
}

.has-error .select-control {
  border-color: rgba(125, 45, 36, 0.34);
}

.image-field__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.image-field__count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
}

.image-dropzone {
  position: relative;
  display: grid;
  min-height: 9.5rem;
  place-items: center;
  gap: var(--space-2);
  padding: var(--space-6);
  border: 1px dashed rgba(17, 17, 17, 0.24);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.66);
  color: var(--color-text);
  cursor: pointer;
  text-align: center;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.image-dropzone.is-dragging,
.image-dropzone:focus-within {
  border-color: rgba(17, 17, 17, 0.42);
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(17, 17, 17, 0.07);
}

.image-dropzone.has-error {
  border-color: rgba(125, 45, 36, 0.42);
  background: rgba(245, 223, 219, 0.32);
}

.image-input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.image-dropzone__title,
.image-dropzone__meta {
  display: block;
}

.image-dropzone__title {
  font-weight: 800;
}

.image-dropzone__meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.image-preview-list {
  display: grid;
  gap: var(--space-3);
  padding: 0;
  margin: 0;
  list-style: none;
}

.image-preview {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: calc(var(--radius-md) - 0.2rem);
  background: rgba(255, 255, 255, 0.76);
}

.image-preview__thumb {
  width: 4rem;
  aspect-ratio: 1;
  border-radius: 0.8rem;
  object-fit: cover;
  background: var(--color-surface-muted);
}

.image-preview__thumb--fallback {
  display: grid;
  place-items: center;
  color: var(--color-text-muted);
  font-weight: 800;
}

.image-preview__copy {
  display: grid;
  min-width: 0;
}

.image-preview__name,
.image-preview__size {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-preview__name {
  font-weight: 800;
}

.image-preview__size {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.image-preview__remove {
  min-height: var(--tap-target-size);
  border: 0;
  border-radius: 0.8rem;
  background: var(--color-primary-soft);
  color: var(--color-text);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 800;
  padding: 0.55rem 0.8rem;
}

.image-preview__remove:focus-visible {
  box-shadow: 0 0 0 4px rgba(17, 17, 17, 0.08);
}

.category-suggestion-field {
  display: grid;
  gap: var(--space-3);
}

.category-suggestion-button {
  width: 100%;
}

.price-recommendation-field {
  display: grid;
  gap: var(--space-2);
}

.button-spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 999px;
  animation: category-spinner 0.7s linear infinite;
}

@keyframes category-spinner {
  to {
    transform: rotate(360deg);
  }
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

  .image-preview {
    grid-template-columns: 3.5rem minmax(0, 1fr);
  }

  .image-preview__thumb {
    width: 3.5rem;
  }

  .image-preview__remove {
    grid-column: 1 / -1;
    width: 100%;
  }
}
</style>
