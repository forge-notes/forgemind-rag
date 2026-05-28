# Demo Script

本文档用于面试或项目演示时按步骤展示 Enterprise Knowledge Agent 的完整最小闭环。

## 访问地址

- 前端：http://192.168.3.93:5173
- 后端 API 文档：http://192.168.3.93:8000/docs
- Qdrant Dashboard：http://192.168.3.93:6333/dashboard

## 1. 登录

1. 打开前端页面。
2. 使用演示账号登录：
   - Username: `admin`
   - Password: `admin123`
3. 登录成功后进入企业知识代理工作台。

演示重点：

- 当前版本是最小可用登录，不实现 JWT、RBAC 或多用户权限。
- 重点展示 RAG 知识库流程，不把复杂权限系统混入 Day 7 范围。

## 2. 上传文档

1. 在“文档上传”区域选择 PDF 或 Markdown 文件。
2. 点击“上传文档”。
3. 在“已上传文档”列表中确认文件出现。

演示重点：

- 文件保存到宿主机 `./uploads`，容器内路径是 `/app/uploads`。
- 文档元数据写入 MySQL `documents` 表。

## 3. 解析文档

1. 在文档列表中找到刚上传的文件。
2. 点击“解析文档”。
3. 等待解析状态变为“已解析”。
4. 检查 chunk 数量是否更新。

演示重点：

- PDF 使用 PyMuPDF 解析文本。
- Markdown 直接读取文本。
- 解析状态从 `uploaded` 变为 `parsing`，成功后变为 `parsed`，失败后变为 `failed`。

## 4. 查看切分结果

1. 点击“查看切分结果”。
2. 查看前几个 chunk 的内容。
3. 对 PDF 文档，检查是否显示页码。
4. 检查每个 chunk 的字符数。

演示重点：

- chunk 大小约 800-1000 字符。
- overlap 约 100-150 字符。
- chunks 保存到 MySQL `document_chunks` 表。

## 5. 向量化

1. 确认文档已解析。
2. 点击“向量化”。
3. 等待向量化状态变为“已向量化”。

演示重点：

- 使用 Ollama `bge-m3:latest` 生成 embedding。
- 向量写入 Qdrant collection `knowledge_chunks`。
- payload 包含 `document_id`、`chunk_id`、`filename`、`chunk_index`、`page_number`、`content`。
- `bge-m3` 只用于 embedding，不用于生成回答。

## 6. RAG 问答

1. 在“知识库问答”区域输入问题。
2. 可以使用示例问题快速演示：
   - 这个人有哪些技术负责人经验？
   - 他熟悉哪些技术栈？
   - 他有没有 Docker 和 CI/CD 经验？
   - 他有没有企业系统重构经验？
   - 他适合什么类型的软件开发岗位？
3. 点击“发送”。
4. 等待后端检索 chunks 并调用本地 LLM 生成回答。

演示重点：

- 问题先通过同一个 embedding service 向量化。
- 系统从 Qdrant 检索 top-k 相关 chunks。
- 后端把 chunks 组装为参考资料 context。
- Ollama 聊天模型只基于参考资料生成回答。

## 7. 查看来源引用

1. 查看回答下方的来源引用卡片。
2. 重点说明每个来源包含：
   - 文档名
   - 页码
   - chunk index
   - score
   - 内容预览

演示重点：

- 回答不是孤立文本，而是可追溯到原始文档片段。
- 当资料不足时，Prompt 要求模型明确说明“当前知识库中没有找到足够信息”。

## 8. 查看问答历史

1. 完成一次问答后，查看右侧“问答历史”。
2. 刷新页面。
3. 重新登录或进入工作台后，确认最近问答记录仍然存在。
4. 点击历史问题，回看对应 answer 和 sources。

演示重点：

- 问答历史保存在 MySQL `qa_records` 表。
- 当前只保存单轮问答，不实现多轮聊天。
- 最近 20 条按 `created_at` 倒序返回。

## 收尾说明

当前项目用于展示企业知识库 RAG 工程闭环，暂不包含 RBAC、多租户、MinIO、Redis、Celery、流式输出和生产级 Nginx 部署。
