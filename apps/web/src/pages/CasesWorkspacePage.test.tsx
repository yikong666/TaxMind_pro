import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { CasesWorkspacePage } from '@/pages/CasesWorkspacePage';
import { applyPreviewFactDecision } from '@/pages/casePreview';

describe('CasesWorkspacePage', () => {
  it('renders only virtual records in preview mode', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases?preview=1']}>
          <CasesWorkspacePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('预览模式：仅展示虚构事项')).toBeInTheDocument();
    expect(screen.getByText('虚构商贸企业季度开票与优惠咨询')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建事项' })).toBeInTheDocument();
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
});
