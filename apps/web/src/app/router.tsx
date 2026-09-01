import { createBrowserRouter } from 'react-router-dom';

import { CasesWorkspacePage } from '@/pages/CasesWorkspacePage';
import { AuditPage } from '@/pages/AuditPage';
import { FeedbackPage } from '@/pages/FeedbackPage';
import { LoginPage } from '@/pages/LoginPage';
import { PolicySearchPage } from '@/pages/PolicySearchPage';
import { ProceduresPage } from '@/pages/ProceduresPage';
import { ReviewQueuePage } from '@/pages/ReviewQueuePage';
import { ReviewDetailPage } from '@/pages/ReviewDetailPage';

export const appRouter = createBrowserRouter([
  {
    path: '/',
    element: <LoginPage />,
  },
  {
    path: '/policies',
    element: <PolicySearchPage />,
  },
  {
    path: '/cases',
    element: <CasesWorkspacePage />,
  },
  {
    path: '/procedures',
    element: <ProceduresPage />,
  },
  { path: '/reviews', element: <ReviewQueuePage /> },
  { path: '/reviews/:taskId', element: <ReviewDetailPage /> },
  { path: '/audit', element: <AuditPage /> },
  { path: '/feedback', element: <FeedbackPage /> },
]);
