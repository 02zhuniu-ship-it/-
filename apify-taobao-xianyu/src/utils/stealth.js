const STEALTH_BROWSERS = [
  {
    name: 'Chrome-Windows-120',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  {
    name: 'Chrome-Windows-119',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  {
    name: 'Mac-Chrome-120',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1680, height: 1050 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  {
    name: 'Edge-Windows-120',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    viewport: { width: 1920, height: 1080 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  {
    name: 'Safari-Mac-17',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  {
    name: 'iPhone-Safari-iOS-17',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    viewport: { width: 390, height: 844 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    isMobile: true,
  },
];

const REFERRERS = [
  'https://www.baidu.com/',
  'https://www.sogou.com/',
  'https://www.bing.com/',
  'https://www.zhihu.com/',
  'https://weibo.com/',
  'https://www.douyin.com/',
  'https://www.jd.com/',
  'https://cart.taobao.com/',
];

const ACCEPT_LANGUAGES = [
  'zh-CN,zh;q=0.9,en;q=0.8',
  'zh-CN,zh-Hans;q=0.9',
  'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pickBrowser() {
  return pick(STEALTH_BROWSERS);
}

function randomDelay(minSec, maxSec) {
  const ms = (minSec + Math.random() * (maxSec - minSec)) * 1000;
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function jitteredInterval(baseSec, jitterSec) {
  const jitter = (Math.random() * 2 - 1) * jitterSec;
  return Math.max(0.3, baseSec + jitter);
}

async function humanize(page, log) {
  try {
    const scrolls = 2 + Math.floor(Math.random() * 4);
    for (let i = 0; i < scrolls; i++) {
      const delta = 300 + Math.floor(Math.random() * 500);
      await page.mouse.wheel(0, delta);
      await randomDelay(0.3, 0.9);
    }
    await page.mouse.wheel(0, -(300 + Math.floor(Math.random() * 400)));
    await randomDelay(0.2, 0.6);
    await page.mouse.move(
      100 + Math.random() * 800,
      100 + Math.random() * 500,
      { steps: 15 + Math.floor(Math.random() * 20) }
    );
  } catch (e) {
    if (log) log.debug(`humanize skip: ${e.message}`);
  }
}

async function injectStealth(page, options = {}) {
  if (options.useStealth === false) return;
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    window.chrome = { runtime: {}, loadTimes: () => ({}), csi: () => ({}) };
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
      parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
  });
}

async function applyBrowserFingerprint(browserContext, browser, cookiesStr) {
  const headers = {
    'Accept-Language': pick(ACCEPT_LANGUAGES),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Ch-Ua': '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
  };
  await browserContext.setExtraHTTPHeaders(headers);
  if (cookiesStr && cookiesStr.trim()) {
    const cookies = cookiesStr.split(';').map((kv) => {
      const [name, ...rest] = kv.trim().split('=');
      const value = rest.join('=').trim();
      return { name, value, domain: '.taobao.com', path: '/' };
    }).filter((c) => c.name && c.value);
    if (cookies.length > 0) {
      await browserContext.addCookies(cookies);
    }
  }
}

module.exports = {
  STEALTH_BROWSERS,
  pickBrowser,
  pickReferrer: () => pick(REFERRERS),
  pickAcceptLanguage: () => pick(ACCEPT_LANGUAGES),
  randomDelay,
  jitteredInterval,
  humanize,
  injectStealth,
  applyBrowserFingerprint,
};
