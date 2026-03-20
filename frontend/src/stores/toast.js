import { defineStore } from 'pinia'

let nextToastId = 0
const activeTimers = new Map()

export const useToastStore = defineStore('toast', {
  state: () => ({
    toasts: [],
  }),
  actions: {
    show(message, options = {}) {
      const toast = {
        id: nextToastId += 1,
        duration: options.duration ?? 3500,
        title: options.title || '',
        type: options.type || 'success',
        message,
      }

      this.toasts.push(toast)

      if (toast.duration > 0 && typeof window !== 'undefined') {
        const timerId = window.setTimeout(() => {
          this.dismiss(toast.id)
        }, toast.duration)

        activeTimers.set(toast.id, timerId)
      }

      return toast.id
    },
    success(message, options = {}) {
      return this.show(message, {
        ...options,
        type: 'success',
      })
    },
    error(message, options = {}) {
      return this.show(message, {
        ...options,
        type: 'error',
      })
    },
    dismiss(toastId) {
      const timerId = activeTimers.get(toastId)

      if (timerId) {
        window.clearTimeout(timerId)
        activeTimers.delete(toastId)
      }

      this.toasts = this.toasts.filter((toast) => toast.id !== toastId)
    },
  },
})
