import { Alert, Card, Space, Tag, Typography } from 'antd';

import type { components } from '@/api/generated/schema';

type RiskFinding = components['schemas']['RuleResultData'];

interface RiskFindingCardProps {
  finding: RiskFinding;
}

const statusPresentation: Record<string, { color: string; label: string }> = {
  hit: { color: 'red', label: '已命中' },
  not_hit: { color: 'default', label: '未命中' },
  need_info: { color: 'gold', label: '待补充事实' },
  manual_review: { color: 'orange', label: '需人工判断' },
};

export function RiskFindingCard({ finding }: RiskFindingCardProps) {
  const status = statusPresentation[finding.status] ?? { color: 'default', label: '未知状态' };

  return (
    <Card size="small" title="事项风险审查">
      <Space direction="vertical" size={12} className="full-width">
        <Space wrap>
          <Tag color={status.color}>{status.label}</Tag>
          {finding.severity === null ? null : <Tag color="red">{finding.severity}</Tag>}
          <Typography.Text>规则版本：{finding.rule_version_id}</Typography.Text>
        </Space>
        {finding.missing_fact_keys.length > 0 ? (
          <Alert
            type="warning"
            showIcon
            message={`待补充事实：${finding.missing_fact_keys.join('、')}`}
          />
        ) : null}
        {finding.basis_chunk_ids.length > 0 ? (
          <Typography.Text type="secondary">
            依据条款：{finding.basis_chunk_ids.join('、')}
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary">当前规则未返回可展示的依据条款标识。</Typography.Text>
        )}
        <Typography.Text type="secondary">
          风险结论由确定性规则生成，模型不能修改。
        </Typography.Text>
      </Space>
    </Card>
  );
}
