import { useQuery } from '@tanstack/react-query';

import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type HealthResponse = components['schemas']['HealthResponse'];

export function useLiveness() {
  return useQuery({
    queryKey: ['health', 'live'],
    queryFn: () => requestJson<HealthResponse>('/health/live'),
    retry: false,
  });
}