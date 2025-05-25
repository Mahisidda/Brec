# Test info

- Name: can pick two books and get recommendations
- Location: /Users/mahisidda/Downloads/Projects/Brec/frontend/tests/home.spec.ts:5:5

# Error details

```
Error: expect.toBeVisible: Error: strict mode violation: locator('text=delta') resolved to 2 elements:
    1) <h3 class="text-lg text-black font-semibold">delta</h3> aka locator('div').filter({ hasText: /^deltaScore: 0\.00$/ }).getByRole('heading')
    2) <h3 class="text-lg text-black font-semibold">delta</h3> aka getByTestId('recommendations-list').getByRole('heading', { name: 'delta' })

Call log:
  - expect.toBeVisible with timeout 5000ms
  - waiting for locator('text=delta')

    at /Users/mahisidda/Downloads/Projects/Brec/frontend/tests/home.spec.ts:48:44
```

# Page snapshot

```yaml
- main:
  - heading "📚 Choose Two Books You Loved" [level=1]
  - paragraph: Click on at least two books below to get personalized recommendations.
  - img "alpha"
  - heading "alpha" [level=3]
  - paragraph: "Score: 0.00"
  - text: ✓ Selected
  - img "delta"
  - heading "delta" [level=3]
  - paragraph: "Score: 0.00"
  - text: ✓ Selected
  - img "bravo"
  - heading "bravo" [level=3]
  - paragraph: "Score: 0.00"
  - img "charlie"
  - heading "charlie" [level=3]
  - paragraph: "Score: 0.00"
  - button "Get Recommendations"
  - heading "You Might Also Like:" [level=2]
  - img "delta"
  - heading "delta" [level=3]
  - paragraph: "Score: 9.50"
  - img "charlie"
  - heading "charlie" [level=3]
  - paragraph: "Score: 8.20"
- alert
- button "Open Next.js Dev Tools":
  - img
```

# Test source

```ts
   1 | // frontend/tests/home.spec.ts
   2 | import { test, expect } from '@playwright/test';
   3 | import popular from './fixtures/popular.json';
   4 |
   5 | test('can pick two books and get recommendations', async ({ page }) => {
   6 |   // 1) Stub /popular_books?limit=… (must include the `*` to match the query)
   7 |   await page.route('**/popular_books*', route =>
   8 |     route.fulfill({
   9 |       status: 200,
  10 |       contentType: 'application/json',
  11 |       body: JSON.stringify(popular),
  12 |     })
  13 |   );
  14 |
  15 |   // 2) Stub your POST /recommend_by_books
  16 |   await page.route('**/recommend_by_books*', route =>
  17 |     route.fulfill({
  18 |       status: 200,
  19 |       contentType: 'application/json',
  20 |       body: JSON.stringify([
  21 |         { Book_ID: '444', Book_Title: 'delta', Recommendation_Score: 9.5 },
  22 |         { Book_ID: '333', Book_Title: 'charlie', Recommendation_Score: 8.2 },
  23 |       ]),
  24 |     })
  25 |   );
  26 |
  27 |   // 3) Now navigate and wait for all network calls to settle
  28 |   await page.goto('/', { waitUntil: 'networkidle' });
  29 |
  30 |   // 4) You should now see exactly `popular.length` cards
  31 |   const cards = page.locator('[data-testid="book-card"]');
  32 |   await expect(cards).toHaveCount(popular.length, { timeout: 10_000 });
  33 |
  34 |   // 5) Click two distinct cards
  35 |   await cards.nth(0).click();
  36 |   await cards.nth(1).click();
  37 |
  38 |   // 6) Fire your recommendation request
  39 |   await page.click('button:has-text("Get Recommendations")');
  40 |
  41 |   // 7) Scope to just the recommendation container
  42 |   const recs = page.locator(
  43 |     '[data-testid="recommendations-list"] >> text=Score:'
  44 |   );
  45 |   await expect(recs).toHaveCount(2, { timeout: 5_000 });
  46 |
  47 |   // 8) And verify the titles you stubbed show up
> 48 |   await expect(page.locator('text=delta')).toBeVisible();
     |                                            ^ Error: expect.toBeVisible: Error: strict mode violation: locator('text=delta') resolved to 2 elements:
  49 |   await expect(page.locator('text=charlie')).toBeVisible();
  50 | });
  51 |
```