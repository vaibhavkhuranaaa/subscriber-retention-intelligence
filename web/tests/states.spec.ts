import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations.filter((item) => item.impact === 'serious' || item.impact === 'critical')).toEqual([])
  await expect(page.locator('html').evaluate((element: HTMLElement) => element.scrollWidth <= element.clientWidth)).resolves.toBe(true)
}

test('provider error names recovery and remains accessible', async ({ page }) => {
  await page.route('**/api/v1/overview?**', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Semantic warehouse unavailable.' }),
  }))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Evidence unavailable')
  await expect(page.getByRole('button', { name: 'Retry product' })).toBeVisible()
  await expectAccessible(page)
})

test('empty cohort state explains the selected window', async ({ page }) => {
  await page.route('**/api/v1/cohorts?**', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: [], meta: { as_of: '2017-03', release_id: 'test', mode: 'private', metric_version: 'm8.1', filters: {} } }),
  }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Cohorts' }).click()
  await expect(page.getByText('No eligible cohorts')).toBeVisible()
  await expectAccessible(page)
})

test('public mode removes private journeys and scenarios', async ({ page }) => {
  await page.route('**/api/v1/status', async (route) => {
    const response = await route.fetch()
    const payload = await response.json()
    payload.meta.mode = 'public'
    payload.data.privacy_boundary = 'aggregate only'
    await route.fulfill({ response, body: JSON.stringify(payload) })
  })
  await page.goto('/')
  await expect(page.getByText('public', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Journeys' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Scenario' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Data', exact: true })).toBeVisible()
  await expectAccessible(page)
})
