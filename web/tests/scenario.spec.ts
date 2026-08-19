import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { TestInfo } from '@playwright/test'
import path from 'node:path'

function evidencePath(testInfo: TestInfo, name: string) {
  return process.env.RETENTION_EVIDENCE_DIR
    ? path.join(process.env.RETENTION_EVIDENCE_DIR, name)
    : testInfo.outputPath(name)
}


test('simulated scenario changes a bounded repeat-subscriber decision', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Scenario' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('50,000-contact scenario')
  await expect(page.getByText('Simulated', { exact: true })).toBeVisible()
  await expect(page.locator('.priority-strip').getByText('881,701')).toBeVisible()
  await expect(page.locator('.priority-strip').getByText('Eligible repeat subscribers')).toBeVisible()
  await expect(page.getByRole('button', { name: '2017-02' })).toHaveCount(0)

  await page.getByLabel('Contact capacity').fill('')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('50,000-contact scenario')
  await page.getByLabel('Contact capacity').fill('30000')
  await page.getByLabel('Assumed retention lift').fill('0.15')
  await page.getByRole('button', { name: 'Run simulated scenario' }).click()
  await expect(page.locator('.scenario-metrics').getByText('30,000')).toBeVisible()
  await expect(page.getByText('Repeat subscribers only · March 2017 score window')).toBeVisible()
  await expect(page.getByText('Excluded', { exact: true })).toBeVisible()
  await page.getByLabel('Offer cost').fill('3')
  await expect(page.locator('.scenario-metrics')).not.toBeVisible()
  await expect(page.getByText('No result for these assumptions')).toBeVisible()
  await page.getByRole('button', { name: 'Run simulated scenario' }).click()
  await expect(page.locator('.scenario-metrics').getByText('30,000')).toBeVisible()
  await page.getByRole('button', { name: 'Definitions', exact: true }).click()
  await page.getByRole('button', { name: 'Scenario' }).click()
  await expect(page.locator('.scenario-metrics').getByText('30,000')).toBeVisible()
  await expect(page.locator('html').evaluate((element) => element.scrollWidth <= element.clientWidth)).resolves.toBe(true)

  const results = await new AxeBuilder({ page }).analyze()
  const violations = results.violations.filter((item) => item.impact === 'serious' || item.impact === 'critical')
  expect(violations).toEqual([])
  expect(consoleErrors).toEqual([])
  await page.evaluate(() => {
    const skipLink = document.querySelector('.skip-link') as HTMLElement | null
    if (skipLink) skipLink.style.display = 'none'
    window.scrollTo(0, 0)
  })
  await page.screenshot({ path: evidencePath(testInfo, `m8-scenario-${testInfo.project.name}.png`), fullPage: true })
})
