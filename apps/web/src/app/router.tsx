import { createBrowserRouter } from 'react-router-dom';

import { BootstrapPage } from '@/pages/BootstrapPage';

export const appRouter = createBrowserRouter([
  {
    path: '/',
    element: <BootstrapPage />,
  },
]);