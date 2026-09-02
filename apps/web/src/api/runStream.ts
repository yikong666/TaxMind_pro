export type QueryRunStreamEventType = 'started' | 'needs_input' | 'delta' | 'completed' | 'failed';

export interface QueryRunStreamEvent {
  id: string;
  event: QueryRunStreamEventType;
  data: {
    run_id: string;
    sequence_no: number;
    occurred_at: string;
    status?: string;
    follow_up_fact_keys?: string[];
    error_code?: string;
    error_detail_safe?: string;
    message_id?: string;
    text?: string;
    citation_ids?: string[];
    gap_codes?: string[];
  };
}

export async function replayQueryRunEvents(
  runId: string,
  accessToken: string,
  lastEventId: string | null,
  onEvent: (event: QueryRunStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers({
    Accept: 'text/event-stream',
    Authorization: `Bearer ${accessToken}`,
  });
  if (lastEventId !== null) {
    headers.set('Last-Event-ID', lastEventId);
  }
  const init: RequestInit = { headers };
  if (signal !== undefined) {
    init.signal = signal;
  }
  const response = await fetch(`/api/v1/query-runs/${runId}/events`, init);
  if (!response.ok || response.body === null) {
    throw new Error('运行事件流不可用');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const next = await reader.read();
    if (next.done) {
      break;
    }
    buffer += decoder.decode(next.value, { stream: true });
    const records = buffer.split('\n\n');
    buffer = records.pop() ?? '';
    records.forEach((record) => {
      const parsed = parseQueryRunStreamEvent(record);
      if (parsed !== null) {
        onEvent(parsed);
      }
    });
  }
  const finalRecord = buffer.trim();
  if (finalRecord) {
    const parsed = parseQueryRunStreamEvent(finalRecord);
    if (parsed !== null) {
      onEvent(parsed);
    }
  }
}

export function parseQueryRunStreamEvent(record: string): QueryRunStreamEvent | null {
  const fields = new Map<string, string>();
  record.split('\n').forEach((line) => {
    const separator = line.indexOf(':');
    if (separator > 0) {
      fields.set(line.slice(0, separator), line.slice(separator + 1).trimStart());
    }
  });
  const id = fields.get('id');
  const event = fields.get('event');
  const rawData = fields.get('data');
  if (id === undefined || rawData === undefined || !isEventType(event)) {
    return null;
  }
  const data: unknown = JSON.parse(rawData);
  if (!isEventData(data)) {
    return null;
  }
  return { id, event, data };
}

function isEventType(value: string | undefined): value is QueryRunStreamEventType {
  return value === 'started' || value === 'needs_input' || value === 'delta' || value === 'completed' || value === 'failed';
}

function isEventData(value: unknown): value is QueryRunStreamEvent['data'] {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const data = value as Record<string, unknown>;
  return typeof data.run_id === 'string'
    && typeof data.sequence_no === 'number'
    && typeof data.occurred_at === 'string';
}
