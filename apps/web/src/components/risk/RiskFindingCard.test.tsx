import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RiskFindingCard } from '@/components/risk/RiskFindingCard';

describe('RiskFindingCard', () => {
  it('renders a deterministic manual-review result with missing facts and evidence identifiers', () => {
    render(
      <RiskFindingCard
        finding={{
          rule_version_id: 'RISK-INVOICE-001-v2',
          status: 'manual_review',
          severity: null,
          missing_fact_keys: ['invoice_amount'],
          basis_chunk_ids: ['policy:invoice:article_12'],
        }}
      />,
    );

    expect(screen.getByText('需人工判断')).toBeInTheDocument();
    expect(screen.getByText('规则版本：RISK-INVOICE-001-v2')).toBeInTheDocument();
    expect(screen.getByText('待补充事实：invoice_amount')).toBeInTheDocument();
    expect(screen.getByText('依据条款：policy:invoice:article_12')).toBeInTheDocument();
    expect(screen.getByText('风险结论由确定性规则生成，模型不能修改。')).toBeInTheDocument();
  });
});
