import { afterEach, vi } from 'vitest'

afterEach(() => {
  window.localStorage.clear()
  document.body.innerHTML = ''
  vi.clearAllMocks()
})
