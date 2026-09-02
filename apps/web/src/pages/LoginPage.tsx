import { useMutation } from '@tanstack/react-query';
import { Alert, Button, Card, Divider, Form, Input, Layout, Space, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { login } from '@/api/auth';
import { setAccessToken } from '@/api/session';

interface LoginFormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const session = useMutation({
    mutationFn: login,
    onSuccess: (response) => {
      setAccessToken(response.data.access_token);
      void navigate('/cases');
    },
  });

  function submit(values: LoginFormValues) {
    session.mutate(values);
  }

  return (
    <Layout className="app-shell login-shell">
      <main className="login-panel">
        <Space direction="vertical" size={24} className="full-width">
          <div>
            <Typography.Title level={1} className="login-title">
              TaxMind Pro
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              财税机构内部专业辅助系统
            </Typography.Paragraph>
          </div>
          <Alert
            type="warning"
            showIcon
            message="内部专业辅助"
            description="仅用于内部分析与客户答复草稿。政策结论和对外意见必须由专业人员审核。"
          />
          <Card title="登录工作台">
            <Form<LoginFormValues> layout="vertical" requiredMark="optional" onFinish={submit}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}
              >
                <Input autoComplete="email" placeholder="name@example.com" />
              </Form.Item>
              <Form.Item
                label="密码"
                name="password"
                rules={[{ required: true, min: 12, message: '密码至少需要 12 个字符' }]}
              >
                <Input.Password autoComplete="current-password" />
              </Form.Item>
              {session.isError ? (
                <Alert
                  className="form-alert"
                  type="error"
                  showIcon
                  message="登录未完成"
                  description="请检查账号、密码和后端服务状态后重试。"
                />
              ) : null}
              <Button type="primary" htmlType="submit" loading={session.isPending} block>
                登录并进入我的工作台
              </Button>
            </Form>
            <Divider plain>或</Divider>
            <Button block onClick={() => void navigate('/cases?preview=1')}>
              进入虚构数据预览
            </Button>
          </Card>
        </Space>
      </main>
    </Layout>
  );
}
