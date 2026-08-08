# 现有 MVP 可信化设计

状态：方案审核通过；本地实现待独立代码审核

## 1. 当前状态与约束

- 前端为 Next.js 14 App Router；后端为 FastAPI + SQLAlchemy async + PostgreSQL；异步任务为 Celery + Redis。
- `Project.id`、`Candidate.id` 当前直接出现在浏览器 API；`creator_token` 经 URL/query 和 `X-Creator-Token` header 流转。
- `Project.token` 目前同时承担分享定位和读取授权，原文存库；候选、投票和 SSE 仍有数字 ID 旁路。
- 采集每轮直接创建候选，缺少稳定来源记录、预算账本、活动 run 唯一性和派发恢复机制。
- 现有 `b1270b2f0ef9` 在非空旧库直接新增 `NOT NULL creator_token`，必须修复迁移路径。
- 当前没有 GitHub Actions、前端测试或浏览器 E2E；线上域名当前不可解析，主机状态未知。

## 2. 总体方案

保留现有技术栈，按六个边界拆分：

1. **访问边界**：分享令牌定位项目，创建者/投票者使用服务端 Cookie，所有项目资源在分享令牌下嵌套。
2. **执行边界**：数据库负责活动 run 唯一性、派发 outbox、租约和幂等；Celery 只执行已持久化的 run。
3. **成本边界**：所有 provider 调用必须通过统一预算网关，在发请求前原子预留。
4. **身份边界**：`Candidate` 是 canonical 实体，`CandidateSource` 保存 provider 身份与生命周期，二者不再混用。
5. **人工边界**：系统值与人工覆盖分离，所有人工变更、恢复和合并均审计。
6. **证据边界**：CI 和 E2E 使用本地服务与 provider mock；生产完成另经授权、迁移和在线 smoke。

## 3. 访问与凭证设计

### 3.1 数据表示

在 `Project` 增加：

- `share_token_hash`、`share_token_version`
- `creator_credential_hash`、`creator_credential_version`、`creator_credential_expires_at`
- `recovery_key_hash`
- `deleted_at`、`purge_after`

令牌均由 CSPRNG 生成，至少 128 bit；服务端以 SHA-256/HMAC 派生值做等时比较，只记录短指纹用于审计。原文只在生成当次返回或写入 Cookie。

### 3.2 路由

对外 API 统一为 `/api/projects/by-token/{share_token}/...`：project、status、report、report/stream、candidates、votes、export、creator session、recollect、share rotation、delete/recover、audit 和 merge proposals。删除现有 `/api/projects/{project_id}/...` 及全局 `/api/candidates/{candidate_id}/votes` 浏览器路由。

候选可继续使用内部整数 ID 作为嵌套资源标识，但每次查询必须同时包含 `candidate.project_id == resolved_project.id`，杜绝跨项目引用。公开 project/status/report/SSE/export/error schema 不含 `Project.id/project_id`；外部项目标识只有调用者已持有的 share token。候选 ID 不得被前端反向用来推导或调用项目 ID 路由。

### 3.3 Cookie

- 创建者 Cookie：随机原文，`HttpOnly; Secure; SameSite=Lax; Path=/api/projects/by-token/{share_token}`。分享令牌轮换时重新签发相同权限的新 path Cookie并清除旧 path Cookie。
- 投票者 Cookie：每项目随机原文，同样限定 token API path；数据库只保存项目域内派生 hash，避免跨项目关联。
- API fetch 使用 credentials；SSE 改用 token 路径，因此 EventSource 自动携带同站 Cookie。Cookie 设置 `Max-Age=15552000` 且服务端使用同一绝对过期时间，二者不因访问续期。
- CORS 仅允许显式来源且 credentials 开启；生产要求前后端同站 HTTPS。CSRF 通过 SameSite、严格 Origin 校验和非简单 JSON 写请求共同防护。

### 3.4 恢复与旧项目认领

创建接口在同一事务生成 share/creator/recovery secrets，提交后设置创建者 Cookie，响应正文只含分享令牌和一次性恢复密钥。创建者凭证与 Cookie 固定 180 天有效、不可滑动续期；过期后管理 API 返回稳定 `creator_recovery_required`。恢复端点接受恢复密钥并做速率限制；成功后轮换创建者凭证、重新开始 180 天有效期并记录审计。

旧前端曾把 `creator_token` 放入分享给同行者的 URL，因此持有该值不构成独立所有权证明。迁移把没有 recovery hash 的旧项目标为 `legacy_unclaimed`，保留分享读取，但拒绝分享轮换、删除、重采集、候选编辑等创建者写操作。URL 中的旧 query 在客户端立即清除，服务端永不提供自动兑换端点。人工认领必须在产品外由受控运维流程验证分享链接之外的独立证据，逐项目签发恢复密钥并审计；无法证明者只能新建项目。预检必须统计 `legacy_unclaimed` 数量并在发布前披露。

### 3.5 Origin 与 CSRF 合同

所有浏览器写请求（创建、恢复、投票及全部创建者 mutation）必须携带与配置 allowlist 完全匹配的 `Origin`；缺失、`null`、生产环境非 HTTPS、伪造或未允许 Origin 均拒绝。预检 OPTIONS 只允许显式来源。服务端同时要求 `Content-Type: application/json`（若未来新增文件接口须另定义防护 token），Cookie 使用 `SameSite=Lax`，三者共同防护 CSRF。只读 GET/SSE 不改变状态，但仍不放宽 CORS credentials。

## 4. 限流、幂等与任务派发

### 4.1 客户端地址

中间件只在直接 peer 属于 `TRUSTED_PROXY_CIDRS` 时解析标准转发头，否则使用 socket peer。IPv6 归一为 `/64`。日志只保留 keyed hash，不保存公开页面可关联的完整 IP。

### 4.2 限流

Redis Lua 脚本实现原子滚动窗口：创建 3/hour + 10/day；重采集 1/hour + 6/day；投票 60/10min + 300/day（项目+IP）及 10/day（项目+投票者+候选）。创建检查先于数据库写；投票 upsert 与数据库审计唯一约束兜底。Redis 不可用时，创建、重采集和投票 fail closed 为脱敏 503，避免绕过成本/滥用边界。

### 4.3 活动 run 与派发

- 数据库为每项目 `pending/running/generating` 建立部分唯一索引。
- 创建/重采集事务锁定 Project 行，先查询活动 run；存在则返回，不增加预算计数。
- 新 run 与 `TaskOutbox` 在同一事务提交。dispatcher 以 `FOR UPDATE SKIP LOCKED` 领取 outbox，成功发送后标记；失败指数退避，避免“数据库已提交但任务未发送”。
- worker 以 run ID 做 compare-and-set 领取，维护 `lease_expires_at/heartbeat_at/attempt_count`；重复 delivery 对已完成/仍持有效租约的 run 为 no-op。过期租约只能由恢复任务接管，同一预算 reservation 不重复计费。
- 分享轮换时递增 token version；SSE 在每次事件/heartbeat 前重验 token version 与 `deleted_at`，失效即发送通用 revoked 事件并关闭。删除事务把活动 run 标为 cancelled、取消未派发 outbox 并递增 execution fence version；worker 在每个阶段写入前、预算网关在每次外呼预留前重验 fence，已删除/已取消即停止且不得再产生费用或业务写入。

## 5. 外部调用预算

增加 `ExternalCallReservation`，字段含 project、run、provider、幂等键、request_units、estimated_cost_usd、状态和时间。统一 `BudgetedProviderClient` 在网络请求前执行单事务：锁定项目预算聚合行，检查并预留批次/生命周期/provider/成本上限，再允许调用。

每个逻辑调用使用稳定幂等键 `run + provider + operation + normalized_request_hash`。重试复用 reservation；只有新逻辑调用增加 request unit。调用成功/失败都会结算状态，失败不返还已消耗的外部请求额度，因为 provider 可能已计费。缓存命中不创建外部 reservation。

预算拒绝抛出领域结果而非通用异常，run 转 `partial_budget_exhausted`，保留已有候选并继续仅缓存/手工路径。前端把内部 provider 状态映射成用户可理解覆盖类别。

## 6. 候选身份、生命周期与合并

### 6.1 模型

- `Candidate`：canonical 候选、活动状态、系统/人工有效展示、manual UUID 与乐观版本。
- `CandidateSource`：candidate FK、identity_provider、entity_type、external_id、canonical_url、fallback_fingerprint、identity_state、collector_vendor/version、原始证据、first/last_seen、consecutive_absences、absence_window_started_at、active。
- `SourceObservation`：provider run 是否完整/成功/预算截断及 source seen/not_seen 证据。
- `MergeProposal`：候选对、score、reasons、状态、创建者决定和 supersession key。
- `CandidateMergeAudit`/`VoteMergeConflictAudit`：survivor、loser、映射和只读冲突证据。
- `CandidateFieldOverride`：字段名、typed JSON value、版本；允许字段为 `name/category/area/source_url/notes/tier/summary`。自动候选的 provider/系统值保持不变，effective value 为非空 override 优先；清空 override 恢复 system value。`notes` 为 manual-only，无 system value。纯手工候选的初始值属于 manual base，后续编辑仍进入版本化 override。
- `CandidateFieldChange`：上述每个可编辑字段的旧/新 effective value、override 动作、restored_from、版本和时间；由于无账号，只记录 actor_role=creator 和凭证版本，不记录密钥。

来源唯一约束优先 `(project_id, identity_provider, entity_type, external_id)`（external ID 非空）；fallback 唯一约束使用 `(project_id, identity_provider, entity_type, fallback_fingerprint)`。pure manual 以 UUID 唯一。

### 6.2 匹配算法

1. 同 provider/type/external ID 精确匹配。
2. 同 provider canonical URL，或确定性 fallback fingerprint。
3. 跨 provider 计算可解释 score；电话/官方域名强信号，或 `<=50m`、高名称相似、类型兼容、无地区冲突的组合。
4. `>=0.98` 自动关联，`0.85–0.98` 建建议，低于阈值分开。已有投票/覆盖的候选只允许步骤 1 自动处理。

匹配代码使用规范化库函数和固定 fixtures；不得调用 LLM 决定身份。

### 6.3 生命周期

provider run 结束时只对“完整 + 成功 + 非预算截断”的 provider 结算 absence。seen 重置连续缺失；not_seen 在事务内递增。达到 3 次且第一次与当前 qualifying absence 相距至少 7 天才令 source inactive。canonical 是否 inactive 根据全部 source 与 manual origin 重新计算，不删除历史。

### 6.4 合并

合并锁定两个候选及其 votes/sources。survivor 选择遵循：手工保护、已有引用量、最早创建时间、ID 最小的稳定次序。来源、图片、审计和提案迁移；字段保留人工覆盖优先。相同 voter hash 的投票取 `updated_at` 最新者，loser 证据写冲突审计。事务末重算聚合，失败整体回滚。“保持分开”记录稳定候选对 key，除身份关键证据变化外不再建议。

## 7. API 与前端行为

- 公共候选响应始终带当前投票者 `user_vote`；只有 `votes_revealed=true` 时带 aggregates。
- 创建者响应可带 aggregates、预算详情、来源状态、审计和建议；所有错误经过公开错误码映射。
- 手工候选表单字段严格限定为 spec 的轻量集合；系统字段只读，人工覆盖可清空。
- 字段历史按候选分页，恢复单字段需携带目标 audit ID，并以乐观版本防止覆盖新的编辑。
- 合并建议为轻量队列，只展示名称、类型、区域、距离、来源 URL/identity 和解释性证据。
- public export 遵循投票隐藏；creator export 带匿名 aggregates 和 `votes_revealed` 标志。两者都不含 voter hash、内部 ID、原始 provider payload 和秘密。
- 页面展示 `complete/partial/stale`、最后成功时间和缺失类别；创建者面板增加预算和建议动作。
- Project 维护 `candidate_data_version`，Report 记录 `generated_from_version`。候选编辑、来源状态变化、合并或字段恢复在事务内递增版本，使旧报告标为 stale；页面不得把 stale 报告表述为最新，后台以该版本作为幂等键重新生成。loser 候选不会继续留在新报告中。

## 8. 迁移方案

1. **迁移预检（只读）**：确认当前 revision、表/行数、重复票、NULL/重复 token、数据库版本和可用空间；任何异常停止，不猜测。
2. **修复历史迁移**：把 `b1270b2f0ef9` 改为：先对旧 votes 按 `(candidate_id, session_id)` 确定性保留 `updated_at` 最新、再以 ID 打破平局并把 loser 写入迁移审计；校验汇总后才建唯一约束。`creator_token` 使用 nullable add → 为既有行生成唯一值 → 建索引 → 设 NOT NULL。这样从 `1c4...` 的非空库与空库都可升级；已执行过该 revision 的库不受文件变化影响。
3. **expand migration**：新增 hash/生命周期/预算/来源/审计/outbox 表和 nullable 新列；从现有 token 计算 share hash。旧 `session_id` 通过 keyed HMAC(`project_id`, `session_id`) 回填为项目域内 voter hash，保持每候选最新票与汇总；完成计数/重复/NULL 校验后才能在 contract 阶段删除原文。旧 creator 只用于把项目标为 `legacy_unclaimed`，不能兑换新权限。已在 `b127` 的库也运行相同 voter backfill 与校验。
4. **兼容部署**：先发布本次变更内、同样经过测试和审核的 bridge 版本。bridge 能读取 expand schema 与 hash 分享链接，但对新模型项目只读并关闭创建者/采集写功能；它是后续安全版本的唯一应用回滚目标，不是当前旧镜像。安全版本新写只走新模型，旧候选通过显式 backfill 命令分批生成 source/provisional 状态与 dry-run proposal。
5. **验证窗口**：核对计数、孤儿、唯一约束、活动 run、预算账本、legacy_unclaimed 和旧分享链接。旧 creator 原文不得用于授权。
6. **contract migration**：在发布验证和兼容观察期结束后，删除原始 creator_token/session_id、禁止旧写路径；是否删除原始 share token 列以实际兼容数据为准，但运行时不得按原文查询或记录。

阶段兼容矩阵：当前旧镜像只适用于迁移前 schema；bridge 可读迁移前/expand 数据但不允许安全模型写入；安全版本读写 expand 数据；contract 后只允许安全版本。每个阶段只能回到表中声明兼容的固定 SHA，禁止把当前旧镜像用于 expand 后回滚。

生产每一步均需备份/恢复点、固定镜像 SHA 和单独明确发布授权。迁移脚本支持 dry-run 统计与有界批次，禁止自动合并跨 provider 旧数据。

## 9. 测试与 CI 设计

- 后端：pytest + PostgreSQL + Redis，覆盖权限、Cookie、限流、预算并发、run/outbox/lease、身份/生命周期/合并、审计、迁移和健康检查。
- 前端：TypeScript、production build，增加 Vitest/Testing Library 覆盖可见性和表单；Playwright 覆盖核心浏览器旅程。
- provider：依赖注入统一 HTTP transport，contract fixtures/mock server；测试环境设置 `DENY_EXTERNAL_NETWORK=1`。
- CI：GitHub Actions 分为 backend、frontend、migration、e2e jobs；缓存仅优化，不改变门禁。E2E 启动 Compose 测试 profile，等待脱敏 health 后执行。
- 本地命令以 `test_cases.md` 为准；先加入目标测试并记录真实 RED，再实现。

## 10. 可观测性、安全与隐私

- JSON 日志含 request_id、project 指纹、run ID、公开错误码和耗时；不含 token、Cookie、query、IP 原文、provider key、raw payload 或异常字符串。
- `/healthz` 仅返回 `ok/degraded` 和组件枚举；详细诊断只进脱敏内部日志。
- 对恢复、分享轮换、删除/恢复、手工编辑、合并决定记录安全/业务审计。
- 加密备份滚动保留 30 天；因此业务 purge 后，已删除内容最长可能再存在于不可在线访问的备份 30 天，到期自动过期。脱敏安全日志保留 90 天，仅含 keyed 项目指纹/事件，不含内容、token、Cookie 或 IP 原文。该语义在发布前写入用户披露。

## 11. 备选方案与取舍

- **JWT 代替服务端凭证**：撤销和单项目 path 隔离更复杂，拒绝。
- **仅 Redis 锁住采集**：Redis 故障或任务重投时不能证明唯一性，拒绝；数据库是真相，Redis只做限流。
- **直接覆盖 Candidate 字段**：无法保护人工编辑或解释来源，拒绝；拆 CandidateSource 与 override。
- **名字/城市模糊自动合并**：误合并不可接受，拒绝。
- **一次性重写旧数据并自动合并**：迁移爆炸半径过大，拒绝；expand/backfill/dry-run/contract 分阶段。
- **引入账号系统或完整治理台**：超出项目一，拒绝。

## 12. 风险与缓解

- 旧创建者无独立所有权证明：保持 legacy_unclaimed 只读，绝不凭曾被分享的旧 secret 提权；只有受控人工认领或新建项目。
- Cookie 跨域失败：生产前验证同站 HTTPS、代理 path、Origin 和 Set-Cookie；不以本地宽松配置替代。
- 并发预算超额：数据库行锁 + 唯一幂等键 + 请求前预留。
- 误合并：强阈值、人工保护、dry-run 和事务审计。
- 大表迁移锁：expand/contract、nullable-first、有界 backfill、锁超时和停止条件。
- CI 假绿：禁止外网、真实 PostgreSQL/Redis、迁移新库与浏览器 E2E。
- 线上未知：发布前重新只读核查 DNS、主机、revision、备份和配置；任何不可用项记 unknown。

## 13. 方案审核记录

- Reviewer 会话标识：`/root/stabilize_mvp_plan_review`
- 审核方式：当前环境没有独立的 Codex 原生方案审核命令，采用需求专属、只读 plan-review fallback；reviewer 未修改文件
- 首次审核范围：本目录五份 artifacts 与当前代码/迁移约束
- 首审结论：BLOCKED，不得进入 RED
- 首审 P0：旧 creator secret 曾随分享链接分发，不能自动兑换所有权
- 首审 P1：旧镜像不可作 expand 后回滚；b127 前重复票与 voter hash 迁移缺失；人工覆盖字段不完整；SSE/删除未 fence；Cookie TTL/Origin 合同缺失；公开响应仍可能含 project ID；迁移命令可能误操作非测试库
- 修复：引入 legacy_unclaimed fail-closed、受审 bridge 回滚矩阵、b127 前去重与项目域 voter hash、七字段 override、SSE/run/预算 fence、180 天凭证与严格 Origin、无 project ID 响应合同、disposable migration script；另落实具体备份/日志保留和报告版本失效
- 第一次复审：BLOCKED；关闭 6 个 P1 及 2 个 P2，保留 AC-02 的旧链接矛盾 P0，以及 bridge 缺实现/测试任务的 P1
- 第二轮修复：AC-02 明确旧链接不授予权限；新增 TC-34 和 T2.10/T2.11/T3.1，要求 bridge 被实现、固定 SHA、验证迁移前/expand 读兼容与全部新模型写 fail closed
- 第二次复审：APPROVE；上述两个 finding 均 CLOSED，未发现直接 P0/P1 回归。Reviewer 明确认可进入真实 RED；该结论不代表实现、代码审核或发布授权。
