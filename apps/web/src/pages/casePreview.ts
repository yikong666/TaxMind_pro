import type { CaseDetailResponse, ConfirmFactsRequest } from '@/api/cases';

type FactDecision = 'confirmed' | 'rejected';

export function applyPreviewFactDecision(
  detail: CaseDetailResponse,
  proposal: ConfirmFactsRequest['fact_proposals'][number],
  decision: FactDecision,
): CaseDetailResponse {
  const nextVersion = detail.data.profile.profile_version + 1;
  const retainedFacts = detail.data.facts
    .filter(
      (fact) =>
        fact.confirmation_status === 'confirmed' &&
        (decision === 'rejected' || fact.fact_key !== proposal.fact_key),
    )
    .map((fact) => ({ ...fact, profile_version: nextVersion }));
  return {
    ...detail,
    data: {
      case: {
        ...detail.data.case,
        current_profile_version: nextVersion,
        version_no: detail.data.case.version_no + 1,
      },
      profile: {
        ...detail.data.profile,
        id: `virtual-profile-${String(nextVersion).padStart(3, '0')}`,
        profile_version: nextVersion,
        supersedes_profile_id: detail.data.profile.id,
      },
      facts: [
        ...retainedFacts,
        {
          id: `virtual-fact-${String(nextVersion).padStart(3, '0')}`,
          profile_version: nextVersion,
          fact_key: proposal.fact_key,
          value_type: proposal.value_type,
          value: proposal.value,
          unit: proposal.unit ?? null,
          source_type: 'reviewer',
          effective_date: proposal.effective_date ?? null,
          confirmation_status: decision,
        },
      ],
    },
  };
}
