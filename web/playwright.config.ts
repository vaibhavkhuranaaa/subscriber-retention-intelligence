import { defineConfig, devices } from '@playwright/test'

const python = process.env.CI ? 'python' : '../.venv/bin/python'
const externalServer = process.env.RETENTION_EXTERNAL_SERVER === '1'
const baseURL = process.env.RETENTION_BASE_URL || 'http://127.0.0.1:8001'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['line']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
  },
  ...(externalServer
    ? {}
    : {
        webServer: {
          command: `${python} -m uvicorn retention_api.main:app --app-dir .. --host 127.0.0.1 --port 8001 --workers 1`,
          url: 'http://127.0.0.1:8001/api/v1/status',
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }),
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { ...devices['iPhone 13'], browserName: 'chromium', viewport: { width: 390, height: 844 } } },
  ],
})
