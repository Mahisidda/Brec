import { defineConfig, devices } from '@playwright/test';

const isCI = process.env.CI === 'true';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },

  use: {
    // Use the URL you’ve configured (fallback to localhost for local dev)
    baseURL: process.env.NEXT_PUBLIC_URL || 'http://localhost:3000',
    headless: true,
    viewport: { width: 1280, height: 720 },
  },

  // Only launch your local Next.js server when NOT in CI
  webServer: isCI
    ? undefined
    : {
        command: 'npm run dev',
        port: 3000,
        cwd: __dirname,
        reuseExistingServer: true,
      },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
