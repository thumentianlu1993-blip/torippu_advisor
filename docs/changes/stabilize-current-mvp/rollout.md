# 现有 MVP 可信化发布方案

## 1. 当前状态

- 状态：**未发布 / 历史发布授权因本次文档指纹变化待重新确认**
- 当前阶段：原 code reviewer `/root/stabilize_mvp_code_review` 已最终 `APPROVE`，覆盖完整工作树指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013`；后续文档证据、Markdown whitespace 与本次 frontend CI Chromium 安装修复产生新指纹，待原 reviewer 复审、远端复跑与用户重新授权，R4.3 仍不得执行
- 最新成功代码审核：2026-08-08 原 reviewer `/root/stabilize_mvp_code_review` 最终 `REVIEW APPROVE`，10 P1、2 P2 与 P1-10 manifest 直接回归全部关闭
- 用户发布授权：用户于 2026-08-08 本轮明确说“发布吧”，对应当时受审指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013`；本次文档修正改变指纹，按规则必须对新指纹重新确认
- 线上事实：2026-08-08 公共 DNS 查询为 NXDOMAIN，HTTPS 不可达；服务器、数据库和部署内部状态 unknown

## 2. 发布前硬门禁

必须同时满足：

1. `test_cases.md` 的本地/CI 门禁全部通过，未覆盖风险已披露。
2. 独立代码 reviewer 对待发布精确 diff 给出成功结论，记录 reviewer、范围和版本指纹。
3. 只读预检确认生产 revision、数据、磁盘、备份可恢复性、Redis/Celery、代理、DNS 权限和 secret 配置；不可用项写 unknown 并停止。
4. 用户针对同一受审内容明确说“上线”“发布吧”或同义授权。
5. 授权后内容未发生任何变化；若变化则回原 reviewer 复审并重新取得授权。

## 3. 受审版本记录

- Code reviewer：未参与实现的独立 code reviewer
- Reviewer 会话标识：`/root/stabilize_mvp_code_review`
- 审核范围：`stabilize-current-mvp` 完整工作树、迁移、CI、bridge、前后端和测试
- 完整工作树 SHA-256：`98196cea6f24ca10be9832ffa68203e29e78b88519da97e7fd5eaefdde0bb5e3`
- 指纹算法：`travel-worktree-v1`。取 `git ls-tree -r --name-only -z HEAD` 的 HEAD tracked 路径、`git ls-files -z` 的当前 index tracked 路径与 `git ls-files --others --exclude-standard -z` 的全部未忽略 untracked 路径之并集，确保已 staged 删除路径仍以 `DELETED` 纳入；按路径原始字节以 `LC_ALL=C` 排序。SHA-256 输入以 `travel-worktree-v1\0` 开始；每项追加 `TYPE\0DECIMAL_PATH_LENGTH\0PATH\0DECIMAL_CONTENT_LENGTH\0CONTENT\0`。普通文件为 `TYPE=FILE`、`CONTENT` 为完整文件字节；符号链接为 `TYPE=SYMLINK`、`CONTENT` 为链接目标字节；tracked 但不存在的路径为 `TYPE=DELETED`、`CONTENT=DELETED`。为消除指纹写入自身造成的循环，计算前仅将 `tasks.md` 与 `rollout.md` 中“完整工作树 SHA-256”字段的值规范化为字面量 `<WORKTREE_SHA256>`；其余内容不变。
- 审核结论与时间：2026-08-08 首审 BLOCKED；同一原 reviewer `/root/stabilize_mvp_code_review` 后续完成全部复审并最终 `REVIEW APPROVE`，10 P1、2 P2 及随后发现的 P1-10 manifest 直接回归均已关闭；批准覆盖指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013`。
- P1-10 修复证据：`check-bridge-compatibility.sh` 的固定覆盖为 digest-pinned `Dockerfile.bridge`、完整 `requirements.bridge.txt` lockfile、`backend/app/**/*.py` 与 `backend/alembic/**/*.py`。P1-9 修改了覆盖内 expand migration，但 manifest 仍为旧值 `2ebb5e1ddb1cd75829597afcebe762379fa9bd292b6b0423cd340808d428e327`；现更新为 `fdc9c41945ba38df0ab43701b4a1c4cc864649ee16cdc9bb0b448f321e01938b`。兼容检查通过，本地 bridge image ID 为 `sha256:efd8b58acf0ddce6db16bed1e35329e677ab04813c55d3c155c4c25d9ddddef8`；同一只读 bridge 在 1c 与 expand schema 上的真实 Next.js Chromium matrix 各 `1 passed`，只使用一次性本地 PostgreSQL/bridge，未配置或调用 provider。
- P1-9 关闭证据：Compose app profile 启动真实 Next.js、FastAPI、PostgreSQL、Redis、本地 mock provider 与 HTTPS gateway；Playwright 未 mock `/api/**`，Chromium 与移动视口真实完成创建、active recovery、手工候选、投票、显隐、轮换、删除与 deleted recovery，并验证真实 Cookie 属性、Origin 拒绝和持久化；Compose smoke/health、内部网络、`DENY_EXTERNAL_NETWORK=1` 与失败日志脱敏均通过。
- 暂存格式门禁：2026-08-08 `git diff --cached --check` 对已 staged 旧快照报告 3 处 untracked Markdown whitespace：`.agents/skills/grill-me-codex/SKILL.md` EOF 多余空行，以及 `docs/changes/stabilize-current-mvp/spec.md` 第 3、4 行行尾空格。工作树已严格只修这 3 处格式，不改语义、产品、测试或配置；按要求未执行 `git add`，因此 index/cached 旧快照仍保留原问题属预期，发布前必须以新指纹复审并重新暂存。
- 非阻塞风险：远端 GitHub Actions run `31243236261` 的 frontend job `93067494916` 因 Chromium 可执行文件缺失失败；focused workflow 修复尚未远端复跑，结果 unknown；公共 DNS/TLS 仍不可用，生产主机内部状态 unknown；真实第三方 provider 未调用，其线上质量与可用性 unknown。

### 首审 finding 修复映射（含 P1-10，均已关闭）

1. 路径 secret：应用仅记录路由模板，禁用 Uvicorn/httpx URL 日志，Compose/Docker 加 `--no-access-log`，Nginx `access_log off`；捕获日志动态测试无 token。
2. 恢复：active 与 30 天 deleted 两种恢复均可重新签发创建者 Cookie；非创建者页面显示 `creator_recovery_required` 恢复入口，真实 Playwright 覆盖。
3. provider：reservation 增加 owner/CAS/结果缓存；重复 delivery 复用结果不重发，project row 锁跨 send，删除已提交时 send=0。
4. LLM：review/report 外呼统一经过 budget transport；`DENY_EXTERNAL_NETWORK` 保持底层 fail-closed，report 以删除与 candidate version fence 停止旧任务。
5. 报告版本：实际 candidate/source/lifecycle 变化每轮只递增一次；report outbox 版本键冲突 no-op；report 使用字段 override 的 effective projection；连续相同两轮与 override 测试覆盖。
6. lease：Celery `acks_late`/`reject_on_worker_lost`，beat CAS 扫描过期 lease、清 owner、按 attempt 唯一重排；恢复/再次领取动态测试覆盖。
7. 最终 fence：候选持久化阶段不再中途 commit，最终 project/run `FOR UPDATE + populate_existing` 校验 owner/fence/deleted；删除竞态回滚候选与 report intent。
8. merge：survivor 固定为 manual、引用量、最早创建、ID 顺序；双 override 与 vote 值/版本/时间写不可变审计，注入失败完整 rollback。
9. CI/E2E：CI 的 app profile 实际启动 backend/frontend/PostgreSQL/Redis/mock-provider 与本地 HTTPS gateway；Playwright 不 mock `/api/**`，通过真实 UI/API/DB/Redis 执行创建、active 恢复、手工候选、投票、显隐、轮换、删除和 deleted 恢复，并从浏览器 cookie jar 断言真实安全属性、合法/非法 Origin 与 reload 后持久化。Compose smoke 等待真实 health、验证无外部 reservation；核心网络 internal，provider 仅本地 mock，失败日志脱敏。
10. bridge：补 project/status/report/SSE/candidates/creator-check/export 只读 surface；旧/expand schema 运行前端 bootstrap 同构请求；固定 Python base digest、bridge 依赖版本和完整 app/alembic build-context manifest，并输出 image digest。
11. P2 migration：移除 `Base.metadata.create_all`，改为显式 Alembic table/index/FK/unique/default/nullability 操作。
12. P2 XFF：从右剥离可信代理，忽略左侧 spoof，非法链稳定返回 `invalid_forwarded_chain` 并动态测试。

## 4. 发布前只读预检证据（2026-08-08）

- Git 一致性：本地 `HEAD`、本地 `origin/main` 与 `git ls-remote` 的远端 `main` 均为 `1b8f18c665ac82ac6b4e5d891b1942324aa3b88d`；本项目受审工作树改动尚未 commit，因此该远端 SHA 不包含当前实现。
- GitHub Actions：`gh` 已认证。远端 run `31243236261`（commit `68e312787f4c476e3796f38e86d89ab3cf5d1b94`）中 frontend 的 Vitest、typecheck 与 production build 通过，但 job `93067494916` 的 bridge frontend matrix 因未安装 Playwright Chromium 可执行文件而失败；full-stack-e2e 因先执行同一显式安装命令而通过。当前仅在 frontend job 增加锁文件对应的 `npx playwright install --with-deps chromium`，尚未 commit/push 或远端复跑，修复结果 unknown，不能以本地门禁替代远端结果。
- DNS/TLS/HTTP：公共 resolver `1.1.1.1` 与 `8.8.8.8` 查询 `travel.umafans.run` 均返回 NXDOMAIN，因此 TLS 与 HTTP 均不可验证。代理环境返回的 `198.18.1.24` 属代理路径结果，不能作为生产服务器、DNS 目标或可达性证据。
- 生产基础设施：仓库部署材料只有通用 `/opt/travel-planner` 路径，没有可验证的生产 host。生产数据库 revision/数据状态、可用 backup restore point、Redis/Celery 状态全部 unknown；在用户提供或确认目标并完成只读核查前停止发布。
- 本地配置：根 `.env` 存在，核心数据库、Redis 与 `NEXT_PUBLIC_API_URL` 键均非空；未读取或记录 secret 值。`CORS_ORIGINS`、`TRUSTED_PROXY_CIDRS`、`RATE_LIMIT_REDIS_URL` 缺失，不能据此推断生产配置完整。
- Compose：development 与 production Compose 语法均 valid，但检查出现 trusted proxy 配置缺失 warning；该 warning 与上述缺失键必须在生产目标确定后核对，当前不修改配置值。
- Bridge：固定 manifest `fdc9c41945ba38df0ab43701b4a1c4cc864649ee16cdc9bb0b448f321e01938b` 校验通过。
- 结论：R4.1 只读预检完成，但生产 host、DNS 管理目标、数据库/备份/Redis/Celery、生产安全配置不足，且 focused CI 修复尚无远端复跑证据，发布仍被阻塞。用户随后曾针对指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013` 明确说“发布吧”；当前 workflow 与证据内容产生新指纹，R4.2 必须先取得原 reviewer 对新指纹的确认、远端 CI 通过证据并由用户重新授权，同时仍需提供或确认生产 host 与 DNS 管理目标。R4.3 未执行。

## 5. 发布授权证据

- 授权人：用户
- 精确表述：“发布吧”
- 对应受审指纹：`1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013`
- 时间：2026-08-08，本轮对话
- 当前效力：该授权对应上述旧指纹；本次只修正文档证据但已产生新完整工作树指纹，依项目规则旧授权失效，等待用户针对新指纹重新确认。此记录不授权 R4.3，也不表示 commit、push、迁移或部署已执行。

## 6. 建议发布顺序

以下只是方案，不构成执行授权：

1. 固定待发布 commit/image SHA；开启变更窗口，暂停创建/重采集写流量。
2. 生成数据库快照并验证可列出/读取；记录当前 Alembic revision、关键表计数和抽样校验和。
3. 运行迁移 preflight dry-run。重复 token、重复 vote、未知 revision、空间不足或锁风险任一出现即停止。
4. 执行 expand migration；校验新表、索引、hash backfill、计数和孤儿为零。
5. 先部署并验证受审 bridge 镜像，再部署安全版本 backend/worker/frontend；旧项目标为 legacy_unclaimed，不开放旧 creator 自动兑换；启动 outbox dispatcher 和 purge/recovery 定时任务。
6. 内部 smoke：health、旧/新分享链接、legacy_unclaimed fail-closed、Cookie path/180-day expiry、Origin、创建、重采集复用、删除 fence、mock/缓存降级；禁止无授权真实 provider 调用。
7. 恢复写流量，观察错误率、队列、活动 run、预算拒绝、legacy_unclaimed 计数和数据库锁。
8. 配置/恢复 `travel.umafans.run` DNS，验证证书、反向代理、Secure Cookie 和 CORS/Origin。
9. 执行公开 smoke；若通过，记录证据并进入兼容观察期。
10. 兼容观察期结束且 legacy_unclaimed 已按披露策略处理后，另行执行 contract migration；其 diff 必须属于已审核内容，否则重新审核和授权。

## 7. 发布后验证

- DNS A/AAAA/CNAME 能从至少两个公共 resolver 解析到预期目标。
- TLS 证书链、主机名和有效期正确；HTTP 强制 HTTPS。
- `/healthz` 为 ok 且响应不泄露数据库/Redis异常。
- 新建一个合成 smoke 项目：响应无 creator secret，Cookie 属性正确，恢复密钥只展示一次。
- 无分享令牌、旧分享令牌、数字 ID 路由均不能读取；当前分享链接可读。
- 投票 Cookie upsert、默认隐藏、公开/再隐藏和 public/private export 正确。
- 创建者手工候选、字段恢复、分享轮换、重采集复用与降级提示正确。
- 队列无异常增长，活动 run 唯一，预算账本不超限，日志无 secret/query/IP 原文。
- 合成项目在验证后按产品删除流程处理；不直接绕过审计清表。

## 8. 监控与停止条件

任一条件触发停止继续发布：

- 迁移 revision/计数/约束与预期不符，或锁等待超过预设窗口。
- 5xx、认证失败或 Cookie 失败持续超阈值。
- 同项目出现多个活动 run、重复外部 reservation 或预算超限。
- 候选数量异常增长、错误自动合并或人工覆盖丢失。
- secret、原始 query、IP、provider payload 或数据库异常出现在公开响应/日志。
- DNS/TLS 目标不明确或健康只部分可验证。

## 9. 回滚

- 安全版本错误但 expand schema 兼容：只回滚到本次受审的固定 bridge 镜像；bridge 可按 hash 只读新模型项目并关闭创建者/采集写功能。当前旧镜像不兼容新写入，严禁作为 expand 后回滚目标；保持 expand 列/表且不要仓促 downgrade 数据。
- 迁移中失败：停止应用写入，保留错误证据；只在已验证备份与明确步骤下恢复。禁止猜测性重跑。
- 错误合并/数据损坏：暂停采集与 merge，使用 merge audit/备份恢复受影响项目；不得批量自动拆分。
- 预算/并发故障：禁用外部派发和重采集，保留读取与手工数据。
- DNS/TLS 故障：撤回新记录或恢复上一已知目标；若没有已知健康目标，保持不可达并报告 unknown，不能指向猜测主机。

回滚后任何修复都改变受审内容，必须回原代码 reviewer 复审并重新取得发布授权。

## 10. 实际发布结果

- 执行人/时间：未执行
- 发布 SHA：无
- 迁移前后 revision：未知 / 未执行
- DNS/TLS：未执行
- Smoke：未执行
- 最终状态：未发布
