import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type CandidateQueueResponse = components['schemas']['CandidateQueueResponse'];
export type SourceSiteListResponse = components['schemas']['SourceSiteListResponse'];

export function listKnowledgeCandidates(accessToken: string): Promise<CandidateQueueResponse> {
  return requestJson<CandidateQueueResponse>('/api/v1/knowledge/candidates', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function listKnowledgeSources(accessToken: string): Promise<SourceSiteListResponse> {
  return requestJson<SourceSiteListResponse>('/api/v1/knowledge/sources', { headers: { Authorization: `Bearer ${accessToken}` } });
}
