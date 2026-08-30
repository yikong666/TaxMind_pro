import { Alert, Button, Card, Skeleton, Space, Tag, Typography } from 'antd';

import { useLiveness } from '@/api/health';

export function ApiHealthCard() {
  const health = useLiveness();

  if (health.isPending) {
    return (
      <Card title="服务连接">
        <Skeleton active paragraph={{ rows: 2 }} />
      </Card>
    );
  }

  if (health.isError) {
    return (
      <Card title="服务连接">
        <Space direction="vertical" size={16} className="full-width">
          <Alert
            type="error"
            showIcon
            message="后端服务暂不可用"
            description={health.error.message}
          />
          <Button onClick={() => void health.refetch()}>重试连接</Button>
        </Space>
      </Card>
    );
  }

  return (
    <Card title="服务连接">
      <Space direction="vertical" size={8}>
        <Space>
          <Tag color="success">API 存活</Tag>
          <Typography.Text code>{health.data.data.status}</Typography.Text>
        </Space>
        <Typography.Text type="secondary">
          请求标识：{health.data.meta.request_id}
        </Typography.Text>
      </Space>
    </Card>
  );
}