<script setup>
import { computed, useAttrs, useId } from 'vue'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  autocomplete: {
    type: String,
    default: 'off',
  },
  error: {
    type: String,
    default: '',
  },
  id: {
    type: String,
    default: '',
  },
  label: {
    type: String,
    default: '',
  },
  modelValue: {
    type: [Number, String],
    default: '',
  },
  multiline: {
    type: Boolean,
    default: false,
  },
  name: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '',
  },
  required: {
    type: Boolean,
    default: false,
  },
  rows: {
    type: Number,
    default: 4,
  },
  type: {
    type: String,
    default: 'text',
  },
})

const emit = defineEmits(['update:modelValue'])
const attrs = useAttrs()
const generatedId = useId()

const inputId = computed(() => props.id || generatedId)
const errorId = computed(() => `${inputId.value}-error`)
const hasError = computed(() => Boolean(props.error))
const controlTag = computed(() => (props.multiline ? 'textarea' : 'input'))
const wrapperClass = computed(() => attrs.class)
const wrapperStyle = computed(() => attrs.style)
const controlAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})

const sharedProps = computed(() => ({
  ...controlAttrs.value,
  'aria-describedby': hasError.value ? errorId.value : undefined,
  'aria-invalid': hasError.value ? 'true' : 'false',
  autocomplete: props.autocomplete,
  class: 'input-control',
  id: inputId.value,
  name: props.name || inputId.value,
  placeholder: props.placeholder,
  required: props.required,
  rows: props.multiline ? props.rows : undefined,
  type: props.multiline ? undefined : props.type,
  value: props.modelValue,
}))

const updateValue = (event) => {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <label
    class="input-wrapper"
    :class="[wrapperClass, { 'has-error': hasError }]"
    :style="wrapperStyle"
    :for="inputId"
  >
    <span v-if="label" class="input-label">
      {{ label }}
    </span>

    <component
      :is="controlTag"
      v-bind="sharedProps"
      @input="updateValue"
    />

    <span v-if="error" :id="errorId" class="input-error">
      {{ error }}
    </span>
  </label>
</template>

<style scoped>
.input-wrapper {
  display: grid;
  gap: 0.55rem;
}

.input-label {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-text);
}

.input-control {
  width: 100%;
  min-height: var(--tap-target-size);
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
  padding: 0.95rem 1rem;
  font-size: 1rem;
  line-height: 1.5;
  color: var(--color-text);
  transition:
    border-color 0.24s ease,
    box-shadow 0.24s ease,
    background-color 0.24s ease;
  appearance: none;
}

.input-control:focus {
  outline: none;
  border-color: rgba(17, 17, 17, 0.3);
  box-shadow:
    0 0 0 4px rgba(17, 17, 17, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  background: #ffffff;
}

textarea.input-control {
  resize: vertical;
  min-height: 7.5rem;
  padding-block: 1rem;
  border-radius: 1.55rem;
}

.has-error .input-control {
  border-color: rgba(125, 45, 36, 0.34);
}

.input-error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
}
</style>
