import { defineConfig, devices } from '@playwright/test'

const port = process.env.PLAYWRIGHT_PORT || '5173'
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${port}`
const shouldStartWebServer = !process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  reporter: [['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: shouldStartWebServer
    ? {
        command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
        url: baseURL,
      }
    : undefined,
})
