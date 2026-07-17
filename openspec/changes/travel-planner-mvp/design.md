## Context

本项目为全新 Web 应用，目标是构建一个旅游攻略生成平台 MVP。核心方法论来自 PRD：先通过自动化采集构建"过饱和候选池"，再由用户与同行人选择，最终输出可执行型攻略。MVP 阶段聚焦"调研报告生成"这一阶段，暂不做正式行程编排。

约束条件：
- 部署在阿里云服务器，与现有 `umafans.run` Django 项目共存。
- 现有项目已占用 80/443 端口并使用 Nginx 反向代理。
- 数据库使用独立 PostgreSQL 容器，避免影响现有项目。
- LLM 使用硅基流动聚合 API（OpenAI 兼容格式）。
- 必须实现小红书自动采集，且采集额外成本控制在 100 元/月以内。
- 开发周期 2–4 周，技术栈由我们推荐。

## Goals / Non-Goals

**Goals:**
- 实现用户创建项目后立即触发多源自动采集。
- 生成结构化调研报告，包含核心体验、重要体验、美食、住宿、交通、预算、tips、参考路线。
- 支持公开链接轻量协作投票，无需注册。
- 支持网页查看与 Google Maps 点位导出。
- 提供 Docker Compose 一键部署方案，与现有服务器共存。

**Non-Goals:**
- 正式行程生成（每日执行表、Plan B、可砍项目等）。
- 内嵌交互式地图。
- 用户注册登录系统。
- 支付、预订、通知机制。
- 日历/Excel/Markdown/PDF 导出。
- 自动定时更新采集数据。

## Decisions

### Decision: Next.js 14+ App Router + FastAPI 分层架构
**Rationale:**
- Next.js 提供 SSR/SSG、PDF 导出库（如 Puppeteer）、React 组件生态，适合内容型报告页面。
- FastAPI 异步原生，适合调用外部 API、LLM、爬虫，且 Python 生态在数据处理和 AI 调用上更成熟。
- 前后端分离便于后续扩展小程序或其他客户端。

**Alternatives considered:**
- Django + Django Templates：与现有项目一致，但前端交互和 PDF 生成不如 Next.js 灵活。
- Next.js 全栈 API Routes：减少一个服务，但 Python 爬虫/LLM 生态无法直接使用。

### Decision: PostgreSQL + Redis + Celery 任务队列
**Rationale:**
- PostgreSQL 存储结构化项目、候选池、投票数据；JSONB 字段可灵活存储采集原始数据和报告章节。
- Redis 作为 Celery broker 和结果后端，支持异步采集任务、LLM 调用、PDF 生成。
- Celery Beat 可用于未来扩展定时任务，MVP 中仅用于任务分发。

**Alternatives considered:**
- SQLite：不适合多 worker 并发和部署。
- RabbitMQ：过重，Redis 已足够。

### Decision: 独立 PostgreSQL 容器而非共用现有数据库
**Rationale:**
- 完全隔离，不影响 `Umanewsbot` 项目。
- 独立备份、迁移、权限管理更简单。
- 不需要修改现有项目的 docker-compose 或数据库权限。

**Alternatives considered:**
- 共用现有 PostgreSQL：节省资源，但需要协调权限和网络，风险更高。

### Decision: 子域名 `travel.umafans.run` 部署
**Rationale:**
- 两个项目完全独立，静态文件路径、Cookie、路由不会冲突。
- 现有 Nginx 只需新增一个 server block，配置清晰。
- 未来迁移或独立域名都更容易。

**Alternatives considered:**
- 子路径 `umafans.run/travel/`：不需要额外域名，但前后端路由、静态文件、API 路径都需要加前缀，容易踩坑。

### Decision: 小红书采集走第三方服务/工具 + 自建低成本爬虫兜底
**Rationale:**
- 100 元/月预算不足以支撑高质量代理池和账号池的完全自建方案。
- 第三方服务（如公开的小红书数据 API、RPA 工具）可以更快稳定获取数据。
- 自建方案作为 fallback，在第三方服务失败时尝试低频抓取。

**Alternatives considered:**
- 纯自建 Playwright/Selenium + 代理池：可控但成本高、维护重，超出预算。
- 放弃小红书自动采集：用户明确不接受。

### Decision: 采集流程采用"泛搜索 → 详细采集"两步
**Rationale:**
- 先生成目的地候选列表，再对每个候选点详细采集，避免一开始就无目标地全量抓取。
- 便于控制数据量和请求次数，符合低成本和低风险原则。

**Alternatives considered:**
- 直接按关键词全量搜索抓取：数据噪声大，成本高。

### Decision: 报告数据使用 JSONB 半结构化存储 + 关系表混合
**Rationale:**
- 报告章节结构灵活，JSONB 适合存储完整的报告内容。
- 候选池、投票、项目等需要查询和索引，使用关系表更合适。

**Alternatives considered:**
- 完全关系表：报告结构频繁变化时迁移成本高。
- 完全文档数据库：增加部署复杂度。

### Decision: 报告分享使用网页链接，MVP 不做 PDF 导出
**Rationale:**
- 用户决定 MVP 阶段不实现 PDF 导出，直接通过网页链接分享调研报告。
- 避免了 Puppeteer/Chromium 带来的 Docker 镜像膨胀、内存占用和服务器资源压力。
- 未来需要 PDF 时，可以重新评估前端生成（如 React-PDF）或后端渲染方案。

**Alternatives considered:**
- Puppeteer 渲染 Next.js 页面：实现简单但资源开销大。
- 前端 React-PDF 生成：不需要后端 Chromium，但页面布局能力有限。

### Decision: 投票使用浏览器 session cookie，无需注册
**Rationale:**
- 符合"轻量协作"要求，降低使用门槛。
- 同一浏览器会话内防止重复投票，换浏览器可再次投票，在朋友小范围内可接受。

**Alternatives considered:**
- 邮箱/微信验证：增加使用成本，不符合轻量协作。

## Risks / Trade-offs

| Risk | Level | Mitigation |
|------|-------|------------|
| 小红书采集不稳定或被封号 | 高 | 设计降级但不允许缺失，实际采用第三方服务 + 自建 fallback；记录来源缺失并在 UI 中提示；必要时你提供账号/登录态 |
| 2–4 周内无法完成所有功能 | 高 | MVP 明确砍掉行程生成、内嵌地图、注册登录；优先保证报告生成 + PDF + 投票 + 部署 |
| LLM 输出不可控导致报告质量差 | 中 | 使用结构化输出（JSON mode）；分阶段调用 LLM（采集清洗 → 摘要 → 分类 → 报告生成）；人工校验首批报告 |
| 第三方服务（地图 API、小红书采集）成本超预算 | 中 | 优先使用免费额度；监控首月用量；必要时限制请求频率或缩小采集范围 |
| 服务器资源不足（内存/磁盘） | 中 | 独立 PostgreSQL + Celery worker 按需启动；首部署时监控资源使用 |
| 图片版权和存储 | 中 | 核心图片下载保存并记录来源，其他图片使用外部 URL；免责声明提示 |
| 现有 Nginx 配置冲突 | 中 | 使用子域名完全隔离；部署前备份现有 Nginx 配置 |
| 数据隐私（公开链接） | 低 | 链接即公开，符合用户选择；share token 使用 UUID 增加不可猜测性 |

## Migration Plan

1. **开发阶段**：在本地使用 Docker Compose 完整运行前后端、数据库、Redis、Celery。
2. **测试阶段**：将代码 push 到 GitHub，在服务器上 clone 到独立目录，使用 Docker Compose 启动新栈。
3. **域名与 Nginx**：添加 `travel.umafans.run` 的 DNS A 记录指向服务器；在现有 Nginx 中新增 server block 反向代理到新后端端口（如 8001）。
4. **上线**：确认新服务健康后，对外开放子域名；保持现有 `umafans.run` 服务不受影响。
5. **回滚**：如遇到问题，停止新 Docker Compose 栈并移除 Nginx server block 即可，不影响现有项目。

## Open Questions

1. 小红书第三方采集服务的具体选型需要在开发早期调研（1–2 天内确定可用性和成本）。
2. 是否愿意为 Google Maps Places API 申请并绑定信用卡？虽然免费额度通常够用，但生产部署需要 API Key。
3. 服务器剩余内存和 CPU 需要确认，以决定 Celery worker 数量和并发度。
4. 首批 MVP 验证目的地建议选择 1–2 个（如日本关西、新西兰南岛），以便集中测试采集逻辑。
5. 是否需要项目创建者拥有"删除整个项目"的权限控制？当前设计默认公开链接，任何人可查看。
