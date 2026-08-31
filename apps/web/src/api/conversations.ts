import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type AppendUserMessageRequest = components['schemas']['AppendUserMessageRequest'];
export type ConversationContextResponse = components['schemas']['ConversationContextResponse'];
export type ConversationResponse = components['schemas']['ConversationResponse'];
export type CreateConversationRequest = components['schemas']['CreateConversationRequest'];
export type MessageData = components['schemas']['MessageData'];
export type MessageResponse = components['schemas']['MessageResponse'];
export type MessagesResponse = components['schemas']['MessagesResponse'];

export function createConversation(
  caseId: string,
  payload: CreateConversationRequest,
  accessToken: string,
): Promise<ConversationResponse> {
  return requestJson<ConversationResponse>(`/api/v1/cases/${caseId}/conversations`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}

export function listConversationMessages(
  conversationId: string,
  accessToken: string,
): Promise<MessagesResponse> {
  return requestJson<MessagesResponse>(`/api/v1/conversations/${conversationId}/messages`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function appendUserMessage(
  conversationId: string,
  payload: AppendUserMessageRequest,
  accessToken: string,
): Promise<MessageResponse> {
  return requestJson<MessageResponse>(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}

export function getConversationContext(
  conversationId: string,
  accessToken: string,
): Promise<ConversationContextResponse> {
  return requestJson<ConversationContextResponse>(
    `/api/v1/conversations/${conversationId}/context`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}
