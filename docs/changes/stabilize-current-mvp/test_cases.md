# 现有 MVP 可信化测试用例

状态：方案审核已通过；RED 已取得，本地 GREEN/REFACTOR 已完成，待独立代码审核

## 1. 测试原则

- 每条验收标准至少有一条自动化证据；安全、并发、预算和迁移必须覆盖失败/边界路径。
- RED 必须由缺失目标行为导致，不能由数据库未启动、依赖缺失或错误命令导致。
- provider 测试全部使用固定 fixture/mock，设置禁止外部网络；任何真实付费请求都使测试无效。
- 时间窗使用可控 clock，随机 secret 使用可注入生成器，不能依赖 sleep。

## 2. 验收映射

| ID | 映射 | 场景与预期 | 层级 |
| --- | --- | --- | --- |
| TC-01 | AC-01 | 数字 project/report/status/SSE/export/recollect 路由返回 404；无/旧/错误 share token 均无法读取；所有浏览器 project/status/report/SSE/export/error payload 均无内部 project ID | API |
| TC-02 | AC-01 | token A 下请求 project B 的 candidate/vote/edit 返回 404 且不泄露存在性 | API |
| TC-03 | AC-02 | 创建响应设置 path/Secure/HttpOnly/SameSite/180-day Cookie，URL/JSON/log/localStorage 无创建者 secret；恢复 key 只出现一次；180 天边界后要求恢复 | API/E2E |
| TC-04 | AC-02 | 旧 creator query 被清除但不能兑换权限；分享持有者并发尝试均无法接管；legacy_unclaimed 只读，受控人工认领才可签发恢复密钥 | API/E2E |
| TC-05 | AC-03 | 删除后公开/管理均 404；连接中的 SSE 立即关闭；活动 run/outbox 被取消且预算网关/worker fence；第 29 天恢复成功并轮换 share；第 31 天恢复失败且 purge 级联 | API/task |
| TC-06 | AC-04 | 同 IP 第 3/4 次每小时、第 10/11 次每日创建边界；拒绝请求无 Project/Run/Outbox 写入 | API |
| TC-07 | AC-04 | IPv6 同 `/64` 聚合，伪造 forwarded header 在非可信 peer 下无效，可信代理链解析正确 | unit/API |
| TC-08 | AC-04 | 重采集 1h/6 day 边界；并发 20 请求只得到同一 active run/outbox | integration |
| TC-09 | AC-04 | 重投同一 Celery task、有效租约与过期租约接管均不重复生成 run/候选/预算 | task |
| TC-10 | AC-04/07 | 投票 60/61、300/301、同 voter/candidate 第 10/11 次改变边界，拒绝时当前 vote 不变 | API |
| TC-11 | AC-05 | 批次第 150/151、生命周期 500/501、USD 2、provider 40/150、40%/50% 边界均在发网前拒绝 | integration |
| TC-12 | AC-05 | 并发 reservation 与任务重试不能越限或重复记账；失败调用不返还额度，缓存命中不计费 | integration |
| TC-13 | AC-05 | 预算触顶保留已成功/缓存/手工候选，run=partial_budget_exhausted，后续生命周期耗尽重采集被阻止 | API/task |
| TC-14 | AC-06 | 同 provider/type/external ID upsert；canonical URL/fingerprint 确定性；弱记录 provisional 且不按名字合并 | unit/integration |
| TC-15 | AC-06 | 跨 provider 强信号、50m 边界、类型/地区冲突、0.98/0.85 阈值产生正确自动关联/建议/分开 | unit |
| TC-16 | AC-06 | 有 vote/override 的旧 candidate 仅 exact provider identity 自动关联；历史扫描仅输出 dry-run proposal | integration |
| TC-17 | AC-06 | 只有 qualifying run 计 absence；第 3 次但不足 7 天仍 active，跨 7 天后 source inactive；seen 重置 | integration |
| TC-18 | AC-06 | pure manual 永不自动 inactive；多来源只失活一个不使 canonical inactive；投票/覆盖/历史保留 | integration |
| TC-19 | AC-06 | 合并成功迁移来源并按最新 vote 解冲突、写审计、重算汇总；注入中途异常时全部回滚 | integration |
| TC-20 | AC-07 | 隐藏时访客只收到 user_vote 且无 counts；公开后有 aggregates；再隐藏后未来响应重新无 counts | API/E2E |
| TC-21 | AC-07 | public export 隐藏/公开遵循状态；creator export 始终含匿名汇总；均无 voter/internal secret | API |
| TC-22 | AC-08 | 创建者轻量新增/编辑，必填与候选 250 auto/300 total 容量边界正确；普通访客拒绝 | API/E2E |
| TC-23 | AC-08 | `name/category/area/source_url/notes/tier/summary` 每个字段的系统刷新、人工优先、清空恢复/空值、审计恢复和版本冲突行为正确 | integration/E2E |
| TC-24 | AC-08 | merge proposal 对比、合并、保持分开；相同证据不再重复建议，关键证据变化可 supersede | API/E2E |
| TC-25 | AC-09 | 一次性 PostgreSQL 从 base upgrade head、downgrade/upgrade；带重复 vote 的 1c4 schema 可在 b127 前确定性去重并保持最终汇总；已在 b127 的旧库也可升级 | migration |
| TC-26 | AC-09 | expand/backfill 后 hash 可读取旧分享链接；session_id 转项目域 voter hash 且计数/upsert 正确；旧 creator 不能兑换；异常数据触发预检停止 | migration |
| TC-27 | AC-10 | Redis/DB/provider 故障返回稳定公开错误；healthz 不含异常、DSN、host 或堆栈 | API |
| TC-28 | AC-10 | ruff、pytest、typecheck、production build、migration、provider mock、Compose smoke、Playwright 在 CI 通过 | CI |
| TC-29 | AC-10 | CI 网络阻断下无真实 provider 请求；任何未 mock 外呼使 job 明确失败 | CI |
| TC-30 | AC-11 | 授权发布后 DNS、TLS、首页、创建、分享读取、Cookie 投票、创建者管理与健康检查 smoke | production |
| TC-31 | AC-02/04/07 | 所有写接口对允许 Origin 成功，对缺失/null/跨站/伪造 Origin 失败；只读接口不产生状态变化 | API |
| TC-32 | AC-06/10 | 候选编辑/合并/失活后报告版本变 stale 并按新版本重建，不展示 loser 或旧字段 | integration |
| TC-33 | AC-01/03 | SSE 连接中轮换 share token 或删除项目时，下个 heartbeat 关闭旧连接且不再发送项目状态 | integration |
| TC-34 | AC-09/10 | 固定 SHA 的 bridge 对迁移前/expand schema 均可读取；对新模型项目的创建者、采集及其他写操作全部 fail closed；当前旧镜像被兼容检查拒绝用于 expand schema | migration/CI |

## 3. RED 批次

先由测试 subagent 只新增/调整测试与测试基础设施，不写产品实现，然后依次运行：

```bash
cd /Users/mentianlu/Code/travel/backend
pytest -q tests/test_access_boundary.py tests/test_rate_limits.py tests/test_project_lifecycle.py
pytest -q tests/test_collection_idempotency.py tests/test_collection_budget.py
pytest -q tests/test_candidate_identity.py tests/test_candidate_lifecycle.py tests/test_candidate_merge.py
pytest -q tests/test_vote_visibility.py tests/test_manual_overrides.py tests/test_migrations.py

cd /Users/mentianlu/Code/travel/frontend
npm test -- --run
npx playwright test
```

预期 RED：新路由/Cookie/模型/限流/预算/identity/审计/UI 尚不存在，测试应在对应行为断言处失败。现有测试仍应能启动；若因环境失败，先修测试环境并重新取得行为 RED，不能把环境错误记录成 RED。

## 4. RED 实际证据

- 执行时间：2026-08-08（Asia/Shanghai）
- 执行者：`/root/stabilize_mvp_red_tests` 测试先行 subagent
- 数据库安全边界：本批合同测试标记为 `no_db`，未打开数据库连接。测试夹具不再继承或派生普通 `DATABASE_URL`；数据库测试必须同时显式提供 `TRAVEL_TEST_DATABASE_URL`、`TRAVEL_DISPOSABLE_DB=1`，且数据库名以 `travel_test_` 开头，否则在连接或 `drop_all` 前拒绝。
- provider 安全边界：后端 RED 在 Docker `--network none` 且 `DENY_EXTERNAL_NETWORK=1` 下运行；`DATABASE_URL` 指向 `127.0.0.1:9/ignored` 作为不可连接哨兵，但本批没有请求数据库 fixture。

执行命令与结果：

```text
docker run --rm --network none \
  -e PYTHONPATH=/workspace/backend \
  -e DATABASE_URL=postgresql+psycopg://ignored:ignored@127.0.0.1:9/ignored \
  -e DENY_EXTERNAL_NETWORK=1 \
  -v /Users/mentianlu/Code/travel:/workspace \
  -w /workspace/backend travel-backend:dev \
  pytest -q tests/test_access_boundary.py tests/test_rate_limits.py \
    tests/test_project_lifecycle.py tests/test_collection_idempotency.py \
    tests/test_collection_budget.py tests/test_candidate_identity.py \
    tests/test_candidate_lifecycle.py tests/test_candidate_merge.py \
    tests/test_vote_visibility.py tests/test_manual_overrides.py \
    tests/test_migrations.py tests/test_health_contract.py

结果：27 failed in 0.09s；全部为目标合同失败，无收集、依赖、数据库或网络错误。

cd frontend && npm test -- --run
结果：1 test file failed；3 tests failed。失败分别为缺少 credentials Cookie 合同、创建者关键 UI、覆盖状态 UI。

cd frontend && npx playwright test
结果：2 failed（chromium 与 mobile-chromium）；精确失败为 mocked browser journey fixture is required，未启动浏览器或真实 provider。

docker ... pytest --collect-only -q
结果：91 tests collected in 0.10s，包括全部既有测试与新增合同测试。

docker ... ruff check --no-cache tests
结果：All checks passed!

cd frontend && npm run typecheck
结果：通过。

git diff --check
结果：通过。
```

代表性精确 RED：

```text
tests/test_access_boundary.py:25
AssertionError: legacy browser routes remain:
{'/api/projects/{project_id}', '/api/projects/{project_id}/status',
 '/api/projects/{project_id}/report', '/api/projects/{project_id}/report/stream',
 '/api/projects/{project_id}/export/google-maps',
 '/api/projects/{project_id}/recollect',
 '/api/projects/{project_id}/candidates',
 '/api/projects/{project_id}/candidates/{candidate_id}',
 '/api/candidates/{candidate_id}/votes'}
```

其他目标 RED 包括：`ProjectRead.id` 暴露、`X-Creator-Token` 仍在前端、`healthz` 序列化 `str(exc)`、`task_outbox`/`external_call_reservations`/`candidate_sources`/override/merge audit 表不存在、历史 creator migration 仍直接 `nullable=False`、disposable migration runner 与 bridge artifact 不存在。

结论：已取得由 AC-01～AC-10 目标行为缺失导致的真实 RED；允许进入实现 subagent 的 GREEN/REFACTOR，但不得把任何任务标成 GREEN。

## 5. GREEN/REFACTOR 验证

实现完成后运行：

```bash
cd /Users/mentianlu/Code/travel/backend
ruff check --no-cache app tests
pytest -q
./scripts/ci/test-migrations.sh

cd /Users/mentianlu/Code/travel/frontend
npm test -- --run
npm run typecheck
NODE_ENV=production npm run build
npx playwright test

cd /Users/mentianlu/Code/travel
docker compose config
docker compose -f docker-compose.prod.yml config
./scripts/ci/compose-smoke.sh
git diff --check
```

`test-migrations.sh` 必须自行创建随机命名的一次性 PostgreSQL 数据库，并校验 host、数据库名前缀与显式 `TRAVEL_DISPOSABLE_DB=1`；任何条件不满足立即拒绝，脚本结束后清理该单库。文档和 CI 不允许直接对继承的 `DATABASE_URL` 执行裸 downgrade。脚本还需运行旧 schema fixture 与数据计数校验。线上 TC-30 只能在代码审核成功且用户明确授权发布后执行。

## 6. 未覆盖项

- 真实第三方 provider 质量/可用性不由 CI 覆盖；发布后仅做不产生付费调用的配置与缓存/降级验证，真实调用需单独授权。
- 备份恢复演练、DNS 平台与主机内状态当前 unknown；发布前只读核查后在 `rollout.md` 补证据。
- 多浏览器/移动真机矩阵不作为项目一门禁；Playwright 覆盖 Chromium 关键旅程，响应式视口另加一档移动尺寸。
- RED 批次本身只锁定了代表性合同；GREEN 已补入真实 PostgreSQL/Redis 的预算、并发、迁移和 bridge 动态边界，详见下一节。更完整的逐阈值/故障注入矩阵仍是后续测试增强项，不替代当前独立代码审核。
- Playwright 已从 mock API 升级为真实 Compose 全栈页面交互；浏览器不拦截 `/api/**`，仅 provider 指向内部本地 mock。
- 一次性 PostgreSQL/Redis 已启动并在验证后清理；未连接或改写任何未知/生产数据库。

## 7. GREEN/REFACTOR 实际证据

- 执行时间：2026-08-08（Asia/Shanghai）。
- 隔离：随机/前缀受限的一次性 PostgreSQL、一次性 Redis、`DENY_EXTERNAL_NETWORK=1`；测试 Compose 网络为 internal，未调用真实 provider。
- 后端：`ruff check --no-cache app scripts tests` 通过；完整 pytest 使用真实 PostgreSQL 与 Redis，`108 passed`、无跳过。
- 动态边界：原预算/并发/Redis 边界继续通过；新增重复 provider delivery 仅真实 send 一次、reservation 后删除 send=0、过期 lease 唯一重排并可领取、active 恢复、日志无 token、XFF 防 spoof/非法拒绝、连续相同采集轮次不增版本/outbox、删除持久化竞态完整 rollback、effective override 报告、merge 完整审计与注入失败 rollback。
- 迁移：随机 `travel_test_*` 数据库完成空库 `upgrade head`、`downgrade base`、再升级至 `1c4...`，插入重复旧票后升级 head；最终只保留较新 `dislike`，项目为 `legacy_unclaimed` 且 share/voter hash 完整；expand 同时放宽旧 `token`、`creator_token`、`session_id` 明文字段，使新 hash-only 行可真实写入，downgrade 前仅在一次性测试库回填兼容值。
- bridge：发布前只读预检发现 P1-9 expand migration 修复导致旧 manifest `2ebb5e1ddb1cd75829597afcebe762379fa9bd292b6b0423cd340808d428e327` 漂移；按既有完整覆盖算法更新为 `fdc9c41945ba38df0ab43701b4a1c4cc864649ee16cdc9bb0b448f321e01938b` 后 compatibility check 通过，本地镜像 ID `sha256:efd8b58acf0ddce6db16bed1e35329e677ab04813c55d3c155c4c25d9ddddef8`（不是远端发布 digest）。同一旧分享令牌在 1c 与 expand schema 均由实际 bridge 容器和实际 Next.js 页面完成 project/status/report/candidates/creator-check bootstrap，Chromium pre/expand 各 `1 passed`，所有写返回 `bridge_write_disabled`；Python base digest 与全部依赖均锁定，未配置或调用 provider。
- 前端：Vitest 3/3、TypeScript、`NODE_ENV=production` build 通过；Compose HTTPS 网关上的 Chromium 与 mobile-chromium `2 passed`。真实 Next.js → FastAPI → PostgreSQL/Redis 链路完成 create/active recovery/manual candidate/vote/reveal-hide/rotate/delete/deleted recovery；通过浏览器 cookie jar 断言真实 `Secure`、`HttpOnly`、`SameSite=Lax` 与 token-scoped Path，非法 Origin 403，并在 reload/轮换/恢复后核对持久化状态。
- Compose：开发、生产、测试 profile config 通过；`compose-smoke.sh` 实际启动 backend/frontend/PostgreSQL/Redis/mock-provider/HTTPS gateway，等待真实 health，执行合法/非法 Origin 创建 smoke，并验证 external reservation 为 0 后清理。核心服务只连 internal 网络，gateway 单独连接 edge；`DENY_EXTERNAL_NETWORK=1`，无真实 provider。GitHub Actions 已建立但远端尚未运行，状态为 unknown；失败日志经脱敏过滤后采集。
- 未执行：生产、DNS/TLS、备份恢复、真实 provider、commit/push/PR；均需独立代码审核和用户明确发布授权。
