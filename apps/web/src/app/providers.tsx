import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import type { ReactNode } from 'react';

import { ErrorBoundary } from '@/app/error-boundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: '#1f5b4f',
              borderRadius: 8,
              colorBgLayout: '#f4f6f5',
            },
          }}
        >
          {children}
        </ConfigProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}