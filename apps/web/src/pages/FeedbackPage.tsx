import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Empty, Form, Input, List, Select, Spin, Tag, Typography } from 'antd';
import { Navigate, useSearchParams } from 'react-router-dom';

import { createFeedbackItem, listFeedbackItems, type FeedbackListResponse } from '@/api/feedback';
import { getAccessToken } from '@/api/session';

type FeedbackForm = { case_id?: string; resource_type: 'case' | 'query_run'; resource_id: string; location_key?: string; error_type: 'citation_error' | 'policy_scope_error' | 'risk_rule_error' | 'procedure_error' | 'other'; description: string };
const previewData: FeedbackListResponse = { data: [{ id: 'virtual-feedback-001', case_id: 'virtual-case-001', profile_version: 1, resource_type: 'query_run', resource_id: 'virtual-run-001', location_key: 'risk-card:RISK-001', error_type: 'citation_error', description_safe: '虚构反馈：请复核引用条款。', status: 'submitted', linked_knowledge_object_id: null, resolution_safe: null, submitted_by: 'virtual-consultant', handled_by: null, version_no: 1, submitted_at: '2026-09-01T00:00:00Z', resolved_at: null }], meta: { request_id: 'preview-only' } };

export function FeedbackPage() {
  const token = getAccessToken(); const client = useQueryClient(); const [params] = useSearchParams(); const preview = params.get('preview') === '1';
  const query = useQuery({ queryKey: ['feedback-items'], enabled: !preview && token !== null, retry: false, queryFn: () => { if (token === null) throw new Error('反馈不可用'); return listFeedbackItems(token); } });
  const mutation = useMutation({ mutationFn: (values: FeedbackForm) => { if (token === null) throw new Error('反馈提交不可用'); return createFeedbackItem(values, token); }, onSuccess: () => { void client.invalidateQueries({ queryKey: ['feedback-items'] }); } });
  if (!preview && token === null) return <Navigate replace to="/" />;
  const data = preview ? previewData : query.data;
  return <main className="feedback-page"><div className="directory-head"><div><h1>反馈纠错</h1><p>处理动作在抽屉中完成，列表只保留关键状态</p></div></div><Alert className="directory-notice" message={preview ? '预览模式：仅展示虚构反馈' : '仅提交脱敏事实；反馈不会直接改写正式知识'} showIcon type={preview ? 'info' : 'warning'} />
    <div className="feedback-grid"><section className="feedback-form-card"><h2>提交反馈</h2><Form<FeedbackForm> layout="vertical" initialValues={{ resource_type: 'query_run', error_type: 'citation_error' }} onFinish={(values) => { mutation.mutate(values); }}><div className="policy-search-grid"><Form.Item label="资源类型" name="resource_type" rules={[{ required: true }]}><Select options={[{ value: 'query_run', label: '查询运行' }, { value: 'case', label: '事项' }]} /></Form.Item><Form.Item label="资源 ID" name="resource_id" rules={[{ required: true }]}><Input /></Form.Item><Form.Item label="错误类型" name="error_type" rules={[{ required: true }]}><Select options={['citation_error', 'policy_scope_error', 'risk_rule_error', 'procedure_error', 'other'].map((value) => ({ value, label: value }))} /></Form.Item></div><Form.Item label="反馈说明" name="description" rules={[{ required: true, min: 3 }]}><Input.TextArea maxLength={1000} showCount /></Form.Item><Button disabled={preview} htmlType="submit" loading={mutation.isPending} type="primary">提交反馈</Button>{mutation.isSuccess ? <Typography.Text type="success">反馈已提交，等待处理。</Typography.Text> : null}{mutation.isError ? <Typography.Text type="danger">反馈提交失败，请检查权限与资源范围。</Typography.Text> : null}</Form></section>
      <section className="feedback-list-card" aria-live="polite"><h2>待处理反馈</h2>{query.isFetching && !preview ? <Spin /> : null}{query.isError && !preview ? <Alert action={<Button size="small" onClick={() => void query.refetch()}>重试</Button>} message="反馈列表加载失败" type="error" /> : null}{data?.data.length === 0 ? <Empty description="尚未提交反馈" /> : null}<List dataSource={data?.data ?? []} renderItem={(item) => <List.Item key={item.id}><div><strong>{item.error_type}</strong><span>{item.resource_type} · {item.resource_id}</span><p>{item.description_safe}</p></div><Tag color="blue">{item.status}</Tag></List.Item>} /></section></div>
  </main>;
}
