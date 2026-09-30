# 淘宝 / 闲鱼 公开商品采集器（Apify Actor）

一个跑在 Apify 平台上的爬虫 Actor，采集**淘宝搜索结果**和**闲鱼二手商品**的公开数据。内置 Stealth 反爬、住宅代理、真人行为模拟，用 Puppeteer 渲染 JS 动态页面。

> ⚠️ **合规声明**：本 Actor 只采集**未登录即可访问的公开搜索结果**，不绕过任何登录、滑块验证或反爬机制。请遵守淘宝/闲鱼的服务条款和相关法律法规，合理控制采集频率。

---

## 快速上手

### 1. 环境要求

- Node.js >= 18
- npm（或 yarn / pnpm）
- 一个 [Apify](https://apify.com) 账号（免费即可）
- **强烈建议**：Apify 付费套餐或单独购买**住宅代理**（Residential Proxy）

### 2. 本地安装依赖

```bash
cd apify-taobao-xianyu
npm install
```

### 3. 本地跑一次测试（模拟 Apify 环境）

```bash
# 先建一个测试用的 input.json
cat > input.json <<EOF
{
  "platform": "taobao",
  "keyword": "降噪耳机",
  "maxPages": 2,
  "maxItems": 50,
  "crawlDetail": false,
  "useStealth": true,
  "useHumanBehavior": true,
  "requestIntervalSecs": 3,
  "randomIntervalJitterSecs": 1.5,
  "pageLoadTimeoutSecs": 20,
  "maxConcurrency": 1,
  "proxyConfiguration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"],
    "apifyProxyCountry": "CN"
  },
  "taobaoSort": "default",
  "onlyInStock": true,
  "saveScreenshots": true
}
EOF

# 本地模拟运行（需要 APIFY_TOKEN 环境变量或本地 storage）
APIFY_LOCAL_EMULATION=1 node src/main.js
```

### 4. 发布到 Apify 平台

```bash
# 方法 A：用 Apify CLI（推荐）
npm install -g apify-cli
apify login            # 首次需要扫码或填 API Token
apify push             # 推到云端
apify call             # 运行一次

# 方法 B：直接推 Docker 镜像到 Apify Docker Hub
# Apify 支持通过 Dockerfile 直接构建，见 Dockerfile
```

---

## 输入参数详解

在 Apify Console → Actor → Input 里可以看到完整表单。核心参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `platform` | enum | `taobao` | `taobao` 或 `xianyu` |
| `keyword` | string | —（必填） | 搜索关键词 |
| `maxPages` | int | 5 | 最多翻几页（淘宝每页约 44 条） |
| `maxItems` | int | 0 | 最多采多少条，0=不限 |
| `crawlDetail` | bool | false | 是否进入详情页。开启后时间×3-5 |
| `useStealth` | bool | true | **必须开**，隐藏 Puppeteer 指纹 |
| `useHumanBehavior` | bool | true | 模拟真人滚动/鼠标移动，慢一点但稳 |
| `requestIntervalSecs` | float | 2.5 | 请求间隔（秒）。建议 1.5-5 |
| `randomIntervalJitterSecs` | float | 1.0 | 间隔抖动，让节奏不规律 |
| `pageLoadTimeoutSecs` | int | 20 | 页面加载超时 |
| `maxConcurrency` | int | 1 | **别超 3**，并发高了秒封 |
| `priceMin / priceMax` | float | 0 | 价格区间过滤，0=不限 |
| `onlyInStock` | bool | true | 跳过缺货/下架 |
| `saveScreenshots` | bool | true | 遇拦截自动截图，方便排查 |

### 代理配置（最关键！）

淘宝/闲鱼反爬**极其严格**。不配置住宅代理的话，跑 3-5 页就会触发滑块验证或返回空页。

**选项 A：Apify 自带住宅代理（推荐）**
```json
{
  "proxyConfiguration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"],
    "apifyProxyCountry": "CN"
  }
}
```
- RESIDENTIAL = 真实住宅 IP，成本较高（约 $2/GB）
- 也可以换成 `RESIDENTIAL_POOL` 或自建分组

**选项 B：用你自己的代理服务**
```json
{
  "customProxyUrls": "http://user:pass@proxy1.com:8080\nhttp://user:pass@proxy2.com:8080"
}
```
支持 Oxylabs、Smartproxy、国内自建住宅代理池。每行一个 URL。

> ❌ **数据中心代理（DATACENTER）绝对不要用**。淘宝/闲鱼一眼识别，直接 block。

---

## 反爬机制一览

本 Actor 做了这些事来降低被识别概率：

| 层级 | 手段 | 代码位置 |
|---|---|---|
| 浏览器指纹 | Stealth 插件 + 手动覆盖 navigator.webdriver / chrome / plugins 等 | [stealth.js](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| User-Agent | 6 套真实浏览器 UA（Chrome/Safari/Edge + Win/Mac/iOS）随机轮换 | [stealth.js](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| 视口/时区 | 跟随 UA 切换 viewport + timezoneId=Asia/Shanghai | [stealth.js](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| HTTP 请求头 | Accept-Language / Sec-Ch-Ua / Sec-Fetch-* 全套真实化 | [stealth.js](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| 行为模拟 | 随机滚动、鼠标移动、延迟点击 | [stealth.js humanize()](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| 请求节奏 | 固定间隔 + 随机抖动，避免匀速特征 | [stealth.js jitteredInterval()](file:///workspace/apify-taobao-xianyu/src/utils/stealth.js) |
| 代理 | 住宅代理 + 可选自定义代理池 | [proxy.js](file:///workspace/apify-taobao-xianyu/src/utils/proxy.js) |
| 拦截检测 | 检测滑块/登录弹窗，自动报错并截图 | [helpers.js waitForBlock()](file:///workspace/apify-taobao-xianyu/src/utils/helpers.js) |

### ⚡ 什么情况下还是会被封？

1. **没配住宅代理** → 3 页就封
2. **并发 > 3** → 5 页就封
3. **请求间隔 < 1 秒** → 10 页后触发滑块
4. **短时间内大量关键词连续跑** → 关联封（同一个代理出口）
5. **cookie 泄漏/过期** → 可能触发二次验证

---

## 输出数据格式

采集结果会自动写入 Apify Dataset，每条数据长这样：

**列表页数据（crawlDetail=false）：**
```json
{
  "platform": "taobao",
  "pageType": "list",
  "title": "索尼 WH-1000XM5 降噪耳机 头戴式",
  "price": { "type": "single", "value": 2299.00, "text": "2299" },
  "sales": 12580,
  "image": "https://img.alicdn.com/...",
  "url": "https://detail.tmall.com/item.htm?id=123456789",
  "shop": "SONY索尼官方旗舰店",
  "location": "上海",
  "collectedAt": "2024-01-15T10:30:00.000Z"
}
```

**详情页数据（crawlDetail=true）：**
```json
{
  "platform": "taobao",
  "pageType": "detail",
  "title": "...",
  "price": { "...": "..." },
  "shop": "...",
  "params": { "品牌": "Sony", "型号": "WH-1000XM5", "颜色": "黑色" },
  "description": "商品描述正文前 2000 字...",
  "url": "...",
  "collectedAt": "..."
}
```

**闲鱼特有字段：**
```json
{
  "platform": "xianyu",
  "description": "闲置95新，自用半年...",
  "location": "北京-朝阳",
  "seller": "xxx闲置",
  "condition": "9成新",
  "images": ["https://...", "https://..."]
}
```

---

## 合规性红线 ⚠️

**必须遵守的 7 条：**

1. ✅ **只采公开数据** —— 登录态才能看到的内容（订单、收藏夹、私聊）不采
2. ✅ **不绕过登录/滑块** —— 触发验证就停，绝不自动打码/模拟点击
3. ✅ **控制频率** —— 单 Actor 日请求量 < 5000，批量采集用多 Actor 分摊
4. ✅ **不采集用户个人信息** —— 闲鱼卖家的昵称/头像可采（公开），但不要存联系方式
5. ✅ **图片仅存 URL** —— 不下载原图到本地，更不要二次分发
6. ✅ **保留 robots.txt 尊重** —— 淘宝搜索页允许爬（s.taobao.com/search），但商品详情页建议降低频率
7. ✅ **仅用于市场研究/价格监控** —— 不要用于恶意比价、刷单、竞争情报的攻击性用途

**淘宝/闲鱼禁止的行为（碰到就封号/封 IP）：**
- ❌ 绕过滑块验证 / 登录墙
- ❌ 模拟 App 签名 / 加密参数逆向
- ❌ 大规模采集（日 > 10 万请求）
- ❌ 采集卖家手机号、地址、聊天记录
- ❌ 反向工程淘宝客 / 联盟 API 接口签名

---

## 目录结构

```
apify-taobao-xianyu/
├── .actor/actor.json         ← Apify Actor 元数据
├── INPUT_SCHEMA.json         ← 输入参数表单定义
├── Dockerfile                ← Apify 云端构建镜像
├── package.json
├── README.md
└── src/
    ├── main.js               ← 入口
    ├── platforms/
    │   ├── taobao.js         ← 淘宝爬虫核心
    │   └── xianyu.js         ← 闲鱼爬虫核心
    └── utils/
        ├── stealth.js        ← 反爬配置（指纹/UA/行为模拟）
        ├── proxy.js          ← 代理配置
        └── helpers.js        ← 数据清洗/价格提取/拦截检测
```

---

## 常见问题

**Q: 跑出来全是空数据怎么办？**
A: 99% 是代理没配好。先检查代理 URL 是否能访问住宅 IP，确认 `apifyProxyGroups` 包含 `RESIDENTIAL`。其次看 Dataset 里有没有 `blocked=true` 的记录，有的话就是触发反爬了。

**Q: 淘宝返回的是天猫和淘宝混合的商品，能分开吗？**
A: 当前不分开。详情页 URL 带 `detail.tmall.com` 的是天猫，`item.taobao.com` 的是淘宝。可以在 `extractListItems` 里加过滤逻辑。

**Q: 闲鱼新版 goofish.com 和旧版 2.taobao.com 有什么区别？**
A: 旧版 2.taobao.com 已经重定向到新版 goofish.com。本 Actor 直接用新版 URL。

**Q: 能定时自动跑吗？**
A: 可以。在 Apify Console → Actor → Schedules 创建定时任务（每天/每小时），设置 cron 表达式即可。

**Q: 能多关键词批量跑吗？**
A: 有两种方式：
   - Apify **Actor Task → 多个 Task 配置不同 keyword**，然后用 **Scheduler / Webhook** 串联
   - 改 `main.js` 让 `input.keywords` 接受数组，循环创建多个 crawler（注意控制总请求量）

---

## 故障排查速查

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| 所有商品为空 `itemCount=0` | 代理被识别 / 淘宝改 DOM class | 1. 换住宅代理 2. 看截图确认页面是否真加载了商品 |
| 中途触发滑块 | 请求太快 / 并发太高 / 代理 IP 脏 | 降 maxConcurrency 到 1，加 requestIntervalSecs 到 5+，换代理 |
| 跑 1-2 页就挂 | 数据中心代理用了 | 立刻换 RESIDENTIAL |
| 闲鱼一直 timeout | goofish.com 在国内境外访问慢 | 确认代理是中国出口（apifyProxyCountry=CN） |
| 本地跑通、云端跑不通 | Docker 沙箱网络差异 | 检查代理是否在容器内可连通 |
