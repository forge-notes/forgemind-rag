import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  project?: string;
  stage?: string;
  version?: string;
  checked_at?: string;
};

type ParseStatus = "uploaded" | "parsing" | "parsed" | "failed";
type EmbeddingStatus = "pending" | "embedding" | "embedded" | "failed";

type DocumentItem = {
  id: number;
  filename: string;
  stored_filename?: string;
  file_size: number;
  parse_status: ParseStatus;
  chunk_count: number;
  embedding_status?: EmbeddingStatus;
  uploaded_at: string;
  parsed_at?: string | null;
  embedded_at?: string | null;
};

type ChunkItem = {
  id: number;
  document_id: number;
  chunk_index: number;
  content: string;
  page_number: number | null;
  char_count: number;
  vector_id?: string | null;
  embedding_status?: EmbeddingStatus;
  created_at: string;
  embedded_at?: string | null;
};

type SearchResult = {
  document_id: number;
  filename: string;
  chunk_id: number;
  chunk_index: number;
  page_number: number | null;
  score: number;
  content: string;
};

type RagSource = {
  document_id: number;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  score: number;
  content: string;
};

type QARecord = {
  id: number;
  question: string;
  answer: string;
  sources: RagSource[];
  model_name: string;
  top_k: number;
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

type SearchState =
  | { status: "idle"; message: string }
  | { status: "searching"; message: string }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type AskState =
  | { status: "idle"; message: string }
  | { status: "asking"; message: string }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

const roadmap = [
  "登录与用户管理",
  "文档上传",
  "文档解析与切分",
  "向量化检索",
  "RAG 问答",
  "问答历史",
];

const exampleQuestions = [
  "这个人有哪些技术负责人经验？",
  "他熟悉哪些技术栈？",
  "他有没有 Docker 和 CI/CD 经验？",
  "他有没有企业系统重构经验？",
  "他适合什么类型的软件开发岗位？",
];

const parseStatusLabel: Record<ParseStatus, string> = {
  uploaded: "未解析",
  parsing: "解析中",
  parsed: "已解析",
  failed: "解析失败",
};

const embeddingStatusLabel: Record<EmbeddingStatus, string> = {
  pending: "未向量化",
  embedding: "向量化中",
  embedded: "已向量化",
  failed: "向量化失败",
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

function previewContent(content: string, limit = 260) {
  const normalized = content.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }

  return `${normalized.slice(0, limit)}...`;
}

async function ensureOk(response: Response) {
  if (response.ok) {
    return;
  }

  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") {
      throw new Error(data.detail);
    }
  } catch (error) {
    if (error instanceof Error && !error.message.startsWith("Unexpected")) {
      throw error;
    }
  }

  throw new Error(`HTTP ${response.status}`);
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
  const [embeddingDocumentId, setEmbeddingDocumentId] = useState<number | null>(null);
  const [chunkDocument, setChunkDocument] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [chunksMessage, setChunksMessage] = useState("选择文档查看切分结果");
  const [searchQuery, setSearchQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [searchState, setSearchState] = useState<SearchState>({
    status: "idle",
    message: "输入问题后检索 Qdrant 中的相关片段",
  });
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [ragQuestion, setRagQuestion] = useState("");
  const [ragTopK, setRagTopK] = useState(5);
  const [askState, setAskState] = useState<AskState>({
    status: "idle",
    message: "输入问题后基于知识库生成回答",
  });
  const [ragAnswer, setRagAnswer] = useState("");
  const [ragSources, setRagSources] = useState<RagSource[]>([]);
  const [qaHistory, setQaHistory] = useState<QARecord[]>([]);
  const [historyMessage, setHistoryMessage] = useState("登录后加载问答历史");
  const [activeRecordId, setActiveRecordId] = useState<number | null>(null);

  const backendHealthUrl = useMemo(() => `${backendBaseUrl}/api/health`, []);
  const loginUrl = useMemo(() => `${backendBaseUrl}/api/auth/login`, []);
  const documentsUrl = useMemo(() => `${backendBaseUrl}/api/documents`, []);
  const uploadUrl = useMemo(
    () => `${backendBaseUrl}/api/documents/upload`,
    [],
  );
  const searchUrl = useMemo(() => `${backendBaseUrl}/api/search`, []);
  const askUrl = useMemo(() => `${backendBaseUrl}/api/ask`, []);
  const historyUrl = useMemo(() => `${backendBaseUrl}/api/qa/history`, []);

  async function loadDocuments() {
    setDocumentsMessage("正在加载文档列表...");

    try {
      const response = await fetch(documentsUrl);
      await ensureOk(response);

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

  async function loadQaHistory() {
    setHistoryMessage("正在加载问答历史...");

    try {
      const response = await fetch(historyUrl);
      await ensureOk(response);

      const data = (await response.json()) as { records: QARecord[] };
      setQaHistory(data.records);
      setHistoryMessage(
        data.records.length > 0 ? "最近 20 条问答已加载" : "暂无问答历史",
      );
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setHistoryMessage(`问答历史加载失败：${detail}`);
    }
  }

  useEffect(() => {
    if (token) {
      void loadDocuments();
      void loadQaHistory();
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
      await ensureOk(response);

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
      await ensureOk(response);

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
      await ensureOk(response);

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
      await ensureOk(response);

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

  async function embedDocument(document: DocumentItem) {
    setEmbeddingDocumentId(document.id);
    setDocumentsMessage(`正在向量化 ${document.filename}...`);

    try {
      const response = await fetch(`${documentsUrl}/${document.id}/embed`, {
        method: "POST",
      });
      await ensureOk(response);

      const embeddedDocument = (await response.json()) as DocumentItem;
      setDocuments((current) =>
        current.map((item) => (item.id === embeddedDocument.id ? embeddedDocument : item)),
      );
      setDocumentsMessage(`${embeddedDocument.filename} 向量化完成`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setDocumentsMessage(`向量化失败：${detail}`);
      await loadDocuments();
    } finally {
      setEmbeddingDocumentId(null);
    }
  }

  async function showChunks(document: DocumentItem) {
    setChunkDocument(document);
    setChunks([]);
    setChunksMessage(`正在加载 ${document.filename} 的切分结果...`);

    try {
      const response = await fetch(`${documentsUrl}/${document.id}/chunks`);
      await ensureOk(response);

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

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearchState({ status: "searching", message: "正在检索知识库..." });
    setSearchResults([]);

    try {
      const response = await fetch(searchUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: searchQuery, top_k: topK }),
      });
      await ensureOk(response);

      const data = (await response.json()) as {
        results: SearchResult[];
      };
      setSearchResults(data.results);
      setSearchState({
        status: "success",
        message:
          data.results.length > 0
            ? `找到 ${data.results.length} 个相关片段`
            : "没有找到相关片段",
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setSearchState({ status: "error", message: `检索失败：${detail}` });
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAskState({ status: "asking", message: "正在生成知识库回答..." });
    setRagAnswer("");
    setRagSources([]);

    try {
      const response = await fetch(askUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: ragQuestion, top_k: ragTopK }),
      });
      await ensureOk(response);

      const data = (await response.json()) as {
        answer: string;
        sources: RagSource[];
        record_id: number | null;
      };
      setRagAnswer(data.answer);
      setRagSources(data.sources);
      setActiveRecordId(data.record_id);
      setAskState({
        status: "success",
        message: data.sources.length > 0 ? "回答已生成" : "回答已生成，但没有来源片段",
      });
      await loadQaHistory();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      setAskState({ status: "error", message: `问答失败：${detail}` });
    }
  }

  function showHistoryRecord(record: QARecord) {
    setRagQuestion(record.question);
    setRagTopK(record.top_k);
    setRagAnswer(record.answer);
    setRagSources(record.sources);
    setActiveRecordId(record.id);
    setAskState({
      status: "success",
      message: "已载入历史问答",
    });
  }

  if (!token) {
    return (
      <main className="app-shell login-shell">
        <section className="login-panel">
          <div>
            <p className="eyebrow">Enterprise Knowledge Agent</p>
            <h1>登录工作台</h1>
            <p className="muted">Day 6 问答历史与体验优化。</p>
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
        <div className="stage-pill">Day 6</div>
      </section>

      <section className="status-grid">
        <div className="panel stage-panel">
          <p className="label">当前阶段</p>
          <h2>问答历史与体验优化</h2>
          <p className="muted">
            当前版本会保存单次问答记录，刷新页面后仍可查看最近 20 条回答和来源引用。
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
              <h2>解析与向量化队列</h2>
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
            {documents.map((document) => {
              const embeddingStatus = document.embedding_status ?? "pending";
              return (
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
                      <span className={`status-badge ${embeddingStatus}`}>
                        {embeddingStatusLabel[embeddingStatus]}
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
                      disabled={
                        document.parse_status !== "parsed" ||
                        embeddingDocumentId === document.id
                      }
                      type="button"
                      onClick={() => void embedDocument(document)}
                    >
                      {embeddingDocumentId === document.id ? "向量化中..." : "向量化"}
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
              );
            })}
          </div>
        </section>
      </section>

      <section className="qa-grid">
        <section className="panel ask-panel">
          <div>
            <p className="label">知识库问答</p>
            <h2>基于来源片段生成回答</h2>
            <p className={`documents-message ${askState.status}`}>
              {askState.message}
            </p>
          </div>

          <div className="example-question-row" aria-label="示例问题">
            {exampleQuestions.map((question) => (
              <button
                className="example-question"
                key={question}
                type="button"
                onClick={() => setRagQuestion(question)}
              >
                {question}
              </button>
            ))}
          </div>

          <form className="ask-form" onSubmit={handleAsk}>
            <label className="question-field">
              问题
              <textarea
                value={ragQuestion}
                onChange={(event) => setRagQuestion(event.target.value)}
                placeholder="输入一个希望基于知识库回答的问题"
              />
            </label>
            <label>
              Top K
              <input
                min={1}
                max={20}
                type="number"
                value={ragTopK}
                onChange={(event) => setRagTopK(Number(event.target.value))}
              />
            </label>
            <button
              className="primary-action"
              disabled={askState.status === "asking"}
              type="submit"
            >
              {askState.status === "asking" ? "生成中..." : "发送"}
            </button>
          </form>

          {ragAnswer ? (
            <article className="answer-box">
              <div className="answer-title">
                <span>回答</span>
                {activeRecordId ? <span>记录 #{activeRecordId}</span> : null}
              </div>
              <p>{ragAnswer}</p>
            </article>
          ) : null}

          <div className="source-list">
            {ragSources.map((source, index) => (
              <article
                className="source-item"
                key={`${source.document_id}-${source.chunk_index}-${index}`}
              >
                <div className="source-card-meta">
                  <span>{source.filename}</span>
                  <span>{source.page_number ? `第 ${source.page_number} 页` : "页码未知"}</span>
                  <span>Chunk {source.chunk_index + 1}</span>
                  <span>score {source.score.toFixed(4)}</span>
                </div>
                <p>{previewContent(source.content)}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel history-panel">
          <div className="documents-header">
            <div>
              <p className="label">问答历史</p>
              <h2>最近 20 条</h2>
            </div>
            <button
              className="secondary-action"
              type="button"
              onClick={() => void loadQaHistory()}
            >
              刷新
            </button>
          </div>

          <p className="documents-message">{historyMessage}</p>

          <div className="history-list">
            {qaHistory.map((record) => (
              <button
                className={`history-item ${record.id === activeRecordId ? "active" : ""}`}
                key={record.id}
                type="button"
                onClick={() => showHistoryRecord(record)}
              >
                <span>{record.question}</span>
                <small>
                  {formatUploadTime(record.created_at)} · {record.model_name} · top {record.top_k}
                </small>
              </button>
            ))}
          </div>
        </section>
      </section>

      <section className="panel search-panel">
        <div>
          <p className="label">知识库检索测试</p>
          <h2>从 Qdrant 返回相关片段</h2>
          <p className={`documents-message ${searchState.status}`}>
            {searchState.message}
          </p>
        </div>

        <form className="search-form" onSubmit={handleSearch}>
          <label>
            问题
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="输入一个检索问题"
            />
          </label>
          <label>
            Top K
            <input
              min={1}
              max={20}
              type="number"
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
            />
          </label>
          <button
            className="primary-action"
            disabled={searchState.status === "searching"}
            type="submit"
          >
            {searchState.status === "searching" ? "搜索中..." : "搜索"}
          </button>
        </form>

        <div className="search-results">
          {searchResults.map((result) => (
            <article className="search-result-item" key={`${result.chunk_id}-${result.score}`}>
              <div className="chunk-header">
                <span>{result.filename}</span>
                <span>
                  {result.page_number ? `第 ${result.page_number} 页 · ` : ""}
                  score {result.score.toFixed(4)}
                </span>
              </div>
              <h3>Chunk {result.chunk_index + 1}</h3>
              <p>{result.content}</p>
            </article>
          ))}
        </div>
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
