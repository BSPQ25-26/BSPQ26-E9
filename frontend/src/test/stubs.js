import { defineComponent, h } from 'vue'

export const BaseCardStub = defineComponent({
  name: 'BaseCard',
  setup(_, { slots }) {
    return () => h('section', { class: 'base-card-stub' }, slots.default?.())
  },
})

export const BaseButtonStub = defineComponent({
  name: 'BaseButton',
  props: {
    disabled: {
      type: Boolean,
      default: false,
    },
    type: {
      type: String,
      default: 'button',
    },
  },
  emits: ['click'],
  template: `
    <button :disabled="disabled" :type="type" @click="$emit('click', $event)">
      <slot />
    </button>
  `,
})

export const BaseInputStub = defineComponent({
  name: 'BaseInput',
  props: {
    error: {
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
    type: {
      type: String,
      default: 'text',
    },
  },
  emits: ['blur', 'update:modelValue'],
  template: `
    <label>
      <span>{{ label }}</span>
      <textarea
        v-if="multiline"
        :name="name"
        :value="modelValue"
        @blur="$emit('blur')"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <input
        v-else
        :name="name"
        :type="type"
        :value="modelValue"
        @blur="$emit('blur')"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <span v-if="error" class="input-error">{{ error }}</span>
    </label>
  `,
})

export const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

export const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })

  return { promise, reject, resolve }
}
