<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  block: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  href: {
    type: String,
    default: '',
  },
  size: {
    type: String,
    default: 'md',
  },
  to: {
    type: [String, Object],
    default: '',
  },
  type: {
    type: String,
    default: 'button',
  },
  variant: {
    type: String,
    default: 'primary',
  },
})

const component = computed(() => {
  if (props.to) {
    return RouterLink
  }

  if (props.href) {
    return 'a'
  }

  return 'button'
})

const componentProps = computed(() => {
  if (props.to) {
    return { to: props.to }
  }

  if (props.href) {
    return { href: props.href }
  }

  return {
    disabled: props.disabled,
    type: props.type,
  }
})
</script>

<template>
  <component
    :is="component"
    class="base-button"
    :class="[`is-${variant}`, `is-${size}`, { 'is-block': block, 'is-disabled': disabled }]"
    v-bind="componentProps"
  >
    <slot />
  </component>
</template>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  padding: 0 1.15rem;
  border: 1px solid transparent;
  border-radius: 1.15rem;
  font-size: 1rem;
  font-weight: 800;
  line-height: 1.2;
  text-align: center;
  text-wrap: balance;
  transition:
    transform 0.24s ease,
    background-color 0.24s ease,
    border-color 0.24s ease,
    color 0.24s ease,
    box-shadow 0.24s ease;
  cursor: pointer;
}

.base-button:hover {
  transform: translateY(-2px);
}

.base-button.is-primary {
  background: linear-gradient(180deg, #1f1f1f, #090909);
  color: #f9f8f4;
  box-shadow: var(--shadow-sm);
}

.base-button.is-primary:hover {
  background: var(--color-primary-strong);
}

.base-button.is-secondary {
  background: var(--color-surface-strong);
  color: var(--color-text);
  border-color: rgba(17, 17, 17, 0.12);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.75),
    0 12px 30px rgba(17, 17, 17, 0.06);
}

.base-button.is-secondary:hover {
  border-color: rgba(17, 17, 17, 0.24);
}

.base-button.is-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border-color: rgba(125, 45, 36, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.base-button.is-danger:hover {
  border-color: rgba(125, 45, 36, 0.34);
  background: #f0d2cc;
}

.base-button.is-ghost {
  background: transparent;
  color: var(--color-text);
  border-color: rgba(17, 17, 17, 0.08);
}

.base-button.is-sm {
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  padding: 0 0.95rem;
  font-size: 1rem;
}

.base-button.is-lg {
  min-height: 3.6rem;
  padding: 0 1.4rem;
  font-size: 1.05rem;
}

.base-button.is-block {
  width: 100%;
}

.base-button.is-disabled {
  opacity: 0.6;
  pointer-events: none;
}
</style>
