import { Empty } from 'antd';

export function SettingsPage() {
  return (
    <main className="settings-page">
      <div className="directory-head"><div><h1>设置</h1><p>登录信息、个人设置和机构成员统一放在左下角入口</p></div></div>
      <section className="settings-empty"><Empty description="成员和机构设置尚未接入当前 MVP API。" /></section>
    </main>
  );
}
