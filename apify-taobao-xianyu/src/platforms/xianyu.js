const Apify = require('apify');
const { PuppeteerCrawler } = require('crawlee');
const puppeteerExtra = require('puppeteer-extra');
const puppeteerStealth = require('puppeteer-extra-plugin-stealth');
const stealthUtils = require('../utils/stealth');
const helpers = require('../utils/helpers');

const stealthPuppeteer = puppeteerExtra.use(puppeteerStealth());

function buildXianyuSearchUrl(keyword, page) {
  const params = new URLSearchParams({
    q: keyword,
    page: String(page),
    sort: '_default',
  });
  return `https://www.goofish.com/search?${params.toString()}`;
}

function extractXianyuListItems($) {
  const items = [];
  const cardSelectors = [
    '[class*="itemCard"]',
    '[class*="ItemCard"]',
    '.item',
    '[data-spm*="item"]',
    'a[href*="goofish.com/item"]',
    'a[href*="2.taobao.com/item"]',
  ];
  let anchors = null;
  for (const sel of cardSelectors) {
    anchors = $(sel);
    if (anchors.length > 0) break;
  }
  if (!anchors || anchors.length === 0) return items;

  const seen = new Set();
  anchors.each((_, el) => {
    const $el = $(el);
    let url = $el.attr('href') || '';
    if (!url) return;
    url = helpers.normalizeItemUrl(url);
    if (!url || seen.has(url)) return;
    seen.add(url);

    const container = $el.closest('[class*="card"], [class*="Card"], div').addBack();
    const title = helpers.cleanText(container.find('[class*="title"], h3, p').first().text());
    const priceText = helpers.cleanText(container.find('[class*="price"]').first().text());
    const priceObj = helpers.extractPrice(priceText);
    const location = helpers.cleanText(container.find('[class*="location"], [class*="area"]').first().text());
    const sellerText = helpers.cleanText(container.find('[class*="seller"], [class*="user"], [class*="name"]').first().text());
    const descText = helpers.cleanText(container.find('[class*="desc"], [class*="description"]').first().text());
    const imgRaw = container.find('img').first().attr('src') || container.find('img').first().attr('data-src') || container.find('img').first().attr('data-original');
    const image = helpers.normalizeImageUrl(imgRaw);

    if (!title && !descText) return;

    items.push({
      platform: 'xianyu',
      title: title || descText.slice(0, 60),
      description: descText,
      price: priceObj,
      location,
      seller: sellerText,
      image,
      url,
      condition: null,
      collectedAt: new Date().toISOString(),
    });
  });
  return items;
}

async function extractXianyuDetail(page, url, log) {
  try {
    const result = await page.evaluate(() => {
      const getText = (sels) => {
        for (const sel of sels) {
          const el = document.querySelector(sel);
          if (el && el.innerText.trim()) return el.innerText.trim();
        }
        return '';
      };
      const title = getText(['h1', '[class*="title"]', '.item-title']);
      const price = getText(['[class*="priceValue"]', '[class*="price"]', '.price-num']);
      const desc = getText(['[class*="desc"]', '[class*="description"]', '.detail-desc']);
      const location = getText(['[class*="location"]', '[class*="area"]', '.city']);
      const condition = getText(['[class*="condition"]', '[class*="level"]', '.goods-level']);
      const seller = getText(['[class*="sellerName"]', '[class*="userName"]', '.nick']);
      const images = Array.from(document.querySelectorAll('img'))
        .map((img) => img.src || img.dataset.src || '')
        .filter((src) => src && src.includes('alicdn'))
        .slice(0, 9);
      return { title, price, desc, location, condition, seller, images };
    });

    return {
      title: helpers.cleanText(result.title),
      price: helpers.extractPrice(result.price),
      description: helpers.cleanText(result.desc),
      location: helpers.cleanText(result.location),
      condition: helpers.cleanText(result.condition),
      seller: helpers.cleanText(result.seller),
      images: result.images.map(helpers.normalizeImageUrl).filter(Boolean),
      url,
    };
  } catch (e) {
    log.warning(`闲鱼详情页解析失败 ${url}: ${e.message}`);
    return null;
  }
}

async function createXianyuCrawler({
  input, proxyConfig, dataset, log, crawleeProxy,
}) {
  const {
    keyword, maxPages, maxItems, crawlDetail,
    useStealth, useHumanBehavior, requestIntervalSecs, randomIntervalJitterSecs,
    pageLoadTimeoutSecs, maxConcurrency,
    priceMin, priceMax, saveScreenshots,
  } = input;

  const seenUrls = new Set();
  let collected = 0;

  const startUrls = [];
  for (let p = 1; p <= maxPages; p++) {
    startUrls.push(buildXianyuSearchUrl(keyword, p));
  }

  log.info(`闲鱼爬虫启动：关键词 "${keyword}"，${maxPages} 页，最多 ${maxItems || '不限'} 条，详情采集=${crawlDetail}`);

  return new PuppeteerCrawler({
    proxyConfiguration: crawleeProxy || undefined,
    maxConcurrency,
    requestHandlerTimeoutSecs: pageLoadTimeoutSecs + 30,
    launchContext: {
      launcher: stealthPuppeteer,
      launchOptions: {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-blink-features=AutomationControlled',
          '--disable-features=IsolateOrigins,site-per-process',
        ],
      },
    },
    preNavigationHooks: [
      async ({ page }) => {
        if (useStealth) await stealthUtils.injectStealth(page);
        const fp = stealthUtils.pickBrowser();
        await page.setViewport(fp.viewport);
        await page.setUserAgent(fp.userAgent);
        await page.evaluateOnNewDocument(() => {
          Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
          window.chrome = { runtime: {} };
        });
      },
    ],
    requestHandler: async ({ request, page, log: crawlLog, $ }) => {
      const url = request.url;
      crawlLog.info(`打开闲鱼页面：${url}`);
      const baseDelay = stealthUtils.jitteredInterval(requestIntervalSecs, randomIntervalJitterSecs);
      await stealthUtils.randomDelay(baseDelay * 0.5, baseDelay * 1.2);

      try {
        await page.waitForLoadState('networkidle2', { timeout: pageLoadTimeoutSecs * 1000 });
      } catch (e) {
        crawlLog.warning(`闲鱼页面加载超时，继续尝试解析: ${e.message}`);
      }

      const blocked = await helpers.waitForBlock(page);
      if (blocked) {
        const res = await helpers.handleBlock(page, crawlLog, saveScreenshots);
        await dataset.pushData({ platform: 'xianyu', blocked: true, ...res, url });
        throw new Error('BLOCKED: captcha or login required');
      }

      if (useHumanBehavior) {
        await stealthUtils.humanize(page, crawlLog);
      }

      const isDetailPage = url.includes('goofish.com/item') || url.includes('2.taobao.com/item');

      if (isDetailPage) {
        const detail = await extractXianyuDetail(page, url, crawlLog);
        if (detail) {
          await dataset.pushData({
            ...detail,
            platform: 'xianyu',
            pageType: 'detail',
            collectedAt: new Date().toISOString(),
          });
        }
        return;
      }

      const rawItems = extractXianyuListItems($);
      crawlLog.info(`闲鱼列表页解析到 ${rawItems.length} 个商品`);

      for (const item of rawItems) {
        if (seenUrls.has(item.url)) continue;
        seenUrls.add(item.url);

        if (!helpers.inPriceRange(item.price, priceMin, priceMax)) {
          crawlLog.debug(`跳过（价格不在范围内）: ${item.title}`);
          continue;
        }
        if (maxItems > 0 && collected >= maxItems) {
          crawlLog.info(`已达到 maxItems=${maxItems}，停止`);
          return;
        }

        if (crawlDetail) {
          Apify.pushData({ ...item, pageType: 'list', needsDetail: true });
        } else {
          await dataset.pushData({ ...item, pageType: 'list' });
        }
        collected++;
      }
    },
    failedRequestHandler: async ({ request, error, log: crawlLog }) => {
      crawlLog.warning(`闲鱼请求失败 ${request.url}: ${error.message}`);
      await dataset.pushData({
        platform: 'xianyu',
        url: request.url,
        error: error.message,
        failed: true,
        collectedAt: new Date().toISOString(),
      });
    },
  });
}

module.exports = {
  createXianyuCrawler,
  buildXianyuSearchUrl,
  extractXianyuListItems,
};
