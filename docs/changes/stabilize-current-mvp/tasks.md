# 现有 MVP 可信化任务

状态说明：`[ ]` 未开始，`[-]` 进行中，`[x]` 已完成，`[!]` 阻塞。不得跳过关口。

## 0. 方案关口

- [x] P0.1 完成本目录五份 artifacts。依赖：产品 Grill 决策冻结。映射：全部 AC。证据：本目录。
- [x] P0.2 建立需求专属方案 reviewer，会话标识写入 `design.md`。依赖：P0.1。证据：`/root/stabilize_mvp_plan_review` 首审 BLOCKED。
- [x] P0.3 修复 reviewer 阻塞 finding，并回原 reviewer 两次复审。依赖：P0.2。证据：同一会话最终全部 CLOSED。
- [x] P0.4 记录方案审核成功。依赖：P0.3。证据：`/root/stabilize_mvp_plan_review` 第二次复审 APPROVE。

## 1. 测试（先取得 RED）

- [x] T1.1 由测试 subagent 建立权限/Cookie/生命周期/限流测试，取得真实 RED。依赖：P0.4。映射：AC-01～04。证据：`test_cases.md`；合同测试 10 条目标失败包含数字路由、Cookie/Origin、生命周期、限流。
- [x] T1.2 建立 run/outbox/lease/预算并发合同测试，取得真实 RED。依赖：P0.4。映射：AC-04～05。证据：`task_outbox`、活动 run 唯一索引、reservation/transport 合同 4 条目标失败；动态并发断言留待 GREEN 补齐。
- [x] T1.3 建立候选 identity/lifecycle/merge/override/audit 合同测试，取得真实 RED。依赖：P0.4。映射：AC-06、AC-08。证据：相关模型、字段和 token-scoped route 6 条目标失败。
- [x] T1.4 建立投票可见性、公开/私有导出、健康脱敏测试，取得真实 RED。依赖：P0.4。映射：AC-07、AC-10。证据：投票/导出 3 条与 health 1 条目标失败。
- [x] T1.5 建立空库/旧库迁移与失败预检合同测试，取得真实 RED。依赖：P0.4。映射：AC-09。证据：nullable-first、disposable runner、bridge artifact 3 条目标失败；未对任何数据库执行迁移。
- [x] T1.6 建立前端 Vitest 与 Playwright 关键旅程合同，取得真实 RED。依赖：P0.4。映射：AC-02、07、08、10。证据：Vitest 3 failed；Playwright chromium/mobile-chromium 2 failed。
- [x] T1.7 将全部 RED 命令、目标失败摘要和环境健康证据写回 `test_cases.md`。依赖：T1.1～T1.6。证据：`test_cases.md` 第 4、6 节；91 tests collected，ruff/typecheck/diff check 通过。

## 2. 实现（仅由实现 subagent 执行 GREEN/REFACTOR）

- [x] T2.1 实现 token-hash、创建者/投票者 Cookie、恢复/轮换/删除状态及嵌套 API；移除数字项目旁路。依赖：T1.7。映射：AC-01～03。
- [x] T2.2 实现可信 IP、Redis 限流、Origin/错误脱敏。依赖：T1.7。映射：AC-04、AC-10。
- [x] T2.3 实现活动 run 唯一约束、outbox、租约、幂等领取与 stale 恢复。依赖：T1.7。映射：AC-04。
- [x] T2.4 实现统一 provider transport 与请求前预算 reservation；禁止测试外网。依赖：T2.3。映射：AC-05、AC-10。
- [x] T2.5 拆分 Candidate/Source/Observation，落实 identity、provisional、absence/inactive 和容量。依赖：T1.7。映射：AC-06。
- [x] T2.6 实现 merge proposal、事务合并、投票冲突与决定审计。依赖：T2.5。映射：AC-06、AC-08。
- [x] T2.7 实现系统值/人工覆盖、字段审计与单字段恢复。依赖：T2.5。映射：AC-08。
- [x] T2.8 实现轻量创建者 UI、重复审核、投票显示控制、降级面板和分层导出。依赖：T2.1、T2.5～T2.7。映射：AC-07～08。
- [x] T2.9 修复历史 migration，新增 expand/backfill/contract 迁移和 dry-run 命令。依赖：T2.1、T2.3、T2.5～T2.7。映射：AC-09。
- [x] T2.10 实现并固定受审 bridge artifact：兼容迁移前/expand 读取，对新模型关闭创建者/采集写入，并提供 schema/SHA 兼容检查；当前旧镜像不得作为 expand 回滚目标。依赖：T2.1、T2.9。映射：AC-09、AC-10。
- [x] T2.11 建立 GitHub Actions、Compose test profile、mock provider 和 smoke 脚本；同步 README/DEPLOYMENT/API_KEYS 配置事实，并在 CI 验证 bridge 兼容矩阵。依赖：T2.1～T2.10。映射：AC-10。
- [x] T2.12 GREEN/REFACTOR：使全部目标与回归测试通过，不扩大产品范围。依赖：T2.1～T2.11。映射：AC-01～10。

实现 subagent 禁止 commit、push、创建 PR、部署、写生产或调用真实付费 provider。每批返回修改文件、测试结果和风险。

## 3. 验证与代码审核

- [x] T3.1 运行 `test_cases.md` 全量本地门禁与 `git diff --check`，记录安全版本及固定 bridge artifact 的精确结果和 SHA。依赖：T2.12。映射：AC-01～10。证据：`test_cases.md` 第 7 节。
- [x] T3.2 核对 spec/design/tests/tasks/rollout 与代码一致，生成受审 diff 指纹。依赖：T3.1。证据：首次 code review 已覆盖完整工作树。
- [x] T3.3 建立未参与实现的需求专属代码 reviewer，执行 Codex 原生 `/review` 或等价只读 review。依赖：T3.2。证据：`/root/stabilize_mvp_code_review` 首审 BLOCKED，无 P0、10 P1、2 P2。
- [x] T3.4 由实现 subagent 修复 finding，回原 reviewer 复审；受审内容任何变化均使旧结论失效。依赖：T3.3。证据：原 reviewer `/root/stabilize_mvp_code_review` 最终 `REVIEW APPROVE`；10 P1、2 P2 与发布前预检发现的 P1-10 `bridge artifact hash drifted` 直接回归均已关闭。P1-10 manifest 由 `2ebb5e1ddb1cd75829597afcebe762379fa9bd292b6b0423cd340808d428e327` 更新为 `fdc9c41945ba38df0ab43701b4a1c4cc864649ee16cdc9bb0b448f321e01938b`，bridge compatibility 与 pre/expand frontend matrix 通过。
- [x] T3.5 记录最新代码审核成功、范围与受审版本。依赖：T3.4。原 reviewer 批准覆盖完整工作树指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013`；发布暂存门禁随后在已 staged 旧快照中发现 3 处 Markdown whitespace，工作树仅以 `apply_patch` 修复 `.agents/skills/grill-me-codex/SKILL.md` 的 EOF 空行及 `spec.md` 两处行尾空格，未执行 `git add`，因此 cached 旧快照预期仍报告原问题。当前完整工作树 SHA-256：`8dcd1a2a1e16de591acebe846e061c8e415ac71ac8d133c94faec9c1bdce1a58`。算法仍为 `travel-worktree-v1`，对 HEAD/index tracked 与未忽略 untracked 路径取并集并按字节序排序，文件纳入完整内容、tracked 缺失路径纳入 `DELETED`，计算前仅把 tasks/rollout 中本指纹字段规范化为字面量 `<WORKTREE_SHA256>`。

## 4. 发布关口（不属于当前授权）

- [x] R4.1 只读重查远端分支、生产主机、数据库 revision/数据、备份、DNS/TLS、配置与权限。依赖：T3.5。证据：2026-08-08 只读预检已完成并记录于 `rollout.md`；Git/DNS/本地配置与 bridge 可验证，生产 host、数据库、备份、Redis/Celery 均 unknown，存在发布阻塞，未执行任何写入。
- [!] R4.2 向用户报告受审内容、风险和精确发布/回滚步骤。依赖：R4.1。用户已于 2026-08-08 本轮针对指纹 `1fef63174df9577a0786086211d51aa7ef82744f3be2e4f6b70b3b63a7c7e013` 明确说“发布吧”；后续文档证据与 3 处纯 whitespace 修复均改变完整工作树指纹，按规则须先由原 reviewer 确认新指纹并由用户重新授权，同时仍待提供或确认生产 host 与 DNS 管理目标。不得据旧授权执行 R4.3。
- [ ] R4.3 获授权后才可 commit、push、PR/merge、迁移、部署、DNS 或生产写入；任何内容漂移须重审并重新授权。依赖：R4.2。
- [ ] R4.4 执行生产 smoke 并记录 AC-11 证据；失败按 `rollout.md` 停止/回滚。依赖：R4.3。

当前发布状态：未授权、未发布。
