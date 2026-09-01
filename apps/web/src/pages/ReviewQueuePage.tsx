import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Empty, Layout, List, Space, Spin, Tag, Typography } from 'antd';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { listReviewTasks, type ReviewQueueResponse } from '@/api/reviews';
import { getAccessToken } from '@/api/session';

const { Header, Content, Footer } = Layout;

const previewData: ReviewQueueResponse = {
  data: [{ id: 'virtual-review-001', case_id: 'virtual-case-001', profile_version: 1, query_run_id: 'virtual-run-001', submitted_by: 'virtual-consultant', assigned_to: null, status: 'pending_review', priority: 'normal', package_summary: { fact_keys: ['invoice_intent'], rule_version_ids: ['RISK-INVOICE-001-v1'], follow_up_fact_keys: ['small_low_profit_status'] }, version_no: 1, submitted_at: '2026-09-01T00:00:00Z', resolved_at: null }], meta: { request_id: 'preview-only' },
};

export function ReviewQueuePage() {
  const token = getAccessToken();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const query = useQuery({ queryKey: ['review-tasks'], enabled: !preview && token !== null, retry: false, queryFn: () => {
    if (token === null) throw new Error('审核队列不可用');
    return listReviewTasks(token);
  } });
  if (!preview && token === null) return <Navigate to="/" replace />;
  const data = preview ? previewData : query.data;
  return <Layout className="app-shell"><Header className="app-header policy-header"><div><Typography.Title level={3} className="brand-title">TaxMind Pro</Typography.Title><Typography.Text className="brand-subtitle">审核队列</Typography.Text></div><Button onClick={() => void navigate(`/cases${preview ? '?preview=1' : ''}`)}>事项工作台</Button></Header><Content className="app-content"><Space direction="vertical" size={24} className="full-width"><Alert type={preview ? 'info' : 'warning'} showIcon message={preview ? '预览模式：仅展示虚构审核任务' : '审核决定必须基于事实、证据和确定性规则'} /><section aria-live="polite">{query.isFetching && !preview ? <Spin /> : null}{query.isError && !preview ? <Alert type="error" message="审核队列加载失败" action={<Button onClick={() => void query.refetch()}>重试</Button>} /> : null}{data?.data.length === 0 ? <Empty description="暂无待处理审核任务" /> : null}<List dataSource={data?.data ?? []} renderItem={(task) => <List.Item key={task.id}><Card title={`事项 ${task.case_id}`} className="full-width"><Space direction="vertical"><Space wrap><Tag color="blue">画像 v{task.profile_version}</Tag><Tag color="gold">{task.status}</Tag><Tag>版本 {task.version_no}</Tag></Space><Typography.Text>事实：{((task.package_summary.fact_keys as string[] | undefined) ?? []).join('、') || '无'}</Typography.Text><Typography.Text>规则：{((task.package_summary.rule_version_ids as string[] | undefined) ?? []).join('、') || '待核验'}</Typography.Text><Typography.Text type="secondary">待补充：{((task.package_summary.follow_up_fact_keys as string[] | undefined) ?? []).join('、') || '无'}</Typography.Text><Button onClick={() => void navigate(`/reviews/${task.id}${preview ? '?preview=1' : ''}`)}>查看审核包</Button></Space></Card></List.Item>} /></section></Space></Content><Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer></Layout>;
}
