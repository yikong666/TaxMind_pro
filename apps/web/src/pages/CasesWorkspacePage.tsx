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
  List,
  Popconfirm,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowUp,
  ChevronDown,
  FileSearch,
  LayoutList,
  Paperclip,
  Plus,
  Search,
  ShieldAlert,
  UserRound,
} from 'lucide-react';

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
  deleteConversation,
  getConversationContext,
  listConversationMessages,
  restoreConversation,
  type ConversationResponse,
  type MessageData,
} from '@/api/conversations';
import { getAccessToken } from '@/api/session';
import { getQueryRun, submitQueryRun, type QueryRunResponse } from '@/api/queryRuns';
import { replayQueryRunEvents } from '@/api/runStream';
import { RiskFindingCard } from '@/components/risk/RiskFindingCard';
import { applyPreviewFactDecision } from '@/pages/casePreview';

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
    updated_at: '2026-08-31T00:00:00Z',
    deleted_at: null,
  },
  memory_sync_status: 'preview_only',
  meta: { request_id: 'preview-only' },
};

const previewQueryRun: QueryRunResponse = {
  data: {
    id: 'virtual-run-001',
    status: 'needs_input',
    case_id: previewDetail.data.case.id,
    conversation_id: previewConversation.data.id,
    profile_version: 1,
    facts_snapshot: {
      business_date: '2026-07-15',
      region_code: '440300',
    },
    public_knowledge_snapshot_id: 'virtual-public-snapshot-001',
    org_knowledge_snapshot_id: null,
    retrieval_plan: {
      route_code: 'policy_applicability',
      use_mysql_exact: false,
      use_milvus_semantic: true,
      graph_expansion_type: 'policy_conditions',
    },
    rule_results: [
      {
        rule_version_id: 'RISK-INVOICE-001-v1',
        status: 'manual_review',
        severity: null,
        missing_fact_keys: ['invoice_amount'],
        basis_chunk_ids: ['virtual:invoice:article_12'],
      },
    ],
    follow_up_fact_keys: ['small_low_profit_status'],
    degradation_events: [],
    rule_version_ids: ['RISK-INVOICE-001-v1'],
    evidence_ids: ['virtual:invoice:article_12'],
    model_profile_id: null,
    prompt_bundle_version: null,
    started_at: null,
    completed_at: null,
    error_code: null,
    error_detail_safe: null,
    final_answer: null,
    audit_resource_id: 'virtual-run-001',
  },
  meta: { request_id: 'preview-only' },
};

export function CasesWorkspacePage() {
  const navigate = useNavigate();
  const [searchParameters] = useSearchParams();
  const queryClient = useQueryClient();
  const accessToken = getAccessToken();
  const isPreview = searchParameters.get('preview') === '1';
  const [createOpen, setCreateOpen] = useState(searchParameters.get('create') === '1');
  const [factConfirmationOpen, setFactConfirmationOpen] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [profileDrawerOpen, setProfileDrawerOpen] = useState(false);
  const [activeTool, setActiveTool] = useState('项目上下文');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(
    isPreview ? previewDetail.data.case.id : null,
  );
  const [previewVisibleDetail, setPreviewVisibleDetail] = useState(previewDetail);
  const [previewVisibleCases, setPreviewVisibleCases] = useState(previewCases);
  const [activeConversation, setActiveConversation] = useState<ConversationResponse | null>(null);
  const [previewMessages, setPreviewMessages] = useState<MessageData[]>([]);
  const [visibleQueryRun, setVisibleQueryRun] = useState<QueryRunResponse | null>(null);
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
  const conversationWritable = activeConversation?.data.status === 'active';
  const canSubmitQueryRun =
    activeConversation !== null && conversationWritable && messageDraft.trim().length > 0;
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
  const deleteConversationMutation = useMutation({
    mutationFn: (id: string) => {
      if (accessToken === null) {
        throw new Error('会话管理不可用');
      }
      return deleteConversation(id, accessToken);
    },
    onSuccess: (result) => {
      setActiveConversation((current) =>
        current === null ? null : { ...current, data: result.data },
      );
      setConversationOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['conversations', result.data.id] });
    },
  });
  const restoreConversationMutation = useMutation({
    mutationFn: (id: string) => {
      if (accessToken === null) {
        throw new Error('会话管理不可用');
      }
      return restoreConversation(id, accessToken);
    },
    onSuccess: (result) => {
      setActiveConversation((current) =>
        current === null ? null : { ...current, data: result.data },
      );
      setConversationOpen(true);
      void queryClient.invalidateQueries({ queryKey: ['conversations', result.data.id] });
    },
  });
  const queryRunMutation = useMutation({
    mutationFn: ({ caseId, conversationId: id, query }: { caseId: string; conversationId: string; query: string }) => {
      if (accessToken === null) {
        throw new Error('专业会话不可用');
      }
      return submitQueryRun(
        caseId,
        { query, conversation_id: id, idempotency_key: crypto.randomUUID() },
        accessToken,
      );
    },
    onSuccess: async (run) => {
      setVisibleQueryRun(run);
      setMessageDraft('');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['conversations', conversationId, 'messages'] }),
        queryClient.invalidateQueries({ queryKey: ['conversations', conversationId, 'context'] }),
      ]);
    },
  });
  const activeRunId = visibleQueryRun?.data.id;

  useEffect(() => {
    if (isPreview || accessToken === null || activeRunId === undefined) {
      return undefined;
    }
    const runId = activeRunId;
    const controller = new AbortController();
    let cancelled = false;
    let lastEventId: string | null = null;
    const replay = async () => {
      while (!cancelled) {
        try {
          await replayQueryRunEvents(
            runId,
            accessToken,
            lastEventId,
            (event) => {
              lastEventId = event.id;
              setVisibleQueryRun((current) => {
                if (current === null || current.data.id !== runId) {
                  return current;
                }
                return {
                  ...current,
                  data: {
                    ...current.data,
                    status: event.data.status ?? current.data.status,
                    follow_up_fact_keys:
                      event.data.follow_up_fact_keys ?? current.data.follow_up_fact_keys,
                    error_code: event.data.error_code ?? current.data.error_code,
                    error_detail_safe:
                      event.data.error_detail_safe ?? current.data.error_detail_safe,
                  },
                };
              });
            },
            controller.signal,
          );
          const refreshed = await getQueryRun(runId, accessToken);
          if (controller.signal.aborted) {
            return;
          }
          setVisibleQueryRun(refreshed);
          if (isTerminalRunStatus(refreshed.data.status)) {
            return;
          }
          await new Promise<void>((resolve) => window.setTimeout(resolve, 1200));
        } catch {
          if (!controller.signal.aborted) {
            await new Promise<void>((resolve) => window.setTimeout(resolve, 2000));
          }
        }
      }
    };
    void replay();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [accessToken, activeRunId, isPreview]);

  if (accessToken === null && !isPreview) {
    return <Navigate to="/" replace />;
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

  function runControlledAnalysis() {
    if (visibleDetail === undefined) {
      return;
    }
    if (isPreview) {
      setVisibleQueryRun({
        ...previewQueryRun,
        data: {
          ...previewQueryRun.data,
          case_id: visibleDetail.data.case.id,
          profile_version: visibleDetail.data.profile.profile_version,
        },
      });
      return;
    }
    if (
      activeConversation === null ||
      !conversationWritable ||
      messageDraft.trim().length === 0
    ) {
      return;
    }
    queryRunMutation.mutate({
      caseId: visibleDetail.data.case.id,
      conversationId: activeConversation.data.id,
      query: messageDraft.trim(),
    });
  }

  function sendMessage() {
    const text = messageDraft.trim();
    if (text.length === 0 || activeConversation === null || !conversationWritable) {
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

  function deleteActiveConversation() {
    if (activeConversation === null) {
      return;
    }
    if (isPreview) {
      const now = new Date().toISOString();
      setActiveConversation({
        ...activeConversation,
        data: {
          ...activeConversation.data,
          status: 'deleted',
          deleted_at: now,
          updated_at: now,
        },
      });
      setConversationOpen(false);
      return;
    }
    deleteConversationMutation.mutate(activeConversation.data.id);
  }

  function restoreActiveConversation() {
    if (activeConversation === null) {
      return;
    }
    if (isPreview) {
      setActiveConversation({
        ...activeConversation,
        data: {
          ...activeConversation.data,
          status: 'active',
          deleted_at: null,
          updated_at: new Date().toISOString(),
        },
      });
      setConversationOpen(true);
      return;
    }
    restoreConversationMutation.mutate(activeConversation.data.id);
  }

  return (
    <div className={`workspace-layout ${historyCollapsed ? 'is-history-collapsed' : ''}`}>
      {!historyCollapsed ? (
        <aside aria-label="项目对话" className="workspace-history">
          <div className="workspace-history-heading">
            <div className="workspace-history-title">项目对话</div>
            <button aria-label="新建事项" className="workspace-new-case" onClick={() => {
              setCreateOpen(true);
            }}><Plus size={14} /></button>
          </div>
          <select aria-label="当前项目" className="workspace-project-picker" value={selectedCaseId ?? ''} onChange={(event) => {
            setSelectedCaseId(event.target.value);
            setActiveConversation(null);
            setPreviewMessages([]);
            setVisibleQueryRun(null);
          }}>
            <option value="" disabled>选择当前项目</option>
            {visibleCases?.data.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select>
          <Button className="workspace-new-conversation" block icon={<Plus size={15} />} onClick={startConversation} disabled={visibleDetail === undefined} loading={!isPreview && createConversationMutation.isPending}>
            新建会话
          </Button>
          {activeConversation !== null ? (
            <>
              <div className="workspace-history-group">当前会话</div>
              <div className="workspace-history-item is-current">
                <span>{activeConversation.data.title}</span>
                <span className="workspace-history-status">
                  {conversationWritable ? '可继续' : '已删除'}
                </span>
                {conversationWritable ? (
                  <Popconfirm
                    cancelText="取消"
                    description="消息和审计历史会保留，恢复后可继续使用。"
                    okText="删除会话"
                    onConfirm={deleteActiveConversation}
                    title="确认删除会话？"
                  >
                    <button aria-label="删除当前会话" type="button">×</button>
                  </Popconfirm>
                ) : (
                  <Popconfirm
                    cancelText="取消"
                    description="恢复后会话将重新允许读取消息和继续录入。"
                    okText="恢复会话"
                    onConfirm={restoreActiveConversation}
                    title="确认恢复会话？"
                  >
                    <button aria-label="恢复当前会话" type="button">↻</button>
                  </Popconfirm>
                )}
              </div>
            </>
          ) : null}
          {isPreview ? (
            <>
              <div className="workspace-history-group">今天</div>
              <div className="workspace-history-item is-current">优惠资格与开票风险<button aria-label="删除会话" disabled>×</button></div>
              <div className="workspace-history-item">补充纳税人身份<button aria-label="删除会话" disabled>×</button></div>
              <div className="workspace-history-group">昨天</div>
              <div className="workspace-history-item">办理材料核验<button aria-label="删除会话" disabled>×</button></div>
            </>
          ) : (
            <div className="workspace-history-notice">后端暂未提供会话列表。新建会话后可管理当前会话并继续录入消息。</div>
          )}
        </aside>
      ) : null}
      <main className="workspace-chat">
        <header className="workspace-projectbar">
          <div className="workspace-project-name">
            <button aria-label={historyCollapsed ? '展开项目对话' : '收起项目对话'} className="workspace-history-toggle" onClick={() => {
              setHistoryCollapsed((current) => !current);
            }}>
              {historyCollapsed ? '›' : '‹'}
            </button>
            <span>{visibleDetail?.data.case.title ?? '请选择一个事项'}</span>
            <ChevronDown aria-hidden="true" size={15} />
          </div>
          <div className="workspace-tools">
            <button className={activeTool === '结构化分析' ? 'is-active' : ''} onClick={() => { setActiveTool('结构化分析'); setProfileDrawerOpen(true); }}><LayoutList size={14} />结构化分析</button>
            <button className={activeTool === '风险审查' ? 'is-active' : ''} onClick={() => {
              setActiveTool('风险审查');
              if (!isPreview && !canSubmitQueryRun) {
                setProfileDrawerOpen(true);
                return;
              }
              runControlledAnalysis();
            }}><ShieldAlert size={14} />风险审查</button>
            <button className={activeTool === '政策证据' ? 'is-active' : ''} onClick={() => { setActiveTool('政策证据'); void navigate(`/policies${isPreview ? '?preview=1' : ''}`); }}><FileSearch size={14} />政策证据</button>
            <button className={activeTool === '项目上下文' ? 'is-active' : ''} onClick={() => {
              setActiveTool('项目上下文');
            }}><UserRound size={14} />项目上下文</button>
          </div>
        </header>
        <div className="workspace-chat-body">
          <div className="workspace-chat-stream">
            <div className="workspace-welcome">
              <h1>今天想先核验什么？</h1>
              <p>围绕当前项目补充事实、查询政策或执行受控风险审查。</p>
            </div>
            {visibleDetail === undefined ? <Empty description="请选择一个事项后继续" /> : null}
            {visibleDetail !== undefined ? (
              <div className="workspace-message workspace-message-assistant">
                <strong>项目上下文已加载</strong><br />
                当前画像 v{visibleDetail.data.profile.profile_version} · 地区 {visibleDetail.data.profile.region_code} · 业务日期 {visibleDetail.data.profile.business_date}
              <div className="workspace-system-card">事实与风险结论只来自已保存的画像、确定性规则与已发布证据；最终回答仅在受信任执行器完成并通过引用校验后展示。</div>
              {isPreview ? <div className="workspace-preview-note">预览模式：仅展示虚构事项</div> : null}
              </div>
            ) : null}
            {(isPreview ? previewMessages : (messagesQuery.data?.data ?? [])).map((message) => (
              <div className={`workspace-message ${message.role === 'assistant' ? 'workspace-message-assistant' : 'workspace-message-user'}`} key={message.id}>{message.content_text}</div>
            ))}
            {visibleQueryRun !== null ? (
              <div className="workspace-analysis-result">
                <div className="workspace-analysis-heading">受控分析运行 <span>{queryRunStatusLabel(visibleQueryRun.data.status)}</span></div>
                {visibleQueryRun.data.follow_up_fact_keys.length > 0 ? <div className="workspace-system-card">请补充：{visibleQueryRun.data.follow_up_fact_keys.join('、')}</div> : null}
                {visibleQueryRun.data.error_detail_safe !== null ? <Alert type="error" showIcon message={visibleQueryRun.data.error_detail_safe} /> : null}
                {visibleQueryRun.data.final_answer !== null ? <div className="workspace-message workspace-message-assistant">{visibleQueryRun.data.final_answer.text}<div className="workspace-system-card">引用：{visibleQueryRun.data.final_answer.citation_ids.join('、') || '无'}</div></div> : null}
                {visibleQueryRun.data.rule_results.map((rule) => <RiskFindingCard key={rule.rule_version_id} finding={rule} />)}
              </div>
            ) : null}
          </div>
          <div className="workspace-composer">
            <Input.TextArea disabled={activeConversation !== null && !conversationWritable} value={messageDraft} onChange={(event) => {
              setMessageDraft(event.target.value);
            }} placeholder={activeConversation === null ? '请先新建会话后再录入匿名化咨询内容…' : conversationWritable ? '在当前项目中补充事实或提出问题…' : '当前会话已删除，请先恢复后继续…'} autoSize={{ minRows: 3, maxRows: 5 }} maxLength={4000} />
            <div className="workspace-composer-footer">
              <div>
                <span className="workspace-chip" aria-disabled="true"><Paperclip size={13} />添加附件说明</span>
                <button className="workspace-chip" onClick={() => void navigate(`/policies${isPreview ? '?preview=1' : ''}`)}><Search size={13} />查政策</button>
              </div>
              <button aria-label="保存用户消息" className="workspace-send" onClick={sendMessage} disabled={messageDraft.trim().length === 0 || activeConversation === null || !conversationWritable} aria-describedby={activeConversation === null ? 'workspace-send-help' : undefined}><ArrowUp size={16} /></button>
            </div>
            {activeConversation === null ? <span className="workspace-send-help" id="workspace-send-help">当前未创建会话，不能保存消息。</span> : null}
            {activeConversation !== null && !conversationWritable ? <span className="workspace-send-help">当前会话已删除，恢复后才能继续。</span> : null}
            {deleteConversationMutation.isError || restoreConversationMutation.isError ? <Alert type="error" showIcon message="会话状态更新失败，请检查权限和后端服务后重试。" /> : null}
            {appendMessageMutation.isError ? <Alert type="error" showIcon message="消息未保存，请检查输入、权限和后端服务后重试。" /> : null}
            {queryRunMutation.isError ? <Alert type="error" showIcon message="运行未创建，请检查会话、事项权限和后端服务后重试。" /> : null}
          </div>
        </div>
      </main>
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
        open={profileDrawerOpen}
        onClose={() => {
          setProfileDrawerOpen(false);
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
            <Button
              onClick={runControlledAnalysis}
              loading={!isPreview && queryRunMutation.isPending}
              disabled={!isPreview && !canSubmitQueryRun}
            >
              运行受控分析
            </Button>
            {!isPreview && !canSubmitQueryRun ? (
              <Typography.Text type="secondary">
                请先创建可用会话，并在输入框填写匿名化问题后再运行分析。
              </Typography.Text>
            ) : null}
            {queryRunMutation.isError ? (
              <Alert type="error" showIcon message="分析未完成，请检查事项权限和后端服务。" />
            ) : null}
            {visibleQueryRun !== null ? (
              <Card size="small" title="受控分析运行">
                <Space direction="vertical" size={8} className="full-width">
                  <Space wrap>
                    <Tag color={queryRunStatusColor(visibleQueryRun.data.status)}>
                      {queryRunStatusLabel(visibleQueryRun.data.status)}
                    </Tag>
                    {visibleQueryRun.data.retrieval_plan !== null ? (
                      <Tag>{visibleQueryRun.data.retrieval_plan.route_code}</Tag>
                    ) : null}
                    <Tag>审计关联：{visibleQueryRun.data.audit_resource_id}</Tag>
                  </Space>
                  {visibleQueryRun.data.follow_up_fact_keys.length > 0 ? (
                    <Alert
                      type="warning"
                      showIcon
                      message={`请补充：${visibleQueryRun.data.follow_up_fact_keys.join('、')}`}
                    />
                  ) : null}
                  {visibleQueryRun.data.error_detail_safe !== null ? (
                    <Alert type="error" showIcon message={visibleQueryRun.data.error_detail_safe} />
                  ) : null}
                  {visibleQueryRun.data.final_answer !== null ? (
                    <Card size="small" title="已持久化最终回答">
                      <Typography.Paragraph>{visibleQueryRun.data.final_answer.text}</Typography.Paragraph>
                      <Typography.Text type="secondary">
                        引用：{visibleQueryRun.data.final_answer.citation_ids.join('、') || '无'}
                      </Typography.Text>
                    </Card>
                  ) : null}
                  {visibleQueryRun.data.rule_results.length === 0 ? (
                    <Typography.Text type="secondary">
                      当前知识快照没有已发布的适用风险规则；系统不会由模型补造规则结论。
                    </Typography.Text>
                  ) : (
                    <Space direction="vertical" size={12} className="full-width">
                      {visibleQueryRun.data.rule_results.map((rule) => (
                        <RiskFindingCard key={rule.rule_version_id} finding={rule} />
                      ))}
                    </Space>
                  )}
                </Space>
              </Card>
            ) : null}
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
        open={false}
        onClose={() => {
          setConversationOpen(false);
        }}
        destroyOnHidden
      >
        <Space direction="vertical" size={16} className="full-width">
          <Alert
            type="info"
            showIcon
            message="会话消息与运行结果均可回放"
            description="用户问题先写入 MySQL；最终回答仅由受信任执行器在引用校验后写入。Redis 不可用时会从 MySQL 恢复上下文。"
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
                      <Tag color={message.role === 'assistant' ? 'green' : 'blue'}>
                        {message.role === 'assistant' ? '最终回答' : '用户消息'} #{message.sequence_no}
                      </Tag>
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
    </div>
  );
}

function isTerminalRunStatus(status: string): boolean {
  return status === 'needs_input' || status === 'completed' || status === 'failed';
}

function queryRunStatusLabel(status: string): string {
  return {
    queued: '排队中',
    running: '执行中',
    completed: '已完成',
    failed: '未执行',
    needs_input: '需要补充事实',
  }[status] ?? status;
}

function queryRunStatusColor(status: string): 'blue' | 'gold' | 'green' | 'red' {
  switch (status) {
    case 'queued':
    case 'running':
      return 'blue';
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    default:
      return 'gold';
  }
}
