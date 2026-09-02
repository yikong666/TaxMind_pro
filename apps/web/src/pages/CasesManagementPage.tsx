import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Empty, Spin } from 'antd';
import { Plus } from 'lucide-react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { listCases, type CasesResponse } from '@/api/cases';
import { getAccessToken } from '@/api/session';

const previewCases: CasesResponse = {
  data: [
    {
      id: 'virtual-case-001',
      case_no: 'CASE-20260901-VIRTUAL-1',
      title: '季度开票与优惠咨询',
      status: 'draft',
      owner_user_id: 'virtual-user-001',
      default_region_code: '440300',
      current_profile_version: 1,
      version_no: 1,
    },
    {
      id: 'virtual-case-002',
      case_no: 'CASE-20260901-VIRTUAL-2',
      title: '申报错误更正咨询',
      status: 'draft',
      owner_user_id: 'virtual-user-001',
      default_region_code: '440300',
      current_profile_version: 1,
      version_no: 1,
    },
    {
      id: 'virtual-case-003',
      case_no: 'CASE-20260901-VIRTUAL-3',
      title: '小规模政策核验',
      status: 'draft',
      owner_user_id: 'virtual-user-001',
      default_region_code: '440300',
      current_profile_version: 1,
      version_no: 1,
    },
  ],
  meta: { request_id: 'preview-only' },
};

function statusLabel(status: string) {
  if (status === 'draft') return '待补充';
  return status;
}

export function CasesManagementPage() {
  const navigate = useNavigate();
  const [searchParameters] = useSearchParams();
  const accessToken = getAccessToken();
  const isPreview = searchParameters.get('preview') === '1';
  const casesQuery = useQuery({
    queryKey: ['cases'],
    queryFn: () => {
      if (accessToken === null) throw new Error('事项列表不可用');
      return listCases(accessToken);
    },
    enabled: !isPreview && accessToken !== null,
  });

  if (!isPreview && accessToken === null) return <Navigate replace to="/" />;

  const cases = isPreview ? previewCases.data : (casesQuery.data?.data ?? []);
  const openWorkbench = () => navigate(isPreview ? '/cases?preview=1' : '/cases');
  const createCase = () => navigate(isPreview ? '/cases?preview=1&create=1' : '/cases?create=1');

  return (
    <main className="case-management-page">
      <div className="case-management-heading">
        <div>
          <h1>我的事项</h1>
          <p>只显示当前需要处理的项目，不堆叠无关信息</p>
        </div>
        <Button icon={<Plus aria-hidden="true" size={16} />} type="primary" onClick={() => void createCase()}>
          新建事项
        </Button>
      </div>

      <div aria-label="事项状态筛选" className="case-management-segment">
        <button aria-pressed="true" type="button">全部项目</button>
        <span>状态以服务端返回为准</span>
      </div>

      {casesQuery.isLoading && !isPreview ? (
        <div className="case-management-state"><Spin tip="正在加载事项" /></div>
      ) : null}
      {casesQuery.isError && !isPreview ? (
        <Alert
          action={<Button size="small" onClick={() => void casesQuery.refetch()}>重试</Button>}
          message="事项列表加载失败，请检查网络后重试。"
          showIcon
          type="error"
        />
      ) : null}
      {!casesQuery.isLoading && !casesQuery.isError && cases.length === 0 ? (
        <div className="case-management-state"><Empty description="暂时没有事项，先创建一个开始工作。" /></div>
      ) : null}
      {cases.length > 0 ? (
        <section className="case-management-panel">
          <table>
            <thead>
              <tr>
                <th>项目</th>
                <th>下一步</th>
                <th>状态</th>
                <th>信息</th>
                <th aria-label="操作" />
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.title}</strong>
                    <span>{item.case_no}</span>
                  </td>
                  <td>进入工作台继续处理</td>
                  <td><span className="case-status">{statusLabel(item.status)}</span></td>
                  <td>地区 {item.default_region_code} · 画像 v{item.current_profile_version}</td>
                  <td>
                    <Button aria-label={`继续处理${item.title}`} size="small" type="text" onClick={() => void openWorkbench()}>
                      继续
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </main>
  );
}
