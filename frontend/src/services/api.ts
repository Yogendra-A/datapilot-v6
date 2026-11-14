import { appConfig } from '../config/app';
import * as mock from './mockApi';
import type { DatabaseSchemaResponse, EvaluationResponse, HistoryItem, QueryRequest, QueryResponse } from '../types/api';

const QUERY_TIMEOUT_MS = 120_000;
const DEFAULT_TIMEOUT_MS = 15_000;

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Backend request failed (${response.status})`);
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The request timed out.');
    if (error instanceof TypeError) throw new Error(`Cannot reach the backend at ${appConfig.apiBaseUrl}. Check that the Colab server and tunnel are running.`);
    if (error instanceof Error && error.message.startsWith('Backend request failed')) throw error;
    throw new Error('The backend request failed. Please try again.');
  } finally {
    window.clearTimeout(timeout);
  }
}
export const executeQuery = (question: string): Promise<QueryResponse> => appConfig.useMockData ? mock.mockExecuteQuery({ question, database_id: appConfig.databaseId }) : request<QueryResponse>(appConfig.endpoints.query, { method: 'POST', body: JSON.stringify({ question, database_id: appConfig.databaseId } satisfies QueryRequest) }, QUERY_TIMEOUT_MS);
export const getDatabaseSchema = (): Promise<DatabaseSchemaResponse> => appConfig.useMockData ? mock.mockSchema() : request(appConfig.endpoints.schema);
export const getQueryHistory = (): Promise<HistoryItem[]> => appConfig.useMockData ? mock.mockHistory() : request(appConfig.endpoints.history);
export const getEvaluationResults = (): Promise<EvaluationResponse> => appConfig.useMockData ? mock.mockEvaluation() : request(appConfig.endpoints.evaluation);
export const getAgentStatus = (): Promise<{ status: string; model?: string; adapter?: string }> => appConfig.useMockData ? Promise.resolve({ status: 'demo' }) : request(appConfig.endpoints.status);
