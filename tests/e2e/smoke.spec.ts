import { test, expect } from '@playwright/test';

test.describe('Vezir API Smoke Tests', () => {
  test('health endpoint returns 200', async ({ request }) => {
    const response = await request.get('/api/v1/health');
    expect(response.status()).toBe(200);
  });

  test('capabilities endpoint returns 200', async ({ request }) => {
    const response = await request.get('/api/v1/capabilities');
    expect(response.status()).toBe(200);
  });

  test('docs endpoint available', async ({ request }) => {
    const response = await request.get('/docs');
    expect(response.status()).toBe(200);
  });

  test('missions endpoint returns 200', async ({ request }) => {
    const response = await request.get('/api/v1/missions');
    expect(response.status()).toBe(200);
  });
});
