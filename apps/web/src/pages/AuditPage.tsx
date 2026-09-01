import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Empty, Layout, List, Space, Spin, Tag, Typography } from 'antd';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { searchAuditLogs, type AuditLogSearchResponse } from '@/api/audit';
import { getAccessToken } from '@/api/session';

const { Header, Content, Footer } = Layout;
const previewData: AuditLogSearchResponse = { data: [{ id: 'virtual-audit-001', action_code: 'review.task.action_recorded', resource_type: 'review_task', resource_id: 'virtual-review-001', actor_user_id: 'virtual-reviewer', request_id: 'preview-only', result: 'success', summary_safe: '虚构审核决定已记录。', occurred_at: '2026-09-01T00:00:00Z' }], meta: { request_id: 'preview-only' } };

export function AuditPage() {
  const token = getAccessToken();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const query = useQuery({ queryKey: ['audit-logs'], enabled: !preview && token !== null, retry: false, queryFn: () => {
    if (token === null) throw new Error('审计日志不可用');
    return searchAuditLogs(token);
  } });
  if (!preview && token === null) return <Navigate to="/" replace />;
  const data = preview ? previewData : query.data;
  return <Layout className="app-shell"><Header className="app-header policy-header"><div><Typography.Title level={3} className="brand-title">TaxMind Pro</Typography.Title><Typography.Text className="brand-subtitle">操作审计</Typography.Text></div><Button onClick={() => void navigate(`/cases${preview ? '?preview=1' : ''}`)}>事项工作台</Button></Header><Content className="app-content"><Space direction="vertical" size={24} className="full-width"><Alert type={preview ? 'info' : 'warning'} showIcon message={preview ? '预览模式：仅展示虚构审计记录' : '仅展示脱敏摘要；不提供审计前后敏感原文'} /><section aria-live="polite">{query.isFetching && !preview ? <Spin /> : null}{query.isError && !preview ? <Alert type="error" message="审计日志加载失败或无权限" action={<Button onClick={() => void query.refetch()}>重试</Button>} /> : null}{data?.data.length === 0 ? <Empty description="暂无可查看的审计记录" /> : null}<List dataSource={data?.data ?? []} renderItem={(item) => <List.Item key={item.id}><Card className="full-width" title={item.action_code}><Space direction="vertical"><Space wrap><Tag>{item.resource_type}</Tag><Tag color={item.result === 'success' ? 'green' : 'red'}>{item.result}</Tag></Space><Typography.Text>资源：{item.resource_id ?? '系统级事件'} · 请求：{item.request_id}</Typography.Text>{item.summary_safe ? <Typography.Text>摘要：{item.summary_safe}</Typography.Text> : <Typography.Text type="secondary">无可展示的脱敏摘要</Typography.Text>}<Typography.Text type="secondary">{new Date(item.occurred_at).toLocaleString()}</Typography.Text></Space></Card></List.Item>} /></section></Space></Content><Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer></Layout>;
}
