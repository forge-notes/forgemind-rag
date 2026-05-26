import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  project?: string;
  stage?: string;
  version?: string;
  checked_at?: string;
};

type DocumentItem = {
  id: number;
  filename: string;
  stored_filename?: string;
  file_size: number;
  parse_status: "uploaded" | "parsing" | "parsed" | "failed";
  chunk_count: number;
  uploaded_at: string;
  parsed_at?: string | null;
};

type ChunkItem = {
  id: number;
  document_id: number;
  chunk_index: number;
  content: string;
  page_number: number | null;
  char_count: number;
  created_at: string;
};

type LoginState =
  | { status: "idle"; message: string }
  | { status: "checking"; message: string }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type CheckState =
  | { status: "idle"; message: string }
  | { status: "checking"; message: string }
  | { status: "success"; message: string; data: HealthResponse }
  | { status: "error"; message: string };

type UploadState =
  | { status: "idle"; message: string }
  | { status: "uploading"; message: string }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

const roadmap = [
  "登录与用户管理",
  "文档上传",
  "文档解析与切分",
  "向量化入库",
  "RAG 问答",
];

const parseStatusLabel: Record<DocumentItem["parse_status"], string> = {
  uploaded: "未解析",
  parsing: "解析中",
  parsed: "已解析",
  failed: "解析失败",
};

const backendBaseUrl =
  import.meta.env.VITE_BACKEND_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatUploadTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function App() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [token, setToken] = useState("");
  const [loginState, setLoginState] = useState<LoginState>({
    status: "idle",
    message: "请输入演示账号登录",
  });
  const [checkState, setCheckState] = useState<CheckState>({
    status: "idle",
    message: "等待检查",
  });
  const [uploadState, setUploadState] = useState<UploadState>({
    status: "idle",
    message: "支持 PDF 和 Markdown 文件",
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentsMessage, setDocumentsMessage] = useState("登录后加载文档列表");
  const [parsingDocumentId, setParsingDocumentId] = useState<number | null>(null);
  const [chunkDocument, setChunkDocument] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [chunksMessage, setChunksMessage] = useState("选择文档查看切分结果");

  const backendHealthUrl = useMemo(() => `${backendBaseUrl}/api/health`, []);
  const loginUrl = useMemo(() => `${backendBaseUrl}/api/auth/login`, []);
  const documentsUrl = useMemo(() => `${backendBaseUrl}/api/documents`, []);
  const uploadUrl = useMemo(
    () => `${backendBaseUrl}/api/documents/upload`,
    [],
  );

  async function loadDocuments() {
    setDocumentsMessage("正在加载文档列表...");

    try {
      const response = await fetch(documentsUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { documents: DocumentItem[] };
      setDocuments(data.documents);
      setDocumentsMessage(
        data.documents.length > 0 ? "文档列表已更新" : "暂无已上传文档",
      );
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setDocumentsMessage(`文档列表加载失败：${detail}`);
    }
  }

  useEffect(() => {
    if (token) {
      void loadDocuments();
    }
  }, [token]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginState({ status: "checking", message: "正在登录..." });

    try {
      const response = await fetch(loginUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { token: string };
      setToken(data.token);
      setLoginState({ status: "success", message: "登录成功" });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setLoginState({
        status: "error",
        message: `登录失败：${detail}`,
      });
    }
  }

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

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setUploadState({ status: "error", message: "请选择一个文件" });
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    setUploadState({ status: "uploading", message: "正在上传文档..." });

    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as DocumentItem;
      setUploadState({
        status: "success",
        message: `${data.filename} 上传成功`,
      });
      setSelectedFile(null);
      setFileInputKey((current) => current + 1);
      await loadDocuments();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setUploadState({
        status: "error",
        message: `上传失败：${detail}`,
      });
    }
  }

  async function parseDocument(document: DocumentItem) {
    setParsingDocumentId(document.id);
    setDocumentsMessage(`正在解析 ${document.filename}...`);

    try {
      const response = await fetch(`${documentsUrl}/${document.id}/parse`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const parsedDocument = (await response.json()) as DocumentItem;
      setDocuments((current) =>
        current.map((item) => (item.id === parsedDocument.id ? parsedDocument : item)),
      );
      setDocumentsMessage(
        `${parsedDocument.filename} 解析完成，共 ${parsedDocument.chunk_count} 个 chunk`,
      );
      await showChunks(parsedDocument);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setDocumentsMessage(`解析失败：${detail}`);
      await loadDocuments();
    } finally {
      setParsingDocumentId(null);
    }
  }

  async function showChunks(document: DocumentItem) {
    setChunkDocument(document);
    setChunks([]);
    setChunksMessage(`正在加载 ${document.filename} 的切分结果...`);

    try {
      const response = await fetch(`${documentsUrl}/${document.id}/chunks`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as {
        document: DocumentItem;
        chunks: ChunkItem[];
      };
      setChunkDocument(data.document);
      setChunks(data.chunks);
      setChunksMessage(
        data.chunks.length > 0 ? "切分结果已加载" : "暂无 chunk，请先解析文档",
      );
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setChunksMessage(`切分结果加载失败：${detail}`);
    }
  }

  if (!token) {
    return (
      <main className="app-shell login-shell">
        <section className="login-panel">
          <div>
            <p className="eyebrow">Enterprise Knowledge Agent</p>
            <h1>登录工作台</h1>
            <p className="muted">Day 3 文档解析与切分。</p>
          </div>

          <form className="login-form" onSubmit={handleLogin}>
            <label>
              用户名
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>

            <label>
              密码
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            <button
              className="primary-action"
              disabled={loginState.status === "checking"}
              type="submit"
            >
              {loginState.status === "checking" ? "登录中..." : "登录"}
            </button>

            <p className={`form-message ${loginState.status}`}>
              {loginState.message}
            </p>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <section className="workspace-header">
        <div>
          <p className="eyebrow">Enterprise Knowledge Agent</p>
          <h1>企业知识代理工作台</h1>
        </div>
        <div className="stage-pill">Day 3</div>
      </section>

      <section className="status-grid">
        <div className="panel stage-panel">
          <p className="label">当前阶段</p>
          <h2>文档解析与文本切分</h2>
          <p className="muted">
            当前版本将上传文件写入 MySQL，支持 PDF/Markdown 解析，并把文本保存为
            800-1000 字符左右的 chunk。
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

      <section className="document-grid">
        <form className="panel upload-panel" onSubmit={handleUpload}>
          <div>
            <p className="label">文档上传</p>
            <h2>上传 PDF 或 Markdown</h2>
            <p className={`form-message ${uploadState.status}`}>
              {uploadState.message}
            </p>
          </div>

          <label className="file-picker">
            <span>{selectedFile ? selectedFile.name : "选择文件"}</span>
            <input
              accept=".pdf,.md,.markdown,application/pdf,text/markdown"
              key={fileInputKey}
              type="file"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
            />
          </label>

          <button
            className="primary-action"
            disabled={uploadState.status === "uploading"}
            type="submit"
          >
            {uploadState.status === "uploading" ? "上传中..." : "上传文档"}
          </button>
        </form>

        <section className="panel documents-panel">
          <div className="documents-header">
            <div>
              <p className="label">已上传文档</p>
              <h2>解析队列</h2>
            </div>
            <button
              className="secondary-action"
              type="button"
              onClick={loadDocuments}
            >
              刷新
            </button>
          </div>

          <p className="documents-message">{documentsMessage}</p>

          <div className="document-list">
            {documents.map((document) => (
              <article className="document-item" key={document.id}>
                <div className="document-main">
                  <div>
                    <h3>{document.filename}</h3>
                    <p>
                      {formatFileSize(document.file_size)} ·{" "}
                      {formatUploadTime(document.uploaded_at)}
                    </p>
                  </div>
                  <div className="document-meta">
                    <span className={`status-badge ${document.parse_status}`}>
                      {parseStatusLabel[document.parse_status]}
                    </span>
                    <span>{document.chunk_count} chunks</span>
                  </div>
                </div>
                <div className="document-actions">
                  <button
                    className="secondary-action"
                    disabled={parsingDocumentId === document.id}
                    type="button"
                    onClick={() => void parseDocument(document)}
                  >
                    {parsingDocumentId === document.id ? "解析中..." : "解析文档"}
                  </button>
                  <button
                    className="secondary-action"
                    type="button"
                    onClick={() => void showChunks(document)}
                  >
                    查看切分结果
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>

      <section className="panel chunks-panel">
        <div>
          <p className="label">切分结果</p>
          <h2>{chunkDocument ? chunkDocument.filename : "等待选择文档"}</h2>
          <p className="documents-message">{chunksMessage}</p>
        </div>

        <div className="chunk-list">
          {chunks.slice(0, 5).map((chunk) => (
            <article className="chunk-item" key={chunk.id}>
              <div className="chunk-header">
                <span>Chunk {chunk.chunk_index + 1}</span>
                <span>
                  {chunk.page_number ? `第 ${chunk.page_number} 页 · ` : ""}
                  {chunk.char_count} 字符
                </span>
              </div>
              <p>{chunk.content}</p>
            </article>
          ))}
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
