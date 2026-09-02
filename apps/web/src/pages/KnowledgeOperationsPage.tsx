import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Empty, Form, Input, Modal, Popconfirm, Select, Spin } from 'antd';
import { Plus, Upload } from 'lucide-react';
import { useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';

import { createKnowledgePublishBatch, listApprovedKnowledgeCandidates, listKnowledgeCandidates, listKnowledgePublishBatches, listKnowledgeSources, materializeKnowledgeSnapshot, registerKnowledgeSource, reviewKnowledgeCandidate, uploadKnowledgeDocument, validateKnowledgePublishBatch, type CandidateQueueResponse, type CandidateReviewRequest, type KnowledgeDocumentUpload, type RegisterSourceSiteRequest, type SourceSiteListResponse } from '@/api/knowledge';
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

type ImportFormValues = Omit<KnowledgeDocumentUpload, 'file'>;

export function KnowledgeOperationsPage() {
  const token = getAccessToken();
  const client = useQueryClient();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [decision, setDecision] = useState<'approved' | 'rejected'>('approved');
  const [sourceRegistrationOpen, setSourceRegistrationOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ chunkCount: number; jobStatus: string } | null>(null);
  const [reviewForm] = Form.useForm<CandidateReviewRequest>();
  const [sourceForm] = Form.useForm<RegisterSourceSiteRequest>();
  const [importForm] = Form.useForm<ImportFormValues>();
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
  const approvedQuery = useQuery({ queryKey: ['knowledge', 'approved-candidates'], enabled: !preview && token !== null, retry: false, queryFn: () => { if (token === null) throw new Error('已通过候选不可用'); return listApprovedKnowledgeCandidates(token); } });
  const publishBatchesQuery = useQuery({ queryKey: ['knowledge', 'publish-batches'], enabled: !preview && token !== null, retry: false, queryFn: () => { if (token === null) throw new Error('发布批次不可用'); return listKnowledgePublishBatches(token); } });
  const reviewMutation = useMutation({
    mutationFn: (payload: CandidateReviewRequest) => {
      if (token === null || selectedCandidateId === null) throw new Error('候选审核不可用');
      return reviewKnowledgeCandidate(selectedCandidateId, payload, token);
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['knowledge', 'candidates'] });
      setSelectedCandidateId(null);
      reviewForm.resetFields();
    },
  });
  const sourceMutation = useMutation({
    mutationFn: (payload: RegisterSourceSiteRequest) => {
      if (token === null) throw new Error('知识来源不可用');
      return registerKnowledgeSource(payload, token);
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['knowledge', 'sources'] });
      setSourceRegistrationOpen(false);
      sourceForm.resetFields();
    },
  });
  const importMutation = useMutation({
    mutationFn: (values: ImportFormValues) => {
      if (token === null || importFile === null) throw new Error('请选择要导入的资料文件');
      return uploadKnowledgeDocument({ ...values, file: importFile }, token);
    },
    onSuccess: (response) => {
      setImportResult({ chunkCount: response.data.chunk_count, jobStatus: response.data.job_status });
      setImportOpen(false);
      setImportFile(null);
      importForm.resetFields();
    },
  });
  const publishMutation = useMutation({ mutationFn: (candidateIds: string[]) => { if (token === null) throw new Error('发布批次不可用'); return createKnowledgePublishBatch(candidateIds, token); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ['knowledge', 'publish-batches'] }); } });
  const validateMutation = useMutation({ mutationFn: (batchId: string) => { if (token === null) throw new Error('发布批次不可用'); return validateKnowledgePublishBatch(batchId, token); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ['knowledge', 'publish-batches'] }); } });
  const snapshotMutation = useMutation({ mutationFn: (batchId: string) => { if (token === null) throw new Error('发布批次不可用'); return materializeKnowledgeSnapshot(batchId, token); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ['knowledge', 'publish-batches'] }); } });
  if (!preview && token === null) return <Navigate replace to="/" />;

  const candidates = preview ? previewCandidates.data : (candidatesQuery.data?.data ?? []);
  const sources = preview ? previewSources.data : (sourcesQuery.data?.data ?? []);
  const approvedCandidates = preview ? [] : (approvedQuery.data?.data ?? []);
  const publishBatches = preview ? [] : (publishBatchesQuery.data?.data ?? []);
  const loading = !preview && (candidatesQuery.isLoading || sourcesQuery.isLoading || approvedQuery.isLoading || publishBatchesQuery.isLoading);
  const error = !preview && (candidatesQuery.isError || sourcesQuery.isError || approvedQuery.isError || publishBatchesQuery.isError);
  const selectedCandidate = candidates.find((candidate) => candidate.id === selectedCandidateId);

  const openReview = (candidateId: string, nextDecision: 'approved' | 'rejected') => {
    setSelectedCandidateId(candidateId);
    setDecision(nextDecision);
    reviewForm.resetFields();
    reviewForm.setFieldsValue({ decision: nextDecision });
  };

  return (
    <main className="knowledge-page">
      <div className="directory-head">
        <div><h1>知识运营</h1><p>复杂动作收进分段视图和弹窗，不堆成后台表单墙</p></div>
        <div className="knowledge-page-actions"><Button disabled={preview} icon={<Upload aria-hidden="true" size={15} />} onClick={() => { setImportOpen(true); }}>导入资料</Button><Button disabled={preview} icon={<Plus aria-hidden="true" size={15} />} onClick={() => { setSourceRegistrationOpen(true); }}>登记来源</Button></div>
      </div>
      <Alert className="directory-notice" description="资料导入仅接收关联来源的本地文件；不会下载外部网页、启动爬虫或伪造导入结果。" message={preview ? '预览模式：仅展示虚构知识候选' : '正式知识必须经过审核、批次校验和发布'} showIcon type={preview ? 'info' : 'warning'} />
      <div className="review-segment"><span className="is-active">候选审核</span><span>来源</span><span>发布批次</span></div>
      {loading ? <div className="review-state"><Spin tip="正在加载知识运营数据" /></div> : null}
      {error ? <Alert action={<Button size="small" onClick={() => { void candidatesQuery.refetch(); void sourcesQuery.refetch(); void approvedQuery.refetch(); void publishBatchesQuery.refetch(); }}>重试</Button>} message="知识运营数据加载失败" showIcon type="error" /> : null}
      {importResult !== null ? <Alert className="directory-notice" description={`任务状态：${importResult.jobStatus}；已解析 ${String(importResult.chunkCount)} 个内容分块。仍需候选审核和发布校验。`} message="资料已提交至受控导入流程" showIcon type="success" /> : null}
      {!loading && !error ? <div className="knowledge-grid">
        <section className="knowledge-panel">
          <div className="knowledge-panel-title"><h2>待审核候选</h2><Button disabled size="small">批量操作</Button></div>
          {candidates.length === 0 ? <Empty description="暂无待审核候选" /> : candidates.map((item) => <article className="knowledge-candidate" key={item.id}><div><strong>{candidateTitle(item.candidate_type)}</strong><span>{item.candidate_type} · 来源条款 {item.source_chunk_id}</span></div><div className="knowledge-candidate-actions"><span className="directory-badge is-amber">{item.review_status}</span><Button disabled={preview} size="small" type="text" onClick={() => { openReview(item.id, 'approved'); }}>通过候选</Button><Button danger disabled={preview} size="small" type="text" onClick={() => { openReview(item.id, 'rejected'); }}>退回候选</Button></div></article>)}
        </section>
        <aside className="knowledge-batch-card">
          <h2>来源与发布批次</h2><div><span>待审核候选</span><strong>{candidates.length}</strong></div><div><span>已通过候选</span><strong>{approvedCandidates.length}</strong></div><div><span>已登记来源</span><strong>{sources.length}</strong></div>{sources.length === 0 ? <p>暂无已登记来源。</p> : sources.map((source) => <div className="knowledge-source-row" key={source.id}><span>{source.name}</span><span className="directory-badge is-amber">{source.status}</span></div>)}<Popconfirm cancelText="取消" description="这会创建待校验批次，不会直接发布知识。" disabled={preview || approvedCandidates.length === 0} okText="创建批次" onConfirm={() => { publishMutation.mutate(approvedCandidates.map((candidate) => candidate.id)); }} title="确认创建发布批次？"><Button disabled={preview || approvedCandidates.length === 0} loading={publishMutation.isPending} size="small">创建发布批次</Button></Popconfirm>{publishBatches.map((batch) => <div className="knowledge-source-row" key={batch.id}><span>{batch.status} · {batch.candidate_count} 项</span><span><Button disabled={preview || !['pending_validation', 'validation_failed', 'validated'].includes(batch.status)} loading={validateMutation.isPending} onClick={() => { validateMutation.mutate(batch.id); }} size="small" type="text">校验</Button><Button disabled={preview || batch.status !== 'validated'} loading={snapshotMutation.isPending} onClick={() => { snapshotMutation.mutate(batch.id); }} size="small" type="text">物化快照</Button></span></div>)}<p>创建批次、校验与物化快照分段执行；物化不等于对外发布。</p>
        </aside>
      </div> : null}
      <Modal footer={null} onCancel={() => { setSelectedCandidateId(null); }} open={selectedCandidate !== undefined} title={decision === 'approved' ? '通过知识候选' : '退回知识候选'}>
        <Form<CandidateReviewRequest> form={reviewForm} layout="vertical" onFinish={(values) => { reviewMutation.mutate(values); }}>
          <Form.Item hidden name="decision"><Input type="hidden" /></Form.Item>
          <p className="knowledge-review-candidate">{selectedCandidate === undefined ? '' : candidateTitle(selectedCandidate.candidate_type)}</p>
          <Form.Item label={decision === 'approved' ? '审核说明（可选）' : '退回原因'} name="reason" rules={decision === 'rejected' ? [{ required: true, min: 3, message: '退回原因至少 3 个字符' }] : []}><Input.TextArea maxLength={1000} showCount /></Form.Item>
          {reviewMutation.isError ? <Alert message="候选审核失败，请检查权限或刷新后重试。" showIcon type="error" /> : null}
          <Button htmlType="submit" loading={reviewMutation.isPending} type="primary">确认{decision === 'approved' ? '通过' : '退回'}</Button>
        </Form>
      </Modal>
      <Modal footer={null} onCancel={() => { setSourceRegistrationOpen(false); }} open={sourceRegistrationOpen} title="登记知识来源">
        <Form<RegisterSourceSiteRequest> form={sourceForm} initialValues={{ collection_method: 'manual', region_code: '440300', source_level: 'A' }} layout="vertical" onFinish={(values) => { sourceMutation.mutate(values); }}>
          <Form.Item name="collection_method" noStyle><Input type="hidden" /></Form.Item>
          <Form.Item label="来源名称" name="name" rules={[{ required: true, min: 2, message: '请输入来源名称' }]}><Input maxLength={200} placeholder="例如：深圳税务政策公开栏目" /></Form.Item>
          <Form.Item label="主管机关" name="authority_name" rules={[{ required: true, min: 2, message: '请输入主管机关' }]}><Input maxLength={200} placeholder="例如：国家税务总局深圳市税务局" /></Form.Item>
          <Form.Item label="来源地址" name="base_url" rules={[{ required: true, type: 'url', message: '请输入来源地址' }]}><Input placeholder="https://example.gov.cn/" /></Form.Item>
          <div className="knowledge-source-form-grid"><Form.Item label="地区代码" name="region_code" rules={[{ required: true, pattern: /^\d{6}$/, message: '请输入 6 位地区代码' }]}><Input maxLength={6} /></Form.Item><Form.Item label="来源等级" name="source_level" rules={[{ required: true }]}><Select options={['A', 'B', 'C', 'D'].map((value) => ({ label: `${value} 级`, value }))} /></Form.Item></div>
          <p className="knowledge-review-candidate">登记后状态为草稿，仅保存来源白名单元数据，不会启动下载、爬取或导入。</p>
          {sourceMutation.isError ? <Alert message="来源登记失败，请检查权限或地址后重试。" showIcon type="error" /> : null}
          <Button htmlType="submit" loading={sourceMutation.isPending} type="primary">确认登记</Button>
        </Form>
      </Modal>
      <Modal footer={null} onCancel={() => { setImportOpen(false); }} open={importOpen} title="导入本地资料">
        <Form<ImportFormValues> form={importForm} initialValues={{ docType: 'announcement', regionCode: '440300', sourceLevel: 'A' }} layout="vertical" onFinish={(values) => { importMutation.mutate(values); }}>
          <Form.Item label="关联来源" name="sourceSiteId" rules={[{ required: true, message: '请选择已登记来源' }]}><Select options={sources.map((source) => ({ label: source.name, value: source.id }))} placeholder="选择已登记来源" /></Form.Item>
          <Form.Item label="资料文件" required><input accept=".htm,.html,.pdf,.txt,text/html,application/pdf,text/plain" aria-label="资料文件" onChange={(event) => { setImportFile(event.target.files?.item(0) ?? null); }} type="file" /></Form.Item>
          <div className="knowledge-source-form-grid"><Form.Item label="标题" name="title" rules={[{ required: true, min: 2, message: '请输入资料标题' }]}><Input maxLength={500} /></Form.Item><Form.Item label="文号（可选）" name="docNo"><Input maxLength={200} /></Form.Item></div>
          <Form.Item label="发布机关" name="issuingAuthority" rules={[{ required: true, min: 2, message: '请输入发布机关' }]}><Input maxLength={200} /></Form.Item>
          <Form.Item label="官方原始地址" name="canonicalUrl" rules={[{ required: true, type: 'url', message: '请输入官方原始地址' }]}><Input placeholder="https://example.gov.cn/policy/001" /></Form.Item>
          <div className="knowledge-import-form-grid"><Form.Item label="地区代码" name="regionCode" rules={[{ required: true, pattern: /^\d{6}$/, message: '请输入 6 位地区代码' }]}><Input maxLength={6} /></Form.Item><Form.Item label="资料类型" name="docType"><Select options={[['law', '法律'], ['regulation', '法规'], ['announcement', '公告'], ['interpretation', '解读'], ['guide', '指引'], ['faq', 'FAQ']].map(([value, label]) => ({ label, value }))} /></Form.Item><Form.Item label="来源等级" name="sourceLevel"><Select options={['A', 'B', 'C', 'D'].map((value) => ({ label: `${value} 级`, value }))} /></Form.Item></div>
          <p className="knowledge-review-candidate">仅接收已授权的本地 HTML、PDF 或 TXT 文件。提交后由后端校验、留档和解析，不下载外部网页。</p>
          {importFile === null ? <Alert message="请选择资料文件后提交" showIcon type="info" /> : null}
          {importMutation.isError ? <Alert message="资料导入失败，请检查来源、文件和元数据后重试。" showIcon type="error" /> : null}
          <Button disabled={importFile === null} htmlType="submit" loading={importMutation.isPending} type="primary">提交受控导入</Button>
        </Form>
      </Modal>
    </main>
  );
}
