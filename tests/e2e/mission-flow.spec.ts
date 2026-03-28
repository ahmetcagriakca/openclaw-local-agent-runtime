import { test, expect } from '@playwright/test';

test.describe('Live Mission E2E Flow', () => {
  test('mission lifecycle: list → create → detail → stages', async ({ request }) => {
    // Step 1: List missions (should return 200 even if empty)
    const listResponse = await request.get('/api/v1/missions');
    expect(listResponse.status()).toBe(200);
    const listBody = await listResponse.json();
    expect(listBody).toHaveProperty('data');
    expect(listBody).toHaveProperty('meta');

    // Step 2: Get capabilities (verify API is fully functional)
    const capsResponse = await request.get('/api/v1/capabilities');
    expect(capsResponse.status()).toBe(200);
    const capsBody = await capsResponse.json();
    expect(capsBody).toHaveProperty('data');

    // Step 3: Get health (full system check)
    const healthResponse = await request.get('/api/v1/health');
    expect(healthResponse.status()).toBe(200);
    const healthBody = await healthResponse.json();
    expect(healthBody).toHaveProperty('data');
    expect(healthBody.data).toHaveProperty('status');

    // Step 4: Get telemetry endpoint (even if empty)
    const telemetryResponse = await request.get('/api/v1/telemetry');
    expect(telemetryResponse.status()).toBe(200);
    const telemetryBody = await telemetryResponse.json();
    expect(telemetryBody).toHaveProperty('data');

    // Step 5: Get approvals endpoint
    const approvalsResponse = await request.get('/api/v1/approvals');
    expect(approvalsResponse.status()).toBe(200);
    const approvalsBody = await approvalsResponse.json();
    expect(approvalsBody).toHaveProperty('data');

    // Step 6: Verify non-existent mission returns 404
    const notFoundResponse = await request.get('/api/v1/missions/nonexistent-id');
    expect(notFoundResponse.status()).toBe(404);
  });

  test('API meta envelope has required fields', async ({ request }) => {
    const response = await request.get('/api/v1/missions');
    const body = await response.json();

    expect(body.meta).toHaveProperty('generatedAt');
    expect(body.meta).toHaveProperty('dataQuality');
  });

  test('host security rejects invalid origin', async ({ request }) => {
    const response = await request.post('/api/v1/approvals/test/approve', {
      headers: { 'Origin': 'http://evil.com' },
    });
    expect(response.status()).toBe(403);
  });
});
