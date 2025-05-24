// frontend/tests/home.spec.ts
import { test, expect } from '@playwright/test';
import popular from './fixtures/popular.json';

test('can pick two books and get recommendations', async ({ page }) => {
  // 1) Stub /popular_books?limit=… (must include the `*` to match the query)
  await page.route('**/popular_books*', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(popular),
    })
  );

  // 2) Stub your POST /recommend_by_books
  await page.route('**/recommend_by_books*', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { Book_ID: '444', Book_Title: 'delta', Recommendation_Score: 9.5 },
        { Book_ID: '333', Book_Title: 'charlie', Recommendation_Score: 8.2 },
      ]),
    })
  );

  // 3) Now navigate and wait for all network calls to settle
  await page.goto('/', { waitUntil: 'networkidle' });

  // 4) You should now see exactly `popular.length` cards
  const cards = page.locator('[data-testid="book-card"]');
  await expect(cards).toHaveCount(popular.length, { timeout: 10_000 });

  // 5) Click two distinct cards
  await cards.nth(0).click();
  await cards.nth(1).click();

  // 6) Fire your recommendation request
  await page.click('button:has-text("Get Recommendations")');

  // 7) Scope to just the recommendation container
  const recs = page.locator(
    '[data-testid="recommendations-list"] >> text=Score:'
  );
  await expect(recs).toHaveCount(2, { timeout: 5_000 });

  // 8) And verify the titles you stubbed show up
  await expect(page.locator('text=delta')).toBeVisible();
  await expect(page.locator('text=charlie')).toBeVisible();
});
