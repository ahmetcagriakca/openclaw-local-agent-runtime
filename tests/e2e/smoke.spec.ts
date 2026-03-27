import { test, expect } from '@playwright/test';

test.describe('Vezir API Smoke Tests', () => {
  test('health endpoint returns 200', async ({ request }) => {
    const response = await request.get('/health');
    expect(response.status()).toBe(200);
  });

  test('API root returns response', async ({ request }) => {
    const response = await request.get('/');
    expect(response.ok()).toBeTruthy();
  });

  test('docs endpoint available', async ({ request }) => {
    const response = await request.get('/docs');
    expect(response.status()).toBe(200);
  });
});
