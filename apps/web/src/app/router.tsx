import { createBrowserRouter } from 'react-router-dom';

import { AppFrame } from '@/components/layout/AppFrame';
import { CasesWorkspacePage } from '@/pages/CasesWorkspacePage';
import { CasesManagementPage } from '@/pages/CasesManagementPage';
import { AuditPage } from '@/pages/AuditPage';
import { FeedbackPage } from '@/pages/FeedbackPage';
import { LoginPage } from '@/pages/LoginPage';
import { KnowledgeOperationsPage } from '@/pages/KnowledgeOperationsPage';
import { PolicySearchPage } from '@/pages/PolicySearchPage';
import { ProceduresPage } from '@/pages/ProceduresPage';
import { ReviewQueuePage } from '@/pages/ReviewQueuePage';
import { ReviewDetailPage } from '@/pages/ReviewDetailPage';
import { SettingsPage } from '@/pages/SettingsPage';

export const appRouter = createBrowserRouter([
  {
    path: '/',
    element: <LoginPage />,
  },
  {
    element: <AppFrame />,
    children: [
      {
        path: '/policies',
        element: <PolicySearchPage />,
      },
      {
        path: '/cases',
        element: <CasesWorkspacePage />,
      },
      {
        path: '/cases/manage',
        element: <CasesManagementPage />,
      },
      {
        path: '/procedures',
        element: <ProceduresPage />,
      },
      { path: '/reviews', element: <ReviewQueuePage /> },
      { path: '/reviews/:taskId', element: <ReviewDetailPage /> },
      { path: '/knowledge', element: <KnowledgeOperationsPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/audit', element: <AuditPage /> },
      { path: '/feedback', element: <FeedbackPage /> },
    ],
  },
]);
