import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Descriptions,
  Empty,
  Form,
  Input,
  Layout,
  List,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { searchPolicies, type PolicySearchResponse } from '@/api/policies';
import { clearAccessToken, getAccessToken } from '@/api/session';

interface SearchFormValues {
  query: string;
  regionCode: string;
  businessDate: string;
}

const { Header, Content, Footer } = Layout;

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

  function logout() {
    clearAccessToken();
    void navigate('/');
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header policy-header">
        <div>
          <Typography.Title level={3} className="brand-title">
            TaxMind Pro
          </Typography.Title>
          <Typography.Text className="brand-subtitle">政策检索与证据详情</Typography.Text>
        </div>
        <Button ghost onClick={logout}>
          {isPreview ? '返回登录' : '退出'}
        </Button>
      </Header>
      <Content className="app-content">
        <Space direction="vertical" size={24} className="full-width">
          <Alert
            type={isPreview ? 'info' : 'warning'}
            showIcon
            message={isPreview ? '预览模式：仅展示虚构示例' : '内部专业辅助：检索结果不是正式税务意见'}
            description={
              isPreview
                ? '该页面没有访问后端、模型或真实政策资料；登录后才能进行受权限保护的正式检索。'
                : '系统仅展示已发布、有效的证据条款。请结合业务事实、地区口径和人工审核作出最终判断。'
            }
          />
          <Card title="检索条件">
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
                  <Button type="primary" htmlType="submit" loading={!isPreview && search.isFetching}>
                    {isPreview ? '查看虚构预览结果' : '检索已发布政策'}
                  </Button>
                </Form.Item>
              </div>
            </Form>
          </Card>
          <Button onClick={() => void navigate(`/cases${isPreview ? '?preview=1' : ''}`)}>
            前往事项工作台
          </Button>
          <section aria-live="polite">
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
            {evidenceData !== undefined && evidenceData.data.length > 0 ? (
              <List
                className="policy-results"
                dataSource={evidenceData.data}
                renderItem={(evidence) => (
                  <List.Item key={evidence.chunk.id}>
                    <Card className="evidence-card" title={evidence.document.title}>
                      <Space direction="vertical" size={12} className="full-width">
                        <Space wrap>
                          <Tag color="green">已发布</Tag>
                          <Tag>{evidence.document.doc_no ?? '无文号'}</Tag>
                          <Tag>{evidence.chunk.clause_label ?? evidence.chunk.heading_path}</Tag>
                          <Tag color="cyan">
                            {evidence.retrieval_reason === 'mysql_exact'
                              ? '精确检索'
                              : '受控检索'}
                          </Tag>
                          {evidence.region_match === 'national_only' ? (
                            <Tag color="gold">全国口径回退</Tag>
                          ) : (
                            <Tag color="blue">本地地区匹配</Tag>
                          )}
                        </Space>
                        <Typography.Paragraph className="evidence-content">
                          {evidence.chunk.content_text}
                        </Typography.Paragraph>
                        <Descriptions size="small" column={{ xs: 1, sm: 2 }}>
                          <Descriptions.Item label="发文机关">
                            {evidence.document.issuing_authority}
                          </Descriptions.Item>
                          <Descriptions.Item label="有效期">
                            {evidence.chunk.effective_start ?? '未标注'} 至{' '}
                            {evidence.chunk.effective_end ?? '持续有效'}
                          </Descriptions.Item>
                        </Descriptions>
                        <Collapse
                          size="small"
                          items={[
                            {
                              key: 'source',
                              label: '查看来源与版本信息',
                              children: (
                                <Space direction="vertical" size={4}>
                                  <Typography.Text>版本：v{evidence.version.version_no}</Typography.Text>
                                  <Typography.Link href={evidence.document.canonical_url} target="_blank">
                                    官方公开来源
                                  </Typography.Link>
                                  <Typography.Text type="secondary">
                                    来源条款标识：{evidence.chunk.source_chunk_id}
                                  </Typography.Text>
                                </Space>
                              ),
                            },
                          ]}
                        />
                      </Space>
                    </Card>
                  </List.Item>
                )}
              />
            ) : null}
          </section>
        </Space>
      </Content>
      <Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer>
    </Layout>
  );
}
