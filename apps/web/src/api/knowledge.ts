import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type CandidateQueueResponse = components['schemas']['CandidateQueueResponse'];
export type CandidateReviewRequest = components['schemas']['CandidateReviewRequest'];
export type KnowledgeCandidateResponse = components['schemas']['KnowledgeCandidateResponse'];
export type KnowledgePublishBatchListResponse = components['schemas']['KnowledgePublishBatchListResponse'];
export type KnowledgePublishBatchResponse = components['schemas']['KnowledgePublishBatchResponse'];
export type KnowledgeSnapshotResponse = components['schemas']['KnowledgeSnapshotResponse'];
export type ManualImportResponse = components['schemas']['ManualImportResponse'];
export type RegisterSourceSiteRequest = components['schemas']['RegisterSourceSiteRequest'];
export type SourceSiteListResponse = components['schemas']['SourceSiteListResponse'];
export type SourceSiteResponse = components['schemas']['SourceSiteResponse'];

export type KnowledgeDocumentUpload = {
  sourceSiteId: string;
  title: string;
  issuingAuthority: string;
  regionCode: string;
  canonicalUrl: string;
  file: File;
  docNo?: string;
  docType?: string;
  sourceLevel?: string;
  publishDate?: string;
  effectiveStart?: string;
  effectiveEnd?: string;
};

export function listKnowledgeCandidates(accessToken: string): Promise<CandidateQueueResponse> {
  return requestJson<CandidateQueueResponse>('/api/v1/knowledge/candidates', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function listApprovedKnowledgeCandidates(accessToken: string): Promise<CandidateQueueResponse> {
  return requestJson<CandidateQueueResponse>('/api/v1/knowledge/candidates/approved', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function listKnowledgePublishBatches(accessToken: string): Promise<KnowledgePublishBatchListResponse> {
  return requestJson<KnowledgePublishBatchListResponse>('/api/v1/knowledge/publish-batches', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function createKnowledgePublishBatch(candidateIds: string[], accessToken: string): Promise<KnowledgePublishBatchResponse> {
  return requestJson<KnowledgePublishBatchResponse>('/api/v1/knowledge/publish-batches', { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify({ candidate_ids: candidateIds }) });
}

export function validateKnowledgePublishBatch(batchId: string, accessToken: string): Promise<KnowledgePublishBatchResponse> {
  return requestJson<KnowledgePublishBatchResponse>(`/api/v1/knowledge/publish-batches/${batchId}/validate`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } });
}

export function materializeKnowledgeSnapshot(batchId: string, accessToken: string): Promise<KnowledgeSnapshotResponse> {
  return requestJson<KnowledgeSnapshotResponse>(`/api/v1/knowledge/publish-batches/${batchId}/materialize-snapshot`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } });
}

export function reviewKnowledgeCandidate(
  candidateId: string,
  payload: CandidateReviewRequest,
  accessToken: string,
): Promise<KnowledgeCandidateResponse> {
  return requestJson<KnowledgeCandidateResponse>(`/api/v1/knowledge/candidates/${candidateId}/review`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}

export function listKnowledgeSources(accessToken: string): Promise<SourceSiteListResponse> {
  return requestJson<SourceSiteListResponse>('/api/v1/knowledge/sources', { headers: { Authorization: `Bearer ${accessToken}` } });
}

export function registerKnowledgeSource(
  payload: RegisterSourceSiteRequest,
  accessToken: string,
): Promise<SourceSiteResponse> {
  return requestJson<SourceSiteResponse>('/api/v1/knowledge/sources', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}

export function uploadKnowledgeDocument(
  payload: KnowledgeDocumentUpload,
  accessToken: string,
): Promise<ManualImportResponse> {
  const formData = new FormData();
  formData.append('source_site_id', payload.sourceSiteId);
  formData.append('title', payload.title);
  formData.append('issuing_authority', payload.issuingAuthority);
  formData.append('region_code', payload.regionCode);
  formData.append('canonical_url', payload.canonicalUrl);
  formData.append('file', payload.file);
  const optionalFields = [
    ['doc_no', payload.docNo],
    ['doc_type', payload.docType],
    ['source_level', payload.sourceLevel],
    ['publish_date', payload.publishDate],
    ['effective_start', payload.effectiveStart],
    ['effective_end', payload.effectiveEnd],
  ] as const;
  optionalFields.forEach(([field, value]) => {
    if (value !== undefined) formData.append(field, value);
  });
  return requestJson<ManualImportResponse>('/api/v1/knowledge/uploads', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  });
}
