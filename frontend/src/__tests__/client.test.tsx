/**
 * API client tests — typed fetch, error handling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getMissions, getHealth, ApiError } from '../api/client'

describe('API Client', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getMissions returns typed response', async () => {
    const mockData = {
      meta: {
        freshnessMs: 100,
        dataQuality: 'fresh',
        sourcesUsed: [],
        sourcesMissing: [],
        generatedAt: '2026-03-25T10:00:00Z',
      },
      missions: [],
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const result = await getMissions()
    expect(result.meta.dataQuality).toBe('fresh')
    expect(result.missions).toEqual([])
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/missions')
  })

  it('throws ApiError on 404', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: 'not_found' }),
    })

    await expect(getHealth()).rejects.toThrow(ApiError)
    try {
      await getHealth()
    } catch (e) {
      expect((e as ApiError).status).toBe(404)
    }
  })

  it('throws ApiError on network error text body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
      text: () => Promise.resolve('Internal Server Error'),
    })

    await expect(getMissions()).rejects.toThrow(ApiError)
  })
})
