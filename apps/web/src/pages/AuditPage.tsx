import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Empty, Spin } from 'antd';
import { Navigate, useSearchParams } from 'react-router-dom';

import { searchAuditLogs, type AuditLogSearchResponse } from '@/api/audit';
import { getAccessToken } from '@/api/session';

const previewData: AuditLogSearchResponse = { data: [{ id: 'virtual-audit-001', action_code: 'review.task.action_recorded', resource_type: 'review_task', resource_id: 'virtual-review-001', actor_user_id: 'virtual-reviewer', request_id: 'preview-only', result: 'success', summary_safe: '虚构审核决定已记录。', occurred_at: '2026-09-01T00:00:00Z' }], meta: { request_id: 'preview-only' } };

export function AuditPage() {
  const token = getAccessToken();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const query = useQuery({ queryKey: ['audit-logs'], enabled: !preview && token !== null, retry: false, queryFn: () => {
    if (token === null) throw new Error('审计日志不可用');
    return searchAuditLogs(token);
  } });
  if (!preview && token === null) return <Navigate replace to="/" />;
  const data = preview ? previewData : query.data;
  return <main className="audit-page">
    <div className="directory-head"><div><h1>操作审计</h1><p>按需筛选，不展示敏感审计快照正文</p></div></div>
    <Alert className="directory-notice" message={preview ? '预览模式：仅展示虚构审计记录' : '仅展示脱敏摘要；不提供审计前后敏感原文'} showIcon type={preview ? 'info' : 'warning'} />
    {query.isFetching && !preview ? <div className="review-state"><Spin tip="正在加载审计记录" /></div> : null}
    {query.isError && !preview ? <Alert action={<Button size="small" onClick={() => void query.refetch()}>重试</Button>} message="审计日志加载失败或无权限" showIcon type="error" /> : null}
    {!query.isFetching && !query.isError && data?.data.length === 0 ? <div className="review-state"><Empty description="暂无可查看的审计记录" /></div> : null}
    {data !== undefined && data.data.length > 0 ? <section className="audit-table-panel"><table><thead><tr><th>时间</th><th>动作</th><th>资源</th><th>结果</th><th>摘要</th></tr></thead><tbody>{data.data.map((item) => <tr key={item.id}><td>{new Date(item.occurred_at).toLocaleString()}</td><td>{item.action_code}</td><td>{item.resource_id ?? '系统级事件'}</td><td><span className="directory-badge is-blue">{item.result}</span></td><td>{item.summary_safe ?? '无可展示的脱敏摘要'}</td></tr>)}</tbody></table></section> : null}
  </main>;
}
