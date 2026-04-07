import { test, expect } from '@playwright/test';

const ORIGIN = 'http://localhost:4000';
const API_HEADERS = { 'Origin': ORIGIN, 'Host': 'localhost:8003' };

test.describe('Live Mission E2E — Sprint 39', () => {
  test('mission create → list → detail lifecycle', async ({ request }) => {
    // Step 1: Create mission
    const createRes = await request.post('/api/v1/missions', {
      headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
      data: { goal: 'E2E test mission — verify lifecycle path', complexity: 'medium' },
    });
    expect(createRes.status()).toBe(201);
    const created = await createRes.json();
    expect(created).toHaveProperty('missionId');
    expect(created.state).toBe('pending');
    const missionId = created.missionId;

    // Step 2: Verify mission appears in list
    const listRes = await request.get('/api/v1/missions', { headers: API_HEADERS });
    expect(listRes.status()).toBe(200);
    const listBody = await listRes.json();
    const found = listBody.missions.find((m: { missionId: string }) => m.missionId === missionId);
    expect(found).toBeTruthy();

    // Step 3: Get mission detail (response: { meta, mission })
    const detailRes = await request.get(`/api/v1/missions/${missionId}`, { headers: API_HEADERS });
    expect(detailRes.status()).toBe(200);
    const detail = await detailRes.json();
    expect(detail).toHaveProperty('mission');
    expect(detail.mission.missionId).toBe(missionId);
  });

  test('approval list returns valid structure with enriched fields', async ({ request }) => {
    const res = await request.get('/api/v1/approvals', {
      headers: API_HEADERS,
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('approvals');
    expect(body).toHaveProperty('meta');
    expect(body.meta).toHaveProperty('dataQuality');
  });

  test('schedule CRUD lifecycle', async ({ request }) => {
    // Create
    const createRes = await request.post('/api/v1/schedules', {
      headers: { 'Origin': ORIGIN, 'Content-Type': 'application/json' },
      data: {
        name: 'E2E Test Schedule',
        template_id: 'preset_system_health',
        cron: '0 9 * * 1-5',
        parameters: {},
      },
    });
    expect(createRes.status()).toBe(201);
    const sched = await createRes.json();
    expect(sched).toHaveProperty('id');
    expect(sched.name).toBe('E2E Test Schedule');
    expect(sched.enabled).toBe(true);
    expect(sched.next_run).toBeTruthy();
    const schedId = sched.id;

    // List
    const listRes = await request.get('/api/v1/schedules', {
      headers: { 'Origin': ORIGIN },
    });
    expect(listRes.status()).toBe(200);
    const listBody = await listRes.json();
    expect(listBody.total).toBeGreaterThanOrEqual(1);

    // Get
    const getRes = await request.get(`/api/v1/schedules/${schedId}`, {
      headers: { 'Origin': ORIGIN },
    });
    expect(getRes.status()).toBe(200);
    const got = await getRes.json();
    expect(got.id).toBe(schedId);

    // Toggle
    const toggleRes = await request.post(`/api/v1/schedules/${schedId}/toggle`, {
      headers: { 'Origin': ORIGIN },
    });
    expect(toggleRes.status()).toBe(200);
    const toggled = await toggleRes.json();
    expect(toggled.enabled).toBe(false);

    // Delete
    const delRes = await request.delete(`/api/v1/schedules/${schedId}`, {
      headers: { 'Origin': ORIGIN },
    });
    expect(delRes.status()).toBe(200);
    expect((await delRes.json()).deleted).toBe(true);

    // Verify deleted
    const verifyRes = await request.get(`/api/v1/schedules/${schedId}`, {
      headers: { 'Origin': ORIGIN },
    });
    expect(verifyRes.status()).toBe(404);
  });

  test('presets list returns published templates', async ({ request }) => {
    const res = await request.get('/api/v1/templates/presets', {
      headers: { 'Origin': ORIGIN },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('presets');
    expect(body.total).toBeGreaterThanOrEqual(3);

    // All presets should be published
    for (const preset of body.presets) {
      expect(preset.status).toBe('published');
      expect(preset.name).toBeTruthy();
      expect(preset.mission_config).toHaveProperty('goal_template');
    }
  });

  test('SSE endpoint is reachable', async ({ request }) => {
    // SSE streams don't complete, so we just verify the endpoint exists
    // by checking a HEAD-like request or accepting timeout as success
    try {
      const res = await request.get('/api/v1/events/stream', {
        headers: API_HEADERS,
        timeout: 2000,
      });
      // If we get here, endpoint responded (unlikely for SSE)
      expect(res.status()).toBe(200);
    } catch (e: unknown) {
      // Timeout is expected for SSE streams — endpoint is reachable
      const msg = e instanceof Error ? e.message : String(e);
      expect(msg).toContain('Timeout');
    }
  });

  test('host security rejects invalid host', async ({ request }) => {
    const res = await request.get('/api/v1/health', {
      headers: { 'Host': 'evil.com' },
    });
    expect(res.status()).toBe(403);
  });
});
