import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Empty, Form, Input, Layout, Select, Space, Spin, Typography } from 'antd';
import { useState } from 'react';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { getReviewTask, recordReviewAction } from '@/api/reviews';
import { getAccessToken } from '@/api/session';

const { Header, Content, Footer } = Layout;
const decisions = [{ value: 'approved', label: '通过' }, { value: 'conditionally_approved', label: '有条件通过' }, { value: 'returned', label: '退回修改' }, { value: 'escalated', label: '升级审核' }];
type Decision = 'approved' | 'conditionally_approved' | 'returned' | 'escalated';
interface ReviewFormValues { decision: Decision; comment?: string }

export function ReviewDetailPage() {
  const token = getAccessToken(); const navigate = useNavigate(); const { taskId = 'virtual-review-001' } = useParams(); const [params] = useSearchParams(); const preview = params.get('preview') === '1'; const [result, setResult] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ['review-task', taskId], enabled: !preview && token !== null, retry: false, queryFn: () => { if (token === null) throw new Error('审核详情不可用'); return getReviewTask(taskId, token); } });
  const action = useMutation({ mutationFn: (values: ReviewFormValues) => { if (token === null) throw new Error('审核决定不可用'); const version = detail.data?.data.version_no; if (version === undefined) throw new Error('审核任务尚未加载'); return recordReviewAction(taskId, { ...values, expected_version_no: version }, token); }, onSuccess: (value) => { setResult(value.data.status); } });
  if (!preview && token === null) return <Navigate to="/" replace />;
  const summary = preview ? { profile_version: 1, fact_keys: ['invoice_intent'], rule_version_ids: ['RISK-INVOICE-001-v1'], follow_up_fact_keys: ['small_low_profit_status'] } : detail.data?.data.package_summary;
  function submit(values: ReviewFormValues) { if (preview) { setResult(values.decision); } else { action.mutate(values); } }
  return <Layout className="app-shell"><Header className="app-header policy-header"><div><Typography.Title level={3} className="brand-title">TaxMind Pro</Typography.Title><Typography.Text className="brand-subtitle">审核详情</Typography.Text></div><Button onClick={() => { void navigate(`/reviews${preview ? '?preview=1' : ''}`); }}>返回审核队列</Button></Header><Content className="app-content"><Space direction="vertical" size={24} className="full-width"><Alert type="warning" showIcon message="审核决定不会修改原始事实、风险命中或规则等级" />{detail.isFetching && !preview ? <Spin /> : null}{detail.isError && !preview ? <Alert type="error" message="审核包加载失败" /> : null}{summary === undefined ? <Empty description="审核包不可用" /> : <Card title="记录审核决定"><Form<ReviewFormValues> layout="vertical" initialValues={{ decision: 'approved' }} onFinish={submit}><Form.Item label="决定" name="decision" rules={[{ required: true }]}><Select options={decisions} /></Form.Item><Form.Item label="审核意见" name="comment"><Input.TextArea rows={4} maxLength={1000} /></Form.Item><Button type="primary" htmlType="submit" loading={action.isPending}>记录审核决定</Button></Form>{result !== null ? <Alert type="success" message={`审核决定已记录：${result}`} /> : null}</Card>}</Space></Content><Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer></Layout>;
}
