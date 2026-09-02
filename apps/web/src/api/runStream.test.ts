import { describe, expect, it } from 'vitest';

import { parseQueryRunStreamEvent } from '@/api/runStream';

describe('parseQueryRunStreamEvent', () => {
  it('parses a replayable final-answer delta without private reasoning', () => {
    const event = parseQueryRunStreamEvent(
      'id: run-1:2\nevent: delta\ndata: {"run_id":"run-1","sequence_no":2,"occurred_at":"2026-09-02T00:00:00+00:00","message_id":"message-1","text":"已验证内容","citation_ids":["chunk-1"]}',
    );

    expect(event).toEqual({
      id: 'run-1:2',
      event: 'delta',
      data: {
        run_id: 'run-1',
        sequence_no: 2,
        occurred_at: '2026-09-02T00:00:00+00:00',
        message_id: 'message-1',
        text: '已验证内容',
        citation_ids: ['chunk-1'],
      },
    });
  });

  it('rejects malformed events', () => {
    expect(parseQueryRunStreamEvent('event: delta\ndata: {}')).toBeNull();
  });
});
