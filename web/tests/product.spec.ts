import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { TestInfo } from '@playwright/test'
import path from 'node:path'

function evidencePath(testInfo: TestInfo, name: string) {
  return process.env.RETENTION_EVIDENCE_DIR
    ? path.join(process.env.RETENTION_EVIDENCE_DIR, name)
    : testInfo.outputPath(name)
}

test('governed operating workflow is accessible and responsive', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to analysis' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Material movements')
  await expect(page.getByText('Renewal weakened')).toHaveCount(0)
  await expect(page.getByText('Observed churn', { exact: true }).first()).toBeVisible()
  await expect(page.locator('.movement-table')).toContainText('6.4%')
  await expect(page.locator('.movement-table')).toContainText('9.0%')
  await expect(page.locator('.movement-table')).toContainText('+2.6 pp')
  await page.getByRole('button', { name: '30-day gross receipts' }).click()
  await expect(page.getByRole('heading', { name: '30-day gross receipts' })).toBeVisible()
  await expect(page.getByText('Source payment', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Observed churn' }).click()
  await expect(page.getByRole('heading', { name: 'Observed churn' })).toBeVisible()
  await expect(page.locator('.reconciliation')).toContainText('8.99% − 6.39% = +2.60 pp')
  const cohortLabels = await page.locator('.cohort-breaks tbody td:first-child').allTextContents()
  expect(cohortLabels.length).toBeGreaterThan(0)
  expect(cohortLabels.every((label) => label.trim() <= '2017-01')).toBe(true)
  await expect(page.locator('.cohort-breaks tbody')).not.toContainText('2017-02')
  await expect(page.locator('.cohort-breaks tbody')).not.toContainText('2017-03')
  const inspectorPrecedesCohorts = await page.evaluate(() => {
    const inspector = document.querySelector('.movement-inspector')
    const cohorts = document.querySelector('.cohort-breaks')
    return Boolean(inspector && cohorts && (inspector.compareDocumentPosition(cohorts) & Node.DOCUMENT_POSITION_FOLLOWING))
  })
  expect(inspectorPrecedesCohorts).toBe(true)
  await page.getByRole('button', { name: 'Cancellation event rate' }).click()
  await expect(page.locator('.inspector-heading strong')).toHaveText(/^[+-]?\d+\.\d pp$/)
  await expect(page.locator('.inspector-heading')).not.toContainText('-0.0 pp')
  await expect(page.locator('html').evaluate((element) => element.scrollWidth <= element.clientWidth)).resolves.toBe(true)

  await page.getByRole('button', { name: '2017-02' }).click()
  await expect(page.locator('.priority-strip').getByText('2017-01-31')).toBeVisible()
  await expect(page.locator('.priority-strip').getByText('992,931')).toBeVisible()
  await page.getByRole('button', { name: '2017-03' }).click()
  await expect(page.locator('.priority-strip').getByText('2017-02-28')).toBeVisible()

  await page.getByRole('button', { name: 'Segments' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Observed churn by segment')
  await page.getByRole('tab', { name: 'Payment' }).click()
  await expect(page.getByText(/Method /).first()).toBeVisible()

  if (testInfo.project.name === 'desktop') {
    await page.getByRole('button', { name: 'Journeys' }).click()
    const firstSubscriber = page.locator('.subscriber-row').first()
    await expect(firstSubscriber).toBeVisible()
    await firstSubscriber.click()
    await expect(page.getByRole('heading', { name: /Latest subscription events/i })).toBeVisible({ timeout: 5_000 })
  }

  const results = await new AxeBuilder({ page }).analyze()
  const violations = results.violations.filter((item) => item.impact === 'serious' || item.impact === 'critical')
  expect(violations).toEqual([])
  expect(consoleErrors).toEqual([])
  await page.getByRole('button', { name: 'Overview' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Material movements')
  const smallSampleCount = await page.locator('.segment-breaks .small-sample').count()
  await expect(page.getByText(/rows below 100 eligible subscribers/i)).toHaveCount(smallSampleCount ? 1 : 0)
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur()
    const skipLink = document.querySelector('.skip-link') as HTMLElement | null
    if (skipLink) skipLink.style.display = 'none'
    window.scrollTo(0, 0)
  })
  await page.screenshot({ path: evidencePath(testInfo, `m9r-dashboard-${testInfo.project.name}-stakeholder.png`), fullPage: true })
  await page.getByRole('button', { name: 'Data', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Detailed data catalog' })).toBeVisible()
  await expect(page.getByText('442,211,685', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Browse full dataset' })).toHaveAttribute('href', 'https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence')
  await expect(page.getByRole('link', { name: 'Member' })).toHaveAttribute('href', /\/viewer\/member\/full$/)
  await expect(page.getByRole('row', { name: /Listening day/ })).toContainText('410,502,905')
  await expect(page.getByText('This is not an aggregate extract.')).toBeVisible()
  await expect(page.locator('html').evaluate((element) => element.scrollWidth <= element.clientWidth)).resolves.toBe(true)
  await page.screenshot({ path: evidencePath(testInfo, `m12-data-catalog-${testInfo.project.name}.png`), fullPage: true })
  await page.getByRole('button', { name: 'Definitions', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Metric definitions')
  await page.screenshot({ path: evidencePath(testInfo, `m9r-dashboard-${testInfo.project.name}-technical.png`), fullPage: true })
})
