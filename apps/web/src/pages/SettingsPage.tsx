import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Empty, Form, Input, Modal, Select, Spin, Tag } from 'antd';
import { useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';

import { addOrganizationMember, getCurrentMembership, listOrganizationMembers, type MemberCreateRequest, type MemberUpdateRequest, updateOrganizationMember } from '@/api/organizations';
import { getAccessToken } from '@/api/session';

const roleOptions = [
  { value: 'org_admin', label: '机构管理员' }, { value: 'consultant', label: '顾问' },
  { value: 'reviewer', label: '复核人' }, { value: 'knowledge_admin', label: '知识管理员' }, { value: 'auditor', label: '审计员' },
];
const previewMembers = [
  { id: 'virtual-member-001', org_id: 'virtual-org-001', user_id: 'virtual-user-001', display_name: '李敏', email: 'li.min@example.invalid', role_code: 'org_admin', status: 'active', user_status: 'active', version_no: 1 },
  { id: 'virtual-member-002', org_id: 'virtual-org-001', user_id: 'virtual-user-002', display_name: '陈楠', email: 'chen.nan@example.invalid', role_code: 'consultant', status: 'active', user_status: 'active', version_no: 1 },
];

function roleLabel(roleCode: string) { return roleOptions.find((option) => option.value === roleCode)?.label ?? roleCode; }

export function SettingsPage() {
  const token = getAccessToken(); const client = useQueryClient(); const [params] = useSearchParams(); const preview = params.get('preview') === '1';
  const [inviteOpen, setInviteOpen] = useState(false); const [editingMemberId, setEditingMemberId] = useState<string | null>(null);
  const [inviteForm] = Form.useForm<MemberCreateRequest>(); const [editForm] = Form.useForm<MemberUpdateRequest>();
  const meQuery = useQuery({ queryKey: ['me'], enabled: !preview && token !== null, retry: false, queryFn: () => { if (token === null) throw new Error('成员设置不可用'); return getCurrentMembership(token); } });
  const orgId = preview ? 'virtual-org-001' : meQuery.data?.membership.org_id;
  const membersQuery = useQuery({ queryKey: ['organization-members', orgId], enabled: !preview && token !== null && orgId !== undefined, retry: false, queryFn: () => { if (token === null || orgId === undefined) throw new Error('成员列表不可用'); return listOrganizationMembers(orgId, token); } });
  const canManage = !preview && meQuery.data?.membership.role_code === 'org_admin';
  const addMember = useMutation({ mutationFn: (payload: MemberCreateRequest) => { if (token === null || orgId === undefined) throw new Error('邀请成员不可用'); return addOrganizationMember(orgId, payload, token); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ['organization-members', orgId] }); setInviteOpen(false); inviteForm.resetFields(); } });
  const updateMember = useMutation({ mutationFn: ({ memberId, payload }: { memberId: string; payload: MemberUpdateRequest }) => { if (token === null || orgId === undefined) throw new Error('成员更新不可用'); return updateOrganizationMember(orgId, memberId, payload, token); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ['organization-members', orgId] }); setEditingMemberId(null); } });
  if (!preview && token === null) return <Navigate replace to="/" />;
  const members = preview ? previewMembers : (membersQuery.data?.data ?? []); const loading = !preview && (meQuery.isLoading || membersQuery.isLoading); const failed = !preview && (meQuery.isError || membersQuery.isError); const editingMember = members.find((member) => member.id === editingMemberId);

  return <main className="settings-page"><div className="directory-head"><div><h1>设置</h1><p>登录信息、个人设置和机构成员统一放在左下角入口</p></div><Button disabled={!canManage} onClick={() => { setInviteOpen(true); }} type="primary">邀请成员</Button></div>
    <Alert className="directory-notice" message={preview ? '预览模式：仅展示虚构成员，邀请和编辑不会写入服务端' : '成员角色与状态由机构管理员维护，所有变更均记录审计'} showIcon type={preview ? 'info' : 'warning'} />
    <section className="settings-members-panel"><div className="settings-members-head"><div><h2>成员与权限</h2><p>{preview ? '虚构机构 · 仅用于界面预览' : `当前角色：${roleLabel(meQuery.data?.membership.role_code ?? '')}`}</p></div><Tag color={canManage ? 'blue' : 'default'}>{canManage ? '可管理成员' : '只读'}</Tag></div>
      {loading ? <div className="review-state"><Spin tip="正在加载成员" /></div> : null}{failed ? <Alert action={<Button size="small" onClick={() => { void meQuery.refetch(); void membersQuery.refetch(); }}>重试</Button>} message="成员信息加载失败或无权限" showIcon type="error" /> : null}{!loading && !failed && members.length === 0 ? <Empty description="暂无成员" /> : null}
      {!loading && !failed && members.length > 0 ? <div className="settings-members-list">{members.map((member) => <article className="settings-member-row" key={member.id}><div><strong>{member.display_name}</strong><span>{member.email ?? '未设置邮箱'} · {roleLabel(member.role_code)}</span></div><div><span className="directory-badge is-blue">{member.status}</span><Button disabled={!canManage} size="small" type="text" onClick={() => { editForm.setFieldsValue({ role_code: member.role_code, status: member.status, version_no: member.version_no }); setEditingMemberId(member.id); }}>编辑</Button></div></article>)}</div> : null}
    </section>
    <Modal footer={null} onCancel={() => { setInviteOpen(false); }} open={inviteOpen} title="邀请成员"><Form<MemberCreateRequest> form={inviteForm} layout="vertical" onFinish={(values) => { addMember.mutate(values); }}><Form.Item label="邮箱" name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}><Input /></Form.Item><Form.Item label="角色" name="role_code" rules={[{ required: true, message: '请选择角色' }]}><Select options={roleOptions} /></Form.Item>{addMember.isError ? <Alert message="邀请失败，请检查账号状态、权限和机构范围。" showIcon type="error" /> : null}<Button htmlType="submit" loading={addMember.isPending} type="primary">发送邀请</Button></Form></Modal>
    <Modal footer={null} onCancel={() => { setEditingMemberId(null); }} open={editingMember !== undefined} title="编辑成员"><Form<MemberUpdateRequest> form={editForm} layout="vertical" onFinish={(values) => { if (editingMember !== undefined) updateMember.mutate({ memberId: editingMember.id, payload: values }); }}><Form.Item label="角色" name="role_code" rules={[{ required: true }]}><Select options={roleOptions} /></Form.Item><Form.Item label="状态" name="status" rules={[{ required: true }]}><Select options={[{ value: 'active', label: '启用' }, { value: 'disabled', label: '停用' }]} /></Form.Item><Form.Item hidden name="version_no"><Input type="hidden" /></Form.Item>{updateMember.isError ? <Alert message="保存失败，成员可能已被其他操作更新。请刷新后重试。" showIcon type="error" /> : null}<Button htmlType="submit" loading={updateMember.isPending} type="primary">保存变更</Button></Form></Modal>
  </main>;
}
