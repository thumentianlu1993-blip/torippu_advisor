## Why

制作一份高质量旅游攻略需要跨多个平台收集、对比、筛选海量信息（景点、餐厅、住宿、交通、预约、评价等），普通用户难以在有限时间内完成充分调研，最终行程往往变成"每日去哪玩"的简单罗列，缺乏可执行性。本项目通过自动化信息采集和 AI 结构化整理，先输出"过饱和候选报告"再让用户与同行人选择，解决信息过载和决策不充分的问题。

## What Changes

本次变更是旅游攻略生成平台的 **MVP 初始化**，建设一个可部署在云服务器上的 Web 应用，支持：

- 用户输入目的地、时长、时间、出发地、同行人、偏好、预算、限制等基础信息。
- 创建项目后立即触发多源自动信息采集（Google Maps、Tripadvisor、Booking/Agoda、景点官网、小红书）。
- 使用 LLM（硅基流动聚合 API）将采集结果整理为结构化调研报告，包含：
  - 核心体验候选
  - 重要体验候选（自然景观、人文景观、游玩景观、购物、当地特色、个人偏好、小众体验）
  - 美食候选（正餐预约池 + 随机资源池）
  - 住宿区域与酒店候选
  - 交通与自驾可行性
  - 预算初估
  - 季节、天气、签证、预约、交通等旅行 tips
  - 多条参考路线
- 支持轻量协作：通过公开链接让同行人查看报告并对核心体验、重要体验、餐厅、住宿进行投票/反选，无需注册。
- 支持报告重新采集和手动编辑候选池。
- 输出网页版完整攻略页面；Google Maps 点位清单导出作为 nice-to-have。
- 部署到阿里云服务器，使用子域名（如 `travel.umafans.run`）与现有 `umafans.run` 项目共存。

**不在 MVP 范围内**：正式行程生成（每日执行表、Plan B、可砍项目等）、内嵌交互地图、支付/预订、用户注册登录系统、通知机制、日历提醒导出。

## Capabilities

### New Capabilities

- `project-onboarding`: 项目创建与基础信息管理。
- `data-collection`: 多源自动信息采集与降级处理。
- `research-report-generation`: 基于采集数据生成结构化调研报告。
- `candidate-pool-management`: 候选池展示、分级、重新采集与手动编辑。
- `lightweight-collaboration`: 公开链接投票与反选。
- `report-export`: 网页报告、Google Maps 点位导出。
- `deployment-infrastructure`: Docker Compose 部署、与现有 Nginx/域名共存、独立 PostgreSQL 容器。

### Modified Capabilities

无。本项目为全新初始化，没有现有 spec 需要修改。

## Impact

- **代码仓库**：新增完整前后端代码、Docker 配置、Nginx 配置、数据库迁移脚本。
- **API**：新增 REST API 供 Next.js 前端调用，以及 Celery 任务队列供异步采集/生成。
- **依赖**：硅基流动 OpenAI-compatible API、Google Maps Places API（可能需申请 Key）、第三方小红书采集服务/工具、PostgreSQL、Redis、Celery、Docker、Nginx。
- **系统**：新增 Docker Compose 服务栈部署到现有阿里云服务器；新增子域名 DNS 记录；新增 Nginx server block 反向代理到新的 web 服务端口。
- **运维**：需要管理小红书采集账号/代理稳定性、LLM API 成本、图片存储、报告生成队列监控。
