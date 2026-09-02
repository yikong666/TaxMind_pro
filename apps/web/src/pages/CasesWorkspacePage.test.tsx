import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { CasesWorkspacePage } from '@/pages/CasesWorkspacePage';
import { applyPreviewFactDecision } from '@/pages/casePreview';

describe('CasesWorkspacePage', () => {
  it('renders the fixed-width conversation history and can collapse it from the project header', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases?preview=1']}>
          <CasesWorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('complementary', { name: '项目对话' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '收起项目对话' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建会话' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建事项' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '收起项目对话' }));

    expect(screen.queryByRole('complementary', { name: '项目对话' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '展开项目对话' })).toBeInTheDocument();
  });

  it('renders only virtual records in preview mode', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases?preview=1']}>
          <CasesWorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('预览模式：仅展示虚构事项')).toBeInTheDocument();
    expect(screen.getAllByText('虚构商贸企业季度开票与优惠咨询').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '新建会话' })).toBeInTheDocument();
  });

  it('creates a new immutable preview profile after confirming a fact candidate', () => {
    const detail = applyPreviewFactDecision(
      {
        data: {
          case: {
            id: 'case-001',
            case_no: 'CASE-001',
            title: '虚构事项',
            status: 'draft',
            owner_user_id: 'user-001',
            default_region_code: '440300',
            current_profile_version: 1,
            version_no: 1,
          },
          profile: {
            id: 'profile-001',
            profile_version: 1,
            legal_form_code: 'LIMITED_COMPANY',
            vat_taxpayer_type: 'SMALL_SCALE',
            small_low_profit_status: 'unknown',
            industry_code: 'GENERAL_TRADE',
            region_code: '440300',
            business_date: '2026-08-31',
            business_action_codes: ['INVOICE_ISSUANCE'],
            extra_attributes: {},
            data_classification: 'synthetic',
            confirmation_status: 'confirmed',
            supersedes_profile_id: null,
          },
          facts: [],
        },
        meta: { request_id: 'preview-test' },
      },
      { fact_key: 'service_scope', value_type: 'text', value: '虚构服务范围' },
      'confirmed',
    );

    expect(detail.data.profile.profile_version).toBe(2);
    expect(detail.data.profile.supersedes_profile_id).toBe('profile-001');
    expect(detail.data.facts[0]?.confirmation_status).toBe('confirmed');
  });

  it('renders a virtual deterministic risk finding after preview analysis runs', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases?preview=1']}>
          <CasesWorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: '风险审查' }));

    expect(screen.getByText('规则版本：RISK-INVOICE-001-v1')).toBeInTheDocument();
    expect(screen.getByText('风险结论由确定性规则生成，模型不能修改。')).toBeInTheDocument();
  });

  it('requires confirmation before deleting and restoring the active preview conversation', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases?preview=1']}>
          <CasesWorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: '新建会话' }));
    fireEvent.click(screen.getByRole('button', { name: '删除当前会话' }));

    expect(screen.getByText('确认删除会话？')).toBeInTheDocument();
    const deleteConfirmation = screen
      .getAllByRole('button', { name: '删除会话' })
      .find((button) => !button.hasAttribute('disabled'));
    if (!deleteConfirmation) {
      throw new Error('未找到可用的删除会话确认按钮');
    }
    fireEvent.click(deleteConfirmation);
    expect(screen.getByText('已删除')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '恢复当前会话' }));
    expect(screen.getByText('确认恢复会话？')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '恢复会话' }));
    expect(screen.getByText('可继续')).toBeInTheDocument();
  }, 10_000);
});
