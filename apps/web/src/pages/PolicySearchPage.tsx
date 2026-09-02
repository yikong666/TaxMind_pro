import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Space,
  Spin,
  Typography,
} from 'antd';
import { Eye, ExternalLink, Search } from 'lucide-react';
import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { searchPolicies, type PolicySearchResponse } from '@/api/policies';
import { getAccessToken } from '@/api/session';

interface SearchFormValues {
  query: string;
  regionCode: string;
  businessDate: string;
}

const previewData: PolicySearchResponse = {
  data: [
    {
      document: {
        id: 'virtual-document-001',
        title: '虚构示例政策资料（仅供界面预览）',
        doc_no: 'TEST-2026-001',
        doc_type: 'announcement',
        source_level: 'A',
        issuing_authority: '虚构测试机关',
        region_code: '000000',
        effective_start: '2026-01-01',
        effective_end: null,
        policy_status: 'active',
        canonical_url: 'https://example.invalid/virtual-policy',
        current_version_id: 'virtual-version-001',
        review_status: 'published',
      },
      version: {
        id: 'virtual-version-001',
        version_no: 1,
        source_url: 'https://example.invalid/virtual-policy',
        mime_type: 'text/plain',
        content_hash_sha256: 'a'.repeat(64),
        review_status: 'published',
        published_at: '2026-01-01T00:00:00Z',
      },
      chunk: {
        id: 'virtual-chunk-001',
        source_chunk_id: 'virtual:v1:article_1',
        chunk_order: 1,
        chunk_type: 'article',
        heading_path: '第一条',
        clause_label: '第一条',
        content_text: '这是用于界面预览的虚构条款，不构成政策依据或专业结论。',
        effective_start: '2026-01-01',
        effective_end: null,
        region_code: '000000',
        policy_status: 'active',
        review_status: 'published',
        index_status: 'pending',
      },
      region_match: 'national_only',
      retrieval_reason: 'mysql_exact',
    },
  ],
  meta: { request_id: 'preview-only' },
};

export function PolicySearchPage() {
  const navigate = useNavigate();
  const [searchParameters] = useSearchParams();
  const accessToken = getAccessToken();
  const isPreview = searchParameters.get('preview') === '1';
  const [submitted, setSubmitted] = useState<SearchFormValues | null>(null);
  const [visibleEvidence, setVisibleEvidence] = useState<PolicySearchResponse['data'][number] | null>(
    null,
  );
  const search = useQuery({
    queryKey: ['policies', 'search', submitted],
    queryFn: () => {
      if (submitted === null || accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return searchPolicies(submitted, accessToken);
    },
    enabled: submitted !== null && accessToken !== null && !isPreview,
    retry: false,
  });
  const evidenceData = isPreview ? previewData : search.data;

  if (accessToken === null && !isPreview) {
    return <Navigate to="/" replace />;
  }

  function submit(values: SearchFormValues) {
    setSubmitted({
      ...values,
      query: values.query.trim(),
    });
  }

  return (
    <main className="directory-page">
      <div className="directory-head">
        <div>
          <h1>查找政策证据</h1>
          <p>搜索、筛选和证据详情保持在一个轻量页面中</p>
        </div>
        <Button
          className="directory-return"
          onClick={() => {
            void navigate(`/cases${isPreview ? '?preview=1' : ''}`);
          }}
        >
          返回工作台
        </Button>
      </div>
      <Alert
        className="directory-notice"
        type={isPreview ? 'info' : 'warning'}
        showIcon
        message={isPreview ? '预览模式：仅展示虚构示例' : '内部专业辅助：检索结果不是正式税务意见'}
        description={
          isPreview
            ? '该页面没有访问后端、模型或真实政策资料；登录后才能进行受权限保护的正式检索。'
            : '系统仅展示已发布、有效的证据条款。请结合业务事实、地区口径和人工审核作出最终判断。'
        }
      />
      <section className="directory-panel">
        <div className="directory-filter">
            <Form<SearchFormValues>
              layout="vertical"
              initialValues={{ regionCode: '440300', businessDate: '2026-08-31' }}
              onFinish={submit}
            >
              <div className="policy-search-grid">
                <Form.Item
                  label="关键词或文号"
                  name="query"
                  rules={[{ required: true, message: '请输入关键词或文号' }]}
                >
                  <Input placeholder="例如：小规模纳税人、TEST-2026-001" allowClear />
                </Form.Item>
                <Form.Item
                  label="地区代码"
                  name="regionCode"
                  rules={[{ required: true, pattern: /^\d{6}$/, message: '请输入六位地区代码' }]}
                >
                  <Input inputMode="numeric" maxLength={6} />
                </Form.Item>
                <Form.Item label="业务发生日" name="businessDate" rules={[{ required: true }]}>
                  <Input type="date" />
                </Form.Item>
                <Form.Item className="policy-search-action">
                  <Button icon={<Search aria-hidden="true" size={15} />} type="primary" htmlType="submit" loading={!isPreview && search.isFetching}>
                    {isPreview ? '搜索预览' : '搜索'}
                  </Button>
                </Form.Item>
              </div>
            </Form>
        </div>
        <section aria-live="polite" className="directory-results">
            {!isPreview && search.isFetching ? <Spin tip="正在按地区和业务日期筛选已发布证据…" /> : null}
            {!isPreview && search.isError ? (
              <Alert
                type="error"
                showIcon
                message="政策检索未完成"
                description="请检查登录权限、后端服务和检索条件后重试。"
                action={<Button onClick={() => void search.refetch()}>重试</Button>}
              />
            ) : null}
            {evidenceData !== undefined && evidenceData.data.length === 0 ? (
              <Empty description="当前条件下没有可用的已发布证据" />
            ) : null}
          {evidenceData?.data.map((evidence) => (
            <article className="directory-list-item" key={evidence.chunk.id}>
              <div>
                <strong>{evidence.document.title}</strong>
                <p>{evidence.document.doc_no ?? '无文号'} · {evidence.chunk.clause_label ?? evidence.chunk.heading_path} · {evidence.document.issuing_authority}</p>
                <span className="directory-excerpt">{evidence.chunk.content_text}</span>
              </div>
              <div className="directory-list-actions">
                <span className={`directory-badge ${evidence.region_match === 'national_only' ? 'is-amber' : 'is-blue'}`}>
                  {evidence.region_match === 'national_only' ? '全国回退' : '本地匹配'}
                </span>
                <Button
                  aria-label="查看"
                  icon={<Eye aria-hidden="true" size={15} />}
                  size="small"
                  onClick={() => {
                    setVisibleEvidence(evidence);
                  }}
                >
                  查看
                </Button>
              </div>
            </article>
          ))}
        </section>
      </section>
      <Drawer
        title="条款证据详情"
        width={640}
        open={visibleEvidence !== null}
        onClose={() => {
          setVisibleEvidence(null);
        }}
        destroyOnHidden
      >
        {visibleEvidence !== null ? (
          <Space direction="vertical" size={16} className="full-width">
            {visibleEvidence.region_match === 'national_only' ? (
              <Alert
                type="warning"
                showIcon
                message="全国口径回退"
                description="当前未匹配到本地地区口径；该条款不能替代广东省或深圳市的办理依据。"
              />
            ) : (
              <Alert type="success" showIcon message="本地地区匹配" />
            )}
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="文件标题">
                {visibleEvidence.document.title}
              </Descriptions.Item>
              <Descriptions.Item label="文号">
                {visibleEvidence.document.doc_no ?? '无文号'}
              </Descriptions.Item>
              <Descriptions.Item label="发文机关">
                {visibleEvidence.document.issuing_authority}
              </Descriptions.Item>
              <Descriptions.Item label="条款">
                {visibleEvidence.chunk.clause_label ?? visibleEvidence.chunk.heading_path}
              </Descriptions.Item>
              <Descriptions.Item label="有效期">
                {visibleEvidence.chunk.effective_start ?? '未标注'} 至{' '}
                {visibleEvidence.chunk.effective_end ?? '持续有效'}
              </Descriptions.Item>
              <Descriptions.Item label="审核状态">
                {visibleEvidence.chunk.review_status === 'published' ? '已发布' : '未发布'}
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                v{visibleEvidence.version.version_no}
              </Descriptions.Item>
              <Descriptions.Item label="来源条款标识">
                {visibleEvidence.chunk.source_chunk_id}
              </Descriptions.Item>
            </Descriptions>
            <section className="evidence-drawer-content">
              <strong>条款原文</strong>
              <Typography.Paragraph className="evidence-content">
                {visibleEvidence.chunk.content_text}
              </Typography.Paragraph>
            </section>
            <Typography.Link href={visibleEvidence.document.canonical_url} target="_blank">
              <ExternalLink aria-hidden="true" size={14} />
              官方公开来源
            </Typography.Link>
          </Space>
        ) : null}
      </Drawer>
    </main>
  );
}
