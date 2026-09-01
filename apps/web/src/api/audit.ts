import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type AuditLogSearchResponse = components['schemas']['AuditLogSearchResponse'];

export function searchAuditLogs(accessToken: string): Promise<AuditLogSearchResponse> {
  return requestJson('/api/v1/audit-logs', { headers: { Authorization: `Bearer ${accessToken}` } });
}
