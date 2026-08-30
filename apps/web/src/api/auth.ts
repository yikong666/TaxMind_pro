import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type LoginResponse = components['schemas']['SessionResponse'];

export interface LoginInput {
  email: string;
  password: string;
}

export function login(input: LoginInput): Promise<LoginResponse> {
  return requestJson<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}
