import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Layout,
  List,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { searchProcedures, type ProcedureSearchResponse } from '@/api/procedures';
import { getAccessToken } from '@/api/session';

const { Header, Content, Footer } = Layout;

interface ProcedureFormValues {
  query: string;
  region: string;
  date: string;
}

const previewData: ProcedureSearchResponse = {
  data: [
    {
      procedure_version_id: 'virtual-procedure-v1',
      procedure_code: 'invoice-red-letter',
      title: '虚构红字发票开具指引',
      region_code: '440300',
      region_match: 'local',
      effective_start: '2026-01-01',
      effective_end: null,
      official_url: 'https://example.invalid/procedure',
      source_chunk_ids: ['virtual:procedure:article_1'],
      materials: ['虚构材料清单'],
      channels: ['线上办理'],
    },
  ],
  meta: { request_id: 'preview-only' },
};

export function ProceduresPage() {
  const accessToken = getAccessToken();
  const navigate = useNavigate();
  const [searchParameters] = useSearchParams();
  const isPreview = searchParameters.get('preview') === '1';
  const [input, setInput] = useState<ProcedureFormValues | null>(null);
  const result = useQuery({
    queryKey: ['procedures', input],
    enabled: !isPreview && input !== null && accessToken !== null,
    retry: false,
    queryFn: () => {
      if (input === null || accessToken === null) {
        throw new Error('办税事项查询不可用');
      }
      return searchProcedures(input.query, input.region, input.date, accessToken);
    },
  });

  if (!isPreview && accessToken === null) {
    return <Navigate to="/" replace />;
  }

  const displayedData = isPreview ? previewData : result.data;

  function submit(values: ProcedureFormValues) {
    setInput({
      query: values.query.trim(),
      region: values.region,
      date: values.date,
    });
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header policy-header">
        <div>
          <Typography.Title level={3} className="brand-title">
            TaxMind Pro
          </Typography.Title>
          <Typography.Text className="brand-subtitle">办税事项库</Typography.Text>
        </div>
        <Button onClick={() => void navigate(`/cases${isPreview ? '?preview=1' : ''}`)}>
          前往事项工作台
        </Button>
      </Header>
      <Content className="app-content">
        <Space direction="vertical" size={24} className="full-width">
          <Alert
            type={isPreview ? 'info' : 'warning'}
            showIcon
            message={
              isPreview
                ? '预览模式：仅展示虚构办税事项'
                : '内部专业辅助：请核验地区、日期与官方来源'
            }
            description={
              isPreview
                ? '该页面不访问真实办税资料；正式结果仅返回已审核发布的事项版本。'
                : '事项指引不替代正式税务意见或主管机关的最终办理要求。'
            }
          />
          <Card title="办税事项查询">
            <Form<ProcedureFormValues>
              layout="vertical"
              initialValues={{ region: '440300', date: '2026-09-01' }}
              onFinish={submit}
            >
              <div className="policy-search-grid">
                <Form.Item
                  label="事项名称或编码"
                  name="query"
                  rules={[{ required: true, message: '请输入事项名称或编码' }]}
                >
                  <Input placeholder="例如：红字发票、invoice-red-letter" allowClear />
                </Form.Item>
                <Form.Item
                  label="地区代码"
                  name="region"
                  rules={[{ required: true, pattern: /^\d{6}$/, message: '请输入六位地区代码' }]}
                >
                  <Input inputMode="numeric" maxLength={6} />
                </Form.Item>
                <Form.Item label="业务发生日" name="date" rules={[{ required: true }]}>
                  <Input type="date" />
                </Form.Item>
                <Form.Item className="policy-search-action">
                  <Button type="primary" htmlType="submit" loading={!isPreview && result.isFetching}>
                    {isPreview ? '查看虚构预览结果' : '查询已发布事项'}
                  </Button>
                </Form.Item>
              </div>
            </Form>
          </Card>
          <section aria-live="polite">
            {!isPreview && result.isFetching ? <Spin tip="正在筛选已发布事项…" /> : null}
            {!isPreview && result.isError ? (
              <Alert
                type="error"
                showIcon
                message="办税事项查询未完成"
                description="请检查登录权限、后端服务和查询条件后重试。"
                action={<Button onClick={() => void result.refetch()}>重试</Button>}
              />
            ) : null}
            {displayedData !== undefined && displayedData.data.length === 0 ? (
              <Empty description="当前条件下没有已发布办税事项" />
            ) : null}
            <List
              dataSource={displayedData?.data ?? []}
              renderItem={(item) => (
                <List.Item key={item.procedure_version_id}>
                  <Card title={item.title} className="full-width">
                    <Space direction="vertical" size={12}>
                      <Space wrap>
                        <Tag>{item.procedure_code}</Tag>
                        <Tag color={item.region_match === 'local' ? 'blue' : 'gold'}>
                          {item.region_match === 'local' ? '本地地区匹配' : '全国口径回退'}
                        </Tag>
                      </Space>
                      <Typography.Text>
                        材料：{item.materials.length > 0 ? item.materials.join('、') : '待核实'}
                      </Typography.Text>
                      <Typography.Text>
                        渠道：{item.channels.length > 0 ? item.channels.join('、') : '待核实'}
                      </Typography.Text>
                      <Typography.Link href={item.official_url} target="_blank">
                        官方办理入口
                      </Typography.Link>
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          </section>
        </Space>
      </Content>
      <Footer className="app-footer">TaxMind Pro · 内部专业辅助</Footer>
    </Layout>
  );
}
