const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const appConfig = {
  apiBaseUrl: rawApiBaseUrl.trim().replace(/\/+$/, ''),
  useMockData: (import.meta.env.VITE_USE_MOCK_DATA ?? 'true') !== 'false',
  databaseId: 'datapilot-business',
  endpoints: { query: '/api/query', schema: '/api/database/schema', history: '/api/history', evaluation: '/api/evaluation', status: '/api/agent/status' },
};
