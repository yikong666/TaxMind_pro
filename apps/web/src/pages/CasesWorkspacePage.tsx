import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Layout,
  List,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import {
  confirmCaseFacts,
  createCase,
  getCase,
  listCases,
  type CaseDetailResponse,
  type CasesResponse,
  type ConfirmFactsRequest,
  type CreateCaseRequest,
} from '@/api/cases';
import {
  appendUserMessage,
  createConversation,
  getConversationContext,
  listConversationMessages,
  type ConversationResponse,
  type MessageData,
} from '@/api/conversations';
import { clearAccessToken, getAccessToken } from '@/api/session';
import { applyPreviewFactDecision } from '@/pages/casePreview';

const { Header, Content, Footer } = Layout;

interface CaseFormValues {
  title: string;
  defaultRegionCode: string;
  legalFormCode: string;
  vatTaxpayerType: string;
  smallLowProfitStatus: 'yes' | 'no' | 'unknown';
  industryCode: string;
  businessDate: string;
  businessActionCode: string;
}

interface FactConfirmationFormValues {
  factKey: string;
  value: string;
  decision: 'confirmed' | 'rejected';
  effectiveDate?: string;
}

const previewDetail: CaseDetailResponse = {
  data: {
    case: {
      id: 'virtual-case-001',
      case_no: 'CASE-20260831-VIRTUAL',
      title: '虚构商贸企业季度开票与优惠咨询',
      status: 'draft',
      owner_user_id: 'virtual-user-001',
      default_region_code: '440300',
      current_profile_version: 1,
      version_no: 1,
    },
    profile: {
      id: 'virtual-profile-001',
      profile_version: 1,
      legal_form_code: 'LIMITED_COMPANY',
      vat_taxpayer_type: 'SMALL_SCALE',
      small_low_profit_status: 'unknown',
      industry_code: 'GENERAL_TRADE',
      region_code: '440300',
      business_date: '2026-07-15',
      business_action_codes: ['INVOICE_ISSUANCE'],
      extra_attributes: {},
      data_classification: 'synthetic',
      confirmation_status: 'confirmed',
      supersedes_profile_id: null,
    },
    facts: [
      {
        id: 'virtual-fact-001',
        profile_version: 1,
        fact_key: 'invoice_intent',
        value_type: 'text',
        value: '仅用于演示的虚构开票咨询',
        unit: null,
        source_type: 'user_input',
        effective_date: '2026-07-15',
        confirmation_status: 'confirmed',
      },
    ],
  },
  meta: { request_id: 'preview-only' },
};

const previewCases: CasesResponse = {
  data: [
    previewDetail.data.case,
    {
      id: 'virtual-case-002',
      case_no: 'CASE-20260831-VIRTUAL-2',
      title: '虚构服务企业税费适用范围咨询',
      status: 'draft',
      owner_user_id: 'virtual-user-001',
      default_region_code: '440300',
      current_profile_version: 2,
      version_no: 2,
    },
  ],
  meta: { request_id: 'preview-only' },
};

const previewConversation: ConversationResponse = {
  data: {
    id: 'virtual-conversation-001',
    case_id: previewDetail.data.case.id,
    title: '虚构事项咨询会话',
    status: 'active',
    started_by: 'virtual-user-001',
    last_message_at: null,
    summary_version: 0,
    created_at: '2026-08-31T00:00:00Z',
  },
  memory_sync_status: 'preview_only',
  meta: { request_id: 'preview-only' },
};

export function CasesWorkspacePage() {
  const navigate = useNavigate();
  const [searchParameters] = useSearchParams();
  const queryClient = useQueryClient();
  const accessToken = getAccessToken();
  const isPreview = searchParameters.get('preview') === '1';
  const [createOpen, setCreateOpen] = useState(false);
  const [factConfirmationOpen, setFactConfirmationOpen] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [previewVisibleDetail, setPreviewVisibleDetail] = useState(previewDetail);
  const [previewVisibleCases, setPreviewVisibleCases] = useState(previewCases);
  const [activeConversation, setActiveConversation] = useState<ConversationResponse | null>(null);
  const [previewMessages, setPreviewMessages] = useState<MessageData[]>([]);
  const [messageDraft, setMessageDraft] = useState('');
  const [form] = Form.useForm<CaseFormValues>();
  const [factForm] = Form.useForm<FactConfirmationFormValues>();
  const casesQuery = useQuery({
    queryKey: ['cases'],
    queryFn: () => {
      if (accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return listCases(accessToken);
    },
    enabled: accessToken !== null && !isPreview,
    retry: false,
  });
  const visibleCases = isPreview ? previewVisibleCases : casesQuery.data;
  const selectedDetail = useQuery({
    queryKey: ['cases', selectedCaseId],
    queryFn: () => {
      if (selectedCaseId === null || accessToken === null) {
        throw new Error('事项详情不可用');
      }
      return getCase(selectedCaseId, accessToken);
    },
    enabled: selectedCaseId !== null && accessToken !== null && !isPreview,
    retry: false,
  });
  const visibleDetail =
    isPreview && selectedCaseId !== null ? previewVisibleDetail : selectedDetail.data;
  const createMutation = useMutation({
    mutationFn: (payload: CreateCaseRequest) => {
      if (accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return createCase(payload, accessToken);
    },
    onSuccess: async (detail) => {
      await queryClient.invalidateQueries({ queryKey: ['cases'] });
      setSelectedCaseId(detail.data.case.id);
      setCreateOpen(false);
      form.resetFields();
    },
  });
  const confirmMutation = useMutation({
    mutationFn: (payload: ConfirmFactsRequest) => {
      if (selectedCaseId === null || accessToken === null) {
        throw new Error('事项事实确认不可用');
      }
      return confirmCaseFacts(selectedCaseId, payload, accessToken);
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(['cases', detail.data.case.id], detail);
      void queryClient.invalidateQueries({ queryKey: ['cases'] });
      setFactConfirmationOpen(false);
      factForm.resetFields();
    },
  });
  const createConversationMutation = useMutation({
    mutationFn: ({ caseId, title }: { caseId: string; title: string }) => {
      if (accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return createConversation(caseId, { title }, accessToken);
    },
    onSuccess: (conversation) => {
      setActiveConversation(conversation);
      setConversationOpen(true);
    },
  });
  const conversationId = activeConversation?.data.id ?? null;
  const messagesQuery = useQuery({
    queryKey: ['conversations', conversationId, 'messages'],
    queryFn: () => {
      if (conversationId === null || accessToken === null) {
        throw new Error('会话消息不可用');
      }
      return listConversationMessages(conversationId, accessToken);
    },
    enabled: conversationOpen && conversationId !== null && accessToken !== null && !isPreview,
    retry: false,
  });
  const contextQuery = useQuery({
    queryKey: ['conversations', conversationId, 'context'],
    queryFn: () => {
      if (conversationId === null || accessToken === null) {
        throw new Error('会话上下文不可用');
      }
      return getConversationContext(conversationId, accessToken);
    },
    enabled: conversationOpen && conversationId !== null && accessToken !== null && !isPreview,
    retry: false,
  });
  const appendMessageMutation = useMutation({
    mutationFn: ({ conversationId: id, text }: { conversationId: string; text: string }) => {
      if (accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return appendUserMessage(
        id,
        { text, idempotency_key: crypto.randomUUID() },
        accessToken,
      );
    },
    onSuccess: async (result) => {
      setMessageDraft('');
      setActiveConversation((current) =>
        current === null ? null : { ...current, memory_sync_status: result.memory_sync_status },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['conversations', conversationId, 'messages'] }),
        queryClient.invalidateQueries({ queryKey: ['conversations', conversationId, 'context'] }),
      ]);
    },
  });

  if (accessToken === null && !isPreview) {
    return <Navigate to="/" replace />;
  }

  function openDetail(caseId: string) {
    setSelectedCaseId(caseId);
    setActiveConversation(null);
    setPreviewMessages([]);
  }

  function submit(values: CaseFormValues) {
    if (isPreview) {
      setSelectedCaseId(previewDetail.data.case.id);
      setCreateOpen(false);
      return;
    }
    createMutation.mutate({
      title: values.title.trim(),
      default_region_code: values.defaultRegionCode,
      subject_profile: {
        legal_form_code: values.legalFormCode,
        vat_taxpayer_type: values.vatTaxpayerType,
        small_low_profit_status: values.smallLowProfitStatus,
        industry_code: values.industryCode,
        region_code: values.defaultRegionCode,
        business_date: values.businessDate,
        business_action_codes: [values.businessActionCode],
        extra_attributes: {},
        data_classification: 'synthetic',
        facts: [],
      },
    });
  }

  function submitFactConfirmation(values: FactConfirmationFormValues) {
    if (visibleDetail === undefined) {
      return;
    }
    const proposal = {
      fact_key: values.factKey.trim(),
      value_type: 'text',
      value: values.value.trim(),
      unit: null,
      effective_date: values.effectiveDate ?? null,
    };
    const payload: ConfirmFactsRequest = {
      profile_version: visibleDetail.data.profile.profile_version,
      fact_proposals: [proposal],
      confirmed_fact_keys: values.decision === 'confirmed' ? [proposal.fact_key] : [],
      rejected_fact_keys: values.decision === 'rejected' ? [proposal.fact_key] : [],
    };
    if (!isPreview) {
      confirmMutation.mutate(payload);
      return;
    }
    const updatedDetail = applyPreviewFactDecision(visibleDetail, proposal, values.decision);
    setPreviewVisibleDetail(updatedDetail);
    setPreviewVisibleCases((current) => ({
      ...current,
      data: current.data.map((item) =>
        item.id === updatedDetail.data.case.id ? updatedDetail.data.case : item,
      ),
    }));
    setFactConfirmationOpen(false);
    factForm.resetFields();
  }

  function startConversation() {
    if (visibleDetail === undefined) {
      return;
    }
    if (isPreview) {
      setActiveConversation({
        ...previewConversation,
        data: {
          ...previewConversation.data,
          case_id: visibleDetail.data.case.id,
          title: `${visibleDetail.data.case.title} · 咨询会话`,
        },
      });
      setConversationOpen(true);
      return;
    }
    createConversationMutation.mutate({
      caseId: visibleDetail.data.case.id,
      title: `${visibleDetail.data.case.title} · 咨询会话`,
    });
  }

  function sendMessage() {
    const text = messageDraft.trim();
    if (text.length === 0 || activeConversation === null) {
      return;
    }
    if (isPreview) {
      const nextSequence = previewMessages.length + 1;
      setPreviewMessages((current) => [
        ...current,
        {
          id: `virtual-message-${String(nextSequence).padStart(3, '0')}`,
          conversation_id: activeConversation.data.id,
          case_id: activeConversation.data.case_id,
          sequence_no: nextSequence,
          role: 'user',
          content_text: text,
          content_json: {},
          visibility: 'user_visible',
          redaction_status: 'not_needed',
          created_at: new Date().toISOString(),
        },
      ]);
      setMessageDraft('');
      return;
    }
    appendMessageMutation.mutate({ conversationId: activeConversation.data.id, text });
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
          <Typography.Text className="brand-subtitle">事项工作台</Typography.Text>
        </div>
        <Space>
          <Button
            ghost
            onClick={() => {
              void navigate(`/policies${isPreview ? '?preview=1' : ''}`);
            }}
          >
            政策检索
          </Button>
          <Button ghost onClick={logout}>
            {isPreview ? '返回登录' : '退出'}
          </Button>
        </Space>
      </Header>
      <Content className="app-content">
        <Space direction="vertical" size={24} className="full-width">
          <Alert
            type={isPreview ? 'info' : 'warning'}
            showIcon
            message={isPreview ? '预览模式：仅展示虚构事项' : '内部专业辅助：请仅录入最小必要的匿名化事实'}
            description={
              isPreview
                ? '本页面没有访问后端或真实客户资料。'
                : '事项与画像会形成可追溯版本；真实身份信息、联系方式和统一社会信用代码不应录入。'
            }
          />
          <Card
            title="我的事项"
            extra={
              <Button
                type="primary"
                onClick={() => {
                  setCreateOpen(true);
                }}
              >
                新建事项
              </Button>
            }
          >
            {casesQuery.isFetching && !isPreview ? <Spin tip="正在加载事项…" /> : null}
            {casesQuery.isError && !isPreview ? (
              <Alert
                type="error"
                showIcon
                message="事项列表未加载"
                description="请检查登录权限和后端服务后重试。"
                action={
                  <Button
                    onClick={() => {
                      void casesQuery.refetch();
                    }}
                  >
                    重试
                  </Button>
                }
              />
            ) : null}
            {visibleCases !== undefined && visibleCases.data.length === 0 ? (
              <Empty description="还没有事项，可先创建一条匿名化或虚构事项" />
            ) : null}
            {visibleCases !== undefined && visibleCases.data.length > 0 ? (
              <List
                dataSource={visibleCases.data}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="detail"
                        onClick={() => {
                          openDetail(item.id);
                        }}
                      >
                        查看画像
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={item.title}
                      description={`${item.case_no} · 地区 ${item.default_region_code}`}
                    />
                    <Space wrap>
                      <Tag color="blue">{item.status}</Tag>
                      <Tag>画像 v{item.current_profile_version}</Tag>
                    </Space>
                  </List.Item>
                )}
              />
            ) : null}
          </Card>
        </Space>
      </Content>
      <Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer>
      <Drawer
        title={isPreview ? '新建虚构事项预览' : '新建匿名化事项'}
        width={560}
        open={createOpen}
        onClose={() => {
          setCreateOpen(false);
        }}
        destroyOnHidden
      >
        <Form<CaseFormValues>
          form={form}
          layout="vertical"
          initialValues={{
            defaultRegionCode: '440300',
            legalFormCode: 'LIMITED_COMPANY',
            vatTaxpayerType: 'SMALL_SCALE',
            smallLowProfitStatus: 'unknown',
            industryCode: 'GENERAL_TRADE',
            businessDate: '2026-08-31',
            businessActionCode: 'INVOICE_ISSUANCE',
          }}
          onFinish={submit}
        >
          <Form.Item
            label="事项标题"
            name="title"
            rules={[{ required: true, min: 2, message: '请输入至少两个字的事项标题' }]}
          >
            <Input placeholder="例如：虚构商贸企业开票咨询" maxLength={200} />
          </Form.Item>
          <div className="case-form-grid">
            <Form.Item
              label="地区代码"
              name="defaultRegionCode"
              rules={[{ required: true, pattern: /^\d{6}$/, message: '请输入六位地区代码' }]}
            >
              <Input maxLength={6} inputMode="numeric" />
            </Form.Item>
            <Form.Item label="业务发生日" name="businessDate" rules={[{ required: true }]}>
              <Input type="date" />
            </Form.Item>
            <Form.Item label="主体类型" name="legalFormCode" rules={[{ required: true }]}>
              <Select options={[{ value: 'LIMITED_COMPANY', label: '有限责任公司' }]} />
            </Form.Item>
            <Form.Item label="增值税身份" name="vatTaxpayerType" rules={[{ required: true }]}>
              <Select options={[{ value: 'SMALL_SCALE', label: '小规模纳税人' }]} />
            </Form.Item>
            <Form.Item label="小型微利企业状态" name="smallLowProfitStatus" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: 'unknown', label: '待确认' },
                  { value: 'yes', label: '是' },
                  { value: 'no', label: '否' },
                ]}
              />
            </Form.Item>
            <Form.Item label="行业代码" name="industryCode" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="业务行为代码" name="businessActionCode" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {createMutation.isError ? (
            <Alert
              className="form-alert"
              type="error"
              showIcon
              message="事项未创建"
              description="请检查输入、权限和后端服务后重试。"
            />
          ) : null}
          <Button type="primary" htmlType="submit" loading={!isPreview && createMutation.isPending} block>
            {isPreview ? '查看虚构事项画像' : '创建事项'}
          </Button>
        </Form>
      </Drawer>
      <Drawer
        title="事项画像"
        width={560}
        open={selectedCaseId !== null}
        onClose={() => {
          setSelectedCaseId(null);
        }}
        destroyOnHidden
      >
        {selectedDetail.isFetching && !isPreview ? <Spin tip="正在加载画像…" /> : null}
        {selectedDetail.isError && !isPreview ? (
          <Alert type="error" showIcon message="事项详情未加载" description="请关闭后重试。" />
        ) : null}
        {visibleDetail !== undefined ? (
          <Space direction="vertical" size={16} className="full-width">
            <Descriptions title={visibleDetail.data.case.title} size="small" column={1}>
              <Descriptions.Item label="事项编号">{visibleDetail.data.case.case_no}</Descriptions.Item>
              <Descriptions.Item label="事项状态">{visibleDetail.data.case.status}</Descriptions.Item>
              <Descriptions.Item label="当前画像版本">
                v{visibleDetail.data.profile.profile_version}
              </Descriptions.Item>
              <Descriptions.Item label="数据分类">
                {visibleDetail.data.profile.data_classification}
              </Descriptions.Item>
            </Descriptions>
            <Descriptions title="画像范围" size="small" column={1}>
              <Descriptions.Item label="地区">{visibleDetail.data.profile.region_code}</Descriptions.Item>
              <Descriptions.Item label="业务发生日">
                {visibleDetail.data.profile.business_date}
              </Descriptions.Item>
              <Descriptions.Item label="业务行为">
                {visibleDetail.data.profile.business_action_codes.join('、')}
              </Descriptions.Item>
            </Descriptions>
            <Button
              type="primary"
              onClick={() => {
                setFactConfirmationOpen(true);
              }}
            >
              确认事实候选并生成新版本
            </Button>
            <Button
              onClick={startConversation}
              loading={!isPreview && createConversationMutation.isPending}
            >
              开始咨询会话
            </Button>
            {createConversationMutation.isError ? (
              <Alert type="error" showIcon message="会话未创建，请检查权限和后端服务。" />
            ) : null}
            <Card size="small" title="已确认事实">
              {visibleDetail.data.facts.filter((fact) => fact.confirmation_status === 'confirmed')
                .length === 0 ? (
                <Typography.Text type="secondary">当前画像尚无补充事实。</Typography.Text>
              ) : (
                <List
                  size="small"
                  dataSource={visibleDetail.data.facts.filter(
                    (fact) => fact.confirmation_status === 'confirmed',
                  )}
                  renderItem={(fact) => (
                    <List.Item>
                      <Typography.Text>{fact.fact_key}</Typography.Text>
                      <Typography.Text type="secondary">{String(fact.value)}</Typography.Text>
                    </List.Item>
                  )}
                />
              )}
            </Card>
            {visibleDetail.data.facts.some((fact) => fact.confirmation_status === 'rejected') ? (
              <Card size="small" title="本版本已拒绝候选">
                <List
                  size="small"
                  dataSource={visibleDetail.data.facts.filter(
                    (fact) => fact.confirmation_status === 'rejected',
                  )}
                  renderItem={(fact) => (
                    <List.Item>
                      <Typography.Text>{fact.fact_key}</Typography.Text>
                      <Tag color="red">已拒绝</Tag>
                    </List.Item>
                  )}
                />
              </Card>
            ) : null}
          </Space>
        ) : null}
      </Drawer>
      <Drawer
        title="确认事实候选"
        width={480}
        open={factConfirmationOpen}
        onClose={() => {
          setFactConfirmationOpen(false);
        }}
        destroyOnHidden
      >
        <Alert
          className="form-alert"
          type="warning"
          showIcon
          message="确认会生成新的不可变画像版本"
          description="只录入虚构或匿名化事实；拒绝的候选也会保留决定状态，供后续审计。"
        />
        <Form<FactConfirmationFormValues>
          form={factForm}
          layout="vertical"
          initialValues={{ decision: 'confirmed', effectiveDate: '2026-08-31' }}
          onFinish={submitFactConfirmation}
        >
          <Form.Item
            label="事实键"
            name="factKey"
            rules={[{ required: true, message: '请输入事实键' }]}
          >
            <Input placeholder="例如：invoice_intent" maxLength={100} />
          </Form.Item>
          <Form.Item
            label="候选内容"
            name="value"
            rules={[{ required: true, message: '请输入虚构或匿名化候选内容' }]}
          >
            <Input.TextArea rows={4} maxLength={500} />
          </Form.Item>
          <Form.Item label="生效日期" name="effectiveDate">
            <Input type="date" />
          </Form.Item>
          <Form.Item label="人工决定" name="decision" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'confirmed', label: '确认并纳入当前事实' },
                { value: 'rejected', label: '拒绝候选' },
              ]}
            />
          </Form.Item>
          {confirmMutation.isError ? (
            <Alert
              className="form-alert"
              type="error"
              showIcon
              message="事实确认未完成"
              description="画像可能已被更新，请刷新事项后重试。"
            />
          ) : null}
          <Button
            type="primary"
            htmlType="submit"
            loading={!isPreview && confirmMutation.isPending}
            block
          >
            提交决定并生成新版本
          </Button>
        </Form>
      </Drawer>
      <Drawer
        title={activeConversation?.data.title ?? '事项咨询会话'}
        width={640}
        open={conversationOpen}
        onClose={() => {
          setConversationOpen(false);
        }}
        destroyOnHidden
      >
        <Space direction="vertical" size={16} className="full-width">
          <Alert
            type="info"
            showIcon
            message="当前阶段仅保存会话消息与可恢复短期上下文"
            description="尚未接入模型回答；消息先写入 MySQL，再同步 Redis。Redis 不可用时会从 MySQL 恢复。"
          />
          <Space wrap>
            <Tag color="blue">画像 v{visibleDetail?.data.profile.profile_version ?? '-'}</Tag>
            <Tag
              color={
                isPreview || activeConversation?.memory_sync_status === 'synced' ? 'green' : 'orange'
              }
            >
              {isPreview
                ? '虚构短期记忆'
                : `记忆同步：${activeConversation?.memory_sync_status ?? '待确认'}`}
            </Tag>
            {contextQuery.data !== undefined ? (
              <Tag>上下文来源：{contextQuery.data.data.memory_source}</Tag>
            ) : null}
          </Space>
          {messagesQuery.isError && !isPreview ? (
            <Alert
              type="error"
              showIcon
              message="消息未加载"
              action={
                <Button
                  onClick={() => {
                    void messagesQuery.refetch();
                  }}
                >
                  重试
                </Button>
              }
            />
          ) : null}
          {messagesQuery.isFetching && !isPreview ? <Spin tip="正在加载会话…" /> : null}
          {(isPreview ? previewMessages : (messagesQuery.data?.data ?? [])).length === 0 ? (
            <Empty description="还没有消息，可录入一条虚构或匿名化咨询" />
          ) : (
            <List
              className="conversation-messages"
              dataSource={isPreview ? previewMessages : (messagesQuery.data?.data ?? [])}
              renderItem={(message) => (
                <List.Item>
                  <Card size="small" className="full-width">
                    <Space direction="vertical" size={4}>
                      <Tag color="blue">用户消息 #{message.sequence_no}</Tag>
                      <Typography.Text>{message.content_text}</Typography.Text>
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          )}
          <Input.TextArea
            value={messageDraft}
            onChange={(event) => {
              setMessageDraft(event.target.value);
            }}
            placeholder="仅输入虚构或匿名化咨询内容"
            rows={4}
            maxLength={4000}
          />
          {appendMessageMutation.isError ? (
            <Alert
              type="error"
              showIcon
              message="消息未保存"
              description="请检查输入、权限和后端服务后重试。"
            />
          ) : null}
          <Button
            type="primary"
            onClick={sendMessage}
            disabled={messageDraft.trim().length === 0}
            loading={!isPreview && appendMessageMutation.isPending}
            block
          >
            保存用户消息
          </Button>
        </Space>
      </Drawer>
    </Layout>
  );
}
