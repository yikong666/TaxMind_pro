import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type ReviewQueueResponse = components['schemas']['ReviewQueueResponse'];
export type ReviewTaskDetailResponse = components['schemas']['ReviewTaskDetailResponse'];
export type ReviewActionRequest = components['schemas']['ReviewActionRequest'];

export function listReviewTasks(accessToken: string): Promise<ReviewQueueResponse> {
  return requestJson('/api/v1/review-tasks', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function getReviewTask(id: string, accessToken: string): Promise<ReviewTaskDetailResponse> {
  return requestJson(`/api/v1/review-tasks/${id}`, { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function recordReviewAction(
  id: string,
  payload: ReviewActionRequest,
  accessToken: string,
): Promise<components['schemas']['ReviewTaskResponse']> {
  return requestJson(`/api/v1/review-tasks/${id}/actions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}
