import { Alert, Button, Flex } from 'antd';
import { Component, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { hasError: false };

  public static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Flex className="fatal-error" vertical gap={16}>
          <Alert
            type="error"
            showIcon
            message="页面暂时无法显示"
            description="未保存的专业结论不会被自动提交，请刷新页面后重试。"
          />
          <Button
            onClick={() => {
              window.location.reload();
            }}
          >
            刷新页面
          </Button>
        </Flex>
      );
    }
    return this.props.children;
  }
}