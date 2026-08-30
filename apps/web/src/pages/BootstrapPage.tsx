import { Alert, Card, Col, Layout, Row, Space, Typography } from 'antd';

import { ApiHealthCard } from '@/components/status/ApiHealthCard';

const { Header, Content, Footer } = Layout;

export function BootstrapPage() {
  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div>
          <Typography.Title level={3} className="brand-title">
            TaxMind Pro
          </Typography.Title>
          <Typography.Text className="brand-subtitle">财税机构内部专业辅助系统</Typography.Text>
        </div>
      </Header>
      <Content className="app-content">
        <Space direction="vertical" size={24} className="full-width">
          <Alert
            type="warning"
            showIcon
            message="内部专业辅助"
            description="系统只生成内部分析和客户答复草稿，不构成正式税务意见；任何专业结论必须经过人工审核。"
          />
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={15}>
              <Card>
                <Typography.Title level={2}>工程基座已建立</Typography.Title>
                <Typography.Paragraph>
                  当前只开放运行状态验证。事项、政策检索、风险审查、办税指导、审核和知识运营将在后续阶段按契约逐项实现。
                </Typography.Paragraph>
                <Typography.Paragraph type="secondary">
                  未接入真实客户数据、真实模型密钥、官方站点采集或自动申报能力。
                </Typography.Paragraph>
              </Card>
            </Col>
            <Col xs={24} lg={9}>
              <ApiHealthCard />
            </Col>
          </Row>
        </Space>
      </Content>
      <Footer className="app-footer">TaxMind Pro · Bootstrap v0.1</Footer>
    </Layout>
  );
}