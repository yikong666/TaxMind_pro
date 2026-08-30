import { toAppError } from '@/api/errors';

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const headers = new Headers(init?.headers);
  headers.set('Accept', 'application/json');
  try {
    response = await fetch(path, {
      ...init,
      headers,
    });
  } catch {
    throw toAppError(0, null, null);
  }

  const requestId = response.headers.get('X-Request-Id');
  const payload: unknown = await response.json();
  if (!response.ok) {
    throw toAppError(response.status, payload, requestId);
  }
  return payload as T;
}