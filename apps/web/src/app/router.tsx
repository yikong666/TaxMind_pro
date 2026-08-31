import { createBrowserRouter } from 'react-router-dom';

import { CasesWorkspacePage } from '@/pages/CasesWorkspacePage';
import { LoginPage } from '@/pages/LoginPage';
import { PolicySearchPage } from '@/pages/PolicySearchPage';

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
]);
