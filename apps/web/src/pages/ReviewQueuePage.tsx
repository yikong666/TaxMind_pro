import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Empty, Spin } from 'antd';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { listReviewTasks, type ReviewQueueResponse } from '@/api/reviews';
import { getAccessToken } from '@/api/session';

const previewData: ReviewQueueResponse = {
  data: [{ id: 'virtual-review-001', case_id: 'virtual-case-001', profile_version: 1, query_run_id: 'virtual-run-001', submitted_by: 'virtual-consultant', assigned_to: null, status: 'pending_review', priority: 'normal', package_summary: { fact_keys: ['invoice_intent'], rule_version_ids: ['RISK-INVOICE-001-v1'], follow_up_fact_keys: ['small_low_profit_status'] }, version_no: 1, submitted_at: '2026-09-01T00:00:00Z', resolved_at: null }],
  meta: { request_id: 'preview-only' },
};

function asTextList(value: unknown) {
  return Array.isArray(value) && value.every((item) => typeof item === 'string') ? value.join('、') : '';
}

export function ReviewQueuePage() {
  const token = getAccessToken();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const query = useQuery({
    queryKey: ['review-tasks'], enabled: !preview && token !== null, retry: false,
    queryFn: () => {
      if (token === null) throw new Error('审核队列不可用');
      return listReviewTasks(token);
    },
  });
  if (!preview && token === null) return <Navigate replace to="/" />;
  const data = preview ? previewData : query.data;

  return (
    <main className="review-queue-page">
      <div className="directory-head">
        <div><h1>待审核</h1><p>先处理风险与事实缺口，而不是展示大段摘要</p></div>
        <Button className="directory-return" onClick={() => void navigate(`/cases${preview ? '?preview=1' : ''}`)}>返回工作台</Button>
      </div>
      <Alert className="directory-notice" message={preview ? '预览模式：仅展示虚构审核任务' : '审核决定必须基于事实、证据和确定性规则'} showIcon type={preview ? 'info' : 'warning'} />
      <div className="review-segment"><span className="is-active">待处理</span><span>正式状态以审核服务为准</span></div>
      {query.isFetching && !preview ? <div className="review-state"><Spin tip="正在加载审核队列" /></div> : null}
      {query.isError && !preview ? <Alert action={<Button size="small" onClick={() => void query.refetch()}>重试</Button>} message="审核队列加载失败" showIcon type="error" /> : null}
      {!query.isFetching && !query.isError && data?.data.length === 0 ? <div className="review-state"><Empty description="暂无待处理审核任务" /></div> : null}
      {data !== undefined && data.data.length > 0 ? (
        <section className="review-table-panel">
          <table><thead><tr><th>事项</th><th>规则</th><th>事实</th><th>提交人</th><th aria-label="操作" /></tr></thead><tbody>{data.data.map((task) => {
            const rules = asTextList(task.package_summary.rule_version_ids);
            const gaps = asTextList(task.package_summary.follow_up_fact_keys);
            return <tr key={task.id}><td><strong>事项 {task.case_id}</strong><span>画像 v{task.profile_version} · 任务 v{task.version_no}</span></td><td><span className="directory-badge is-amber">{rules || '待核验'}</span></td><td>{gaps ? <span className="directory-badge is-amber">缺：{gaps}</span> : '完整'}</td><td>{task.submitted_by}</td><td><Button aria-label="审核" size="small" type="text" onClick={() => void navigate(`/reviews/${task.id}${preview ? '?preview=1' : ''}`)}>审核</Button></td></tr>;
          })}</tbody></table>
          <span className="sr-only">规则：{asTextList(data.data[0]?.package_summary.rule_version_ids)}</span>
          <span className="sr-only">待补充：{asTextList(data.data[0]?.package_summary.follow_up_fact_keys)}</span>
        </section>
      ) : null}
    </main>
  );
}
