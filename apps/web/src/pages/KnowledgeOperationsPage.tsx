import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Empty, Spin } from 'antd';
import { Upload } from 'lucide-react';
import { Navigate, useSearchParams } from 'react-router-dom';

import { listKnowledgeCandidates, listKnowledgeSources, type CandidateQueueResponse, type SourceSiteListResponse } from '@/api/knowledge';
import { getAccessToken } from '@/api/session';

const previewCandidates: CandidateQueueResponse = {
  data: [{ id: 'virtual-candidate-001', batch_id: 'virtual-batch-001', candidate_type: 'policy_clause', created_at: '2026-09-02T00:00:00Z', extraction_confidence: '0.91', extraction_method: 'rule_based', normalization_status: 'normalized', payload: {}, review_reason_safe: null, review_status: 'pending', reviewed_at: null, reviewed_by: null, source_chunk_id: 'virtual:chunk:1', source_document_id: 'virtual-document-001' }],
  meta: { request_id: 'preview-only' },
};
const previewSources: SourceSiteListResponse = {
  data: [{ id: 'virtual-source-001', authority_name: '虚构测试机关', base_url: 'https://example.invalid', collection_method: 'manual', crawl_interval_minutes: null, created_at: '2026-09-02T00:00:00Z', created_by: 'virtual-user-001', domain: 'example.invalid', last_checked_at: null, name: '虚构政策资料源', region_code: '440300', source_level: 'A', status: 'active', updated_at: '2026-09-02T00:00:00Z', whitelist_rules: {} }],
  meta: { request_id: 'preview-only' },
};

function candidateTitle(candidateType: string) {
  return candidateType === 'policy_clause' ? '第一条：适用范围' : `候选：${candidateType}`;
}

export function KnowledgeOperationsPage() {
  const token = getAccessToken();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const candidatesQuery = useQuery({
    queryKey: ['knowledge', 'candidates'], enabled: !preview && token !== null, retry: false,
    queryFn: () => {
      if (token === null) throw new Error('知识候选不可用');
      return listKnowledgeCandidates(token);
    },
  });
  const sourcesQuery = useQuery({
    queryKey: ['knowledge', 'sources'], enabled: !preview && token !== null, retry: false,
    queryFn: () => {
      if (token === null) throw new Error('知识来源不可用');
      return listKnowledgeSources(token);
    },
  });
  if (!preview && token === null) return <Navigate replace to="/" />;

  const candidates = preview ? previewCandidates.data : (candidatesQuery.data?.data ?? []);
  const sources = preview ? previewSources.data : (sourcesQuery.data?.data ?? []);
  const loading = !preview && (candidatesQuery.isLoading || sourcesQuery.isLoading);
  const error = !preview && (candidatesQuery.isError || sourcesQuery.isError);

  return (
    <main className="knowledge-page">
      <div className="directory-head">
        <div><h1>知识运营</h1><p>复杂动作收进分段视图和弹窗，不堆成后台表单墙</p></div>
        <Button disabled icon={<Upload aria-hidden="true" size={15} />}>导入资料</Button>
      </div>
      <Alert className="directory-notice" description="资料导入需要文件和来源元数据；本页未接入上传表单，不会伪造导入成功。" message={preview ? '预览模式：仅展示虚构知识候选' : '正式知识必须经过审核、批次校验和发布'} showIcon type={preview ? 'info' : 'warning'} />
      <div className="review-segment"><span className="is-active">候选审核</span><span>来源</span><span>发布批次</span></div>
      {loading ? <div className="review-state"><Spin tip="正在加载知识运营数据" /></div> : null}
      {error ? <Alert action={<Button size="small" onClick={() => { void candidatesQuery.refetch(); void sourcesQuery.refetch(); }}>重试</Button>} message="知识运营数据加载失败" showIcon type="error" /> : null}
      {!loading && !error ? <div className="knowledge-grid">
        <section className="knowledge-panel">
          <div className="knowledge-panel-title"><h2>待审核候选</h2><Button disabled size="small">批量操作</Button></div>
          {candidates.length === 0 ? <Empty description="暂无待审核候选" /> : candidates.map((item) => <article className="knowledge-candidate" key={item.id}><div><strong>{candidateTitle(item.candidate_type)}</strong><span>{item.candidate_type} · 来源条款 {item.source_chunk_id}</span></div><span className="directory-badge is-amber">{item.review_status}</span></article>)}
        </section>
        <aside className="knowledge-batch-card">
          <h2>当前发布批次</h2><div><span>待审核候选</span><strong>{candidates.length}</strong></div><div><span>已登记来源</span><strong>{sources.length}</strong></div><div><span>状态</span><span className="directory-badge is-amber">等待校验</span></div><p>校验与快照物化需要明确的发布批次，本页不代替该受控流程。</p>
        </aside>
      </div> : null}
    </main>
  );
}
