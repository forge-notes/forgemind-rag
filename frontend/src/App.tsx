import { useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  project?: string;
  stage?: string;
  version?: string;
  checked_at?: string;
};

type CheckState =
  | { status: "idle"; message: string }
  | { status: "checking"; message: string }
  | { status: "success"; message: string; data: HealthResponse }
  | { status: "error"; message: string };

const roadmap = [
  "登录与用户管理",
  "文档上传与解析",
  "企业知识库",
  "RAG 问答",
  "权限与 RBAC",
];

const backendBaseUrl =
  import.meta.env.VITE_BACKEND_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

function App() {
  const [checkState, setCheckState] = useState<CheckState>({
    status: "idle",
    message: "等待检查",
  });

  const backendHealthUrl = useMemo(
    () => `${backendBaseUrl}/api/health`,
    [],
  );

  async function checkBackendConnection() {
    setCheckState({ status: "checking", message: "正在连接后端..." });

    try {
      const response = await fetch(backendHealthUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as HealthResponse;
      setCheckState({
        status: "success",
        message: `后端连接正常，版本 ${data.version ?? "unknown"}`,
        data,
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setCheckState({
        status: "error",
        message: `后端连接失败：${detail}`,
      });
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace-header">
        <div>
          <p className="eyebrow">Enterprise Knowledge Agent</p>
          <h1>企业知识代理工作台</h1>
        </div>
        <div className="stage-pill">Day 1</div>
      </section>

      <section className="status-grid">
        <div className="panel stage-panel">
          <p className="label">当前阶段</p>
          <h2>工程初始化和 Docker Compose 可运行底座</h2>
          <p className="muted">
            FastAPI、React、MySQL 8、Qdrant 已纳入同一套容器编排。
          </p>
        </div>

        <div className="panel connection-panel">
          <div className="connection-copy">
            <p className="label">后端状态</p>
            <p className={`connection-state ${checkState.status}`}>
              <span aria-hidden="true" />
              {checkState.message}
            </p>
          </div>
          <button
            className="primary-action"
            type="button"
            onClick={checkBackendConnection}
            disabled={checkState.status === "checking"}
          >
            {checkState.status === "checking" ? "检查中..." : "检查后端连接"}
          </button>
          {checkState.status === "success" ? (
            <dl className="health-detail">
              <div>
                <dt>服务</dt>
                <dd>{checkState.data.service}</dd>
              </div>
              <div>
                <dt>阶段</dt>
                <dd>{checkState.data.stage}</dd>
              </div>
              <div>
                <dt>接口</dt>
                <dd>/api/health</dd>
              </div>
            </dl>
          ) : null}
        </div>
      </section>

      <section className="roadmap-section">
        <div className="section-heading">
          <p className="label">功能规划</p>
          <h2>后续迭代方向</h2>
        </div>
        <div className="roadmap-grid">
          {roadmap.map((item, index) => (
            <article className="roadmap-item" key={item}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h3>{item}</h3>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export default App;
