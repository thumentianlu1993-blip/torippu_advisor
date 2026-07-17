# API Key 配置指南

本文档列出本项目所有外部数据与 LLM 服务的 API Key 来源、获取方式及价格。请将实际 Key 填入 `backend/.env`（该文件不会提交到 Git）。

> 最小可跑通配置：**SiliconFlow + Serper + Jina AI Reader + Apify + Foursquare**，其余按需启用。

---

## 1. LLM（报告生成、优缺点标签提取）

| 环境变量 | 服务 | 获取方式 | 价格（2026） |
|---|---|---|---|
| `SILICONFLOW_API_KEY` | [SiliconFlow](https://siliconflow.cn) | 注册 → 控制台生成 API Key | 新账号约 ¥14（~$2）免费额度；Qwen2.5-7B 约 ¥0.4/1M tokens，Qwen2.5-72B 约 ¥2/1M tokens |

---

## 2. 搜索 + 网页提取（主链路，推荐优先配置）

| 环境变量 | 服务 | 获取方式 | 价格（2026） |
|---|---|---|---|
| `SERPER_API_KEY` | [Serper.dev](https://serper.dev) | 注册 → Dashboard 生成 | **2,500 次一次性免费**；付费按量约 $0.30–$1/1K |
| `TAVILY_API_KEY` | [Tavily](https://tavily.com) | 注册后自动生成 | **1,000 credits/月免费**；Project 计划 $30/月 4,000 credits |
| `JINA_AI_ENABLED` | [Jina AI Reader](https://r.jina.ai) | 无需 Key，设为 `true` 即可 | **免费** |
| `FIRECRAWL_API_KEY` | [Firecrawl](https://firecrawl.dev) | 注册 → 控制台生成 | **1,000 credits/月免费**；Hobby ~$13–16/月 |

### 推荐组合

```bash
SERPER_API_KEY=你的_Serper_Key
JINA_AI_ENABLED=true
```

- Serper 负责搜索目标页面（小红书、携程、TripAdvisor、大众点评等）。
- Jina AI Reader 负责提取页面正文：`https://r.jina.ai/http://目标URL`。
- Firecrawl 仅在 Jina 失败且配置了 Key 时作为 fallback。

---

## 3. POI 基础数据

| 环境变量 | 服务 | 获取方式 | 价格（2026） |
|---|---|---|---|
| `FOURSQUARE_API_KEY` | [Foursquare Places API v3](https://docs.foursquare.com/developer/docs/developer-console-get-started) | 注册 → 创建 Project → 拿 API Key | 2026.6 后 **500 Pro calls/月免费** + $200/月 credit；Pro $15/1K；Premium（照片/tips）$18.75/1K 且无免费额度 |
| `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/) | 创建项目 → 启用 Places API → 创建 Credentials | 2025.3 后取消统一 $200 credit，改为按 SKU：Essentials 10K/月、Pro 5K/月、Enterprise 1K/月免费；超出后 $5–$32/1K；**必须绑信用卡** |
| `APIFY_API_TOKEN` | [Apify](https://apify.com) | Console → Integrations → 生成 Token | **$5/月免费额度**；Starter $29/月 |
| `YELP_API_KEY` | [Yelp Fusion](https://docs.developer.yelp.com/docs/places-intro) | 注册 → 创建 App → 拿 Key | **已无免费版**，Base $229/月、Enhanced $299/月、Premium $643/月（均含 30K 调用） |

---

## 4. 平台-specific 第三方 API（兜底/补充）

### 4.1 小红书

| 环境变量 | 来源 | 获取方式 | 价格 |
|---|---|---|---|
| `XIAOHONGSHU_API_KEY`<br>`XIAOHONGSHU_API_BASE_URL`<br>`XIAOHONGSHU_API_ENDPOINT` | **官方**：[小红书开放平台](https://open.xiaohongshu.com/) | 企业认证 → 创建应用 → 拿 Key | 企业认证费约 ¥600，审核 2–4 周；按配额计费 |
| `TIKHUB_API_KEY`<br>`TIKHUB_XIAOHONGSHU_ENDPOINT` | **第三方**：TikHub.io | [tikhub.io/xiaohongshu-api](https://tikhub.io/xiaohongshu-api) 注册 | **$0.05 免费额度**，$0.01/请求 |
| 或 RapidAPI | **第三方**：[Xiaohongshu All API](https://rapidapi.com/dataapiman/api/xiaohongshu-all-api/pricing) | RapidAPI 注册订阅 | 免费 20 次/月；Pro $39.99/月 1,800 次 |

### 4.2 TripAdvisor

| 环境变量 | 来源 | 获取方式 | 价格 |
|---|---|---|---|
| `TRIPADVISOR_API_KEY` | **官方 Content API**：[developer-tripadvisor.com](https://developer-tripadvisor.com/) | 申请成为合作伙伴 | 审核制；限 5 reviews/5 photos/地点，日限 10K |
| `STAYAPI_API_KEY` | **第三方**：[StayAPI](https://stayapi.com/apis/tripadvisor) | 注册 → 订阅套餐 | 免费 50 次/月；Basic $49/月 1,500 次；Scale $450/月 10 万次 |
| `DATAFORSEO_LOGIN`<br>`DATAFORSEO_PASSWORD` | **第三方**：[DataForSEO](https://dataforseo.com/apis/reviews-api/tripadvisor-reviews-api) | 注册 → 充值 | 最低充值 $50；TripAdvisor reviews $0.00075/10 条（标准优先级） |

### 4.3 大众点评

| 环境变量 | 来源 | 获取方式 | 价格 |
|---|---|---|---|
| `DIANPING_API_KEY`<br>`DIANPING_API_BASE_URL` | **官方**：[美团开放平台](https://open.meituan.com/) | 企业资质 + 商务合作 | 评价数据不公开，需正式合作 |
| 第三方 scraping 服务 | WebFusionData / DataZivot / RetailScrape | 官网询价 | 按数据量和频率报价（非官方，需谨慎） |

### 4.4 携程 / Trip.com

| 环境变量 | 来源 | 获取方式 | 价格 |
|---|---|---|---|
| `CTRIP_API_KEY`<br>`CTRIP_API_BASE_URL` | **官方**：[携程开放平台/联盟](https://u.ctrip.com/) | 注册联盟 → 申请 API 权限 | 以酒店/机票/门票预订为主，按佣金；审核数天到数周 |
| 第三方 wrapper | 如 onebound 等 | 非官方 | 不建议生产使用 |

---

## 5. 住宿联盟（现有占位）

| 环境变量 | 来源 | 获取方式 | 价格 |
|---|---|---|---|
| `BOOKING_AFFILIATE_ID` | Booking.com Affiliate / Travelpayouts | [partners.booking.com](https://partners.booking.com/) 或 [travelpayouts.com](https://www.travelpayouts.com/) | 免费加入，按预订佣金 |
| `AGODA_API_KEY` | [Agoda Partner Hub](https://partners.agoda.com/) | 提交商业申请 | 需商务审核 4–8 周；标准佣金 4–7%，直连 API 12–18% |

---

## 6. 已废弃/可留空

| 环境变量 | 说明 |
|---|---|
| `BING_SEARCH_API_KEY` | Bing Web Search API v7 已于 2025 年 8 月退役，新账号无法申请。留空即可，已被 Serper/Tavily 替代。 |

---

## 7. 推荐的最小 `.env` 配置

```bash
# LLM
SILICONFLOW_API_KEY=your_siliconflow_api_key

# 搜索 + 网页提取（免费额度足够测试）
SERPER_API_KEY=your_serper_api_key
JINA_AI_ENABLED=true

# POI 基础数据
FOURSQUARE_API_KEY=your_foursquare_api_key
APIFY_API_TOKEN=your_apify_api_token

# 平台第三方 API（按需启用）
TIKHUB_API_KEY=your_tikhub_api_key
TIKHUB_XIAOHONGSHU_ENDPOINT=https://api.tikhub.io/api/v1/xiaohongshu/search
STAYAPI_API_KEY=your_stayapi_api_key
DATAFORSEO_LOGIN=your_dataforseo_login
DATAFORSEO_PASSWORD=your_dataforseo_password

# 以下国内平台官方接口需商务合作，可先留空
XIAOHONGSHU_API_KEY=
TRIPADVISOR_API_KEY=
DIANPING_API_KEY=
CTRIP_API_KEY=
BOOKING_AFFILIATE_ID=
AGODA_API_KEY=
```

---

## 8. 安全提醒

- 所有 Key 都写在 `backend/.env` 中，**不要提交到 Git**。
- `backend/.env.example` 只放占位符，用于团队新人参考。
- 生产环境建议通过 Docker secrets 或云厂商 Secret Manager 注入。

---

## 参考来源

- [SiliconFlow API Review](https://apirank.vip/tutorials/siliconflow-api-review/)
- [Google Maps Platform Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Foursquare Developer Console](https://docs.foursquare.com/developer/docs/developer-console-get-started)
- [Foursquare Upcoming Pricing Changes](https://docs.foursquare.com/developer/reference/upcoming-changes)
- [Apify Pricing](https://use-apify.com/docs/what-is-apify/apify-pricing)
- [Yelp Fusion Docs](https://docs.developer.yelp.com/docs/places-intro)
- [Serper.dev](https://serper.dev)
- [Tavily Credits & Pricing](https://docs.tavily.com/documentation/api-credits)
- [Firecrawl Pricing](https://fastcrw.com/blog/firecrawl-pricing-explained)
- [TikHub Xiaohongshu API](https://tikhub.io/xiaohongshu-api)
- [RapidAPI Xiaohongshu All API Pricing](https://rapidapi.com/dataapiman/api/xiaohongshu-all-api/pricing)
- [TripAdvisor Content API](https://tripadvisor-content-api.readme.io/reference/overview)
- [StayAPI TripAdvisor API](https://stayapi.com/apis/tripadvisor)
- [DataForSEO TripAdvisor Reviews API](https://dataforseo.com/apis/reviews-api/tripadvisor-reviews-api)
- [Meituan Open Platform](https://open.meituan.com/)
- [Agoda Developer Getting Started](https://developer.agoda.com/demand/docs/getting-started)
