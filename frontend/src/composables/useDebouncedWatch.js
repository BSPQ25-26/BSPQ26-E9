import { watch } from 'vue'

export const useDebouncedWatch = (source, callback, options = {}) => {
  const { debounce = 300, ...watchOptions } = options
  let timeoutId = null

  const stop = watch(
    source,
    (...args) => {
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }

      timeoutId = window.setTimeout(() => {
        timeoutId = null
        callback(...args)
      }, debounce)
    },
    watchOptions,
  )

  return () => {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
    }

    stop()
  }
}
