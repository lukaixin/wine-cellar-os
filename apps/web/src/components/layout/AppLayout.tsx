import type { ReactNode } from "react";
import { api } from "../../api";
import { pageTitle, type Page } from "../../domain/constants";

export function AppLayout({
  page,
  setPage,
  error,
  notice,
  loading,
  refresh,
  children,
}: {
  page: Page;
  setPage: (page: Page) => void;
  error: string | null;
  notice: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">Wine Cellar OS</div>
          <div className="subtle">本地酒窖管理 Alpha</div>
        </div>
        <nav>
          <button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}>Dashboard</button>
          <button className={page === "collection" ? "active" : ""} onClick={() => setPage("collection")}>Collection Explorer</button>
          <button className={page === "bottles" ? "active" : ""} onClick={() => setPage("bottles")}>藏酒列表</button>
          <button className={page === "add" ? "active" : ""} onClick={() => setPage("add")}>新增入库</button>
          <button className={page === "import" ? "active" : ""} onClick={() => setPage("import")}>库存导入</button>
          <button className={page === "registry-search" ? "active" : ""} onClick={() => setPage("registry-search")}>Registry Search</button>
          <button className={page === "registry" ? "active" : ""} onClick={() => setPage("registry")}>Registry Quality</button>
          <button className={page === "label" ? "active" : ""} onClick={() => setPage("label")}>酒标入库</button>
          <button className={page === "cellar" ? "active" : ""} onClick={() => setPage("cellar")}>酒柜地图</button>
          <button className={page === "transactions" ? "active" : ""} onClick={() => setPage("transactions")}>Transaction</button>
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <h1>{pageTitle(page)}</h1>
            <span className="subtle">{new Date().toLocaleDateString("zh-CN")}</span>
          </div>
          <div className="topbar-actions">
            <a className="button secondary" href={api.bottleCsvUrl()}>导出 CSV</a>
            <button className="secondary" onClick={refresh}>刷新</button>
          </div>
        </header>

        {error && <div className="banner error">{error}</div>}
        {notice && <div className="banner success">{notice}</div>}
        {loading ? <div className="empty">加载中</div> : children}
      </main>
    </div>
  );
}
