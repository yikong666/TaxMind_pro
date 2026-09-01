import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type FeedbackListResponse = components['schemas']['FeedbackListResponse'];
export type CreateFeedbackRequest = components['schemas']['CreateFeedbackRequest'];

export function listFeedbackItems(accessToken: string): Promise<FeedbackListResponse> {
  return requestJson('/api/v1/feedback-items', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function createFeedbackItem(payload: CreateFeedbackRequest, accessToken: string): Promise<components['schemas']['FeedbackItemResponse']> {
  return requestJson('/api/v1/feedback-items', {
    method: 'POST', headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify(payload),
  });
}
