const Apify = require('apify');
const { PuppeteerCrawler } = require('crawlee');
const puppeteerExtra = require('puppeteer-extra');
const puppeteerStealth = require('puppeteer-extra-plugin-stealth');
const stealthUtils = require('../utils/stealth');
const helpers = require('../utils/helpers');

function buildStealthPuppeteer() {
  const pupper = puppeteerExtra.use(puppeteerStealth());
  return pupper;
}

const stealthPuppeteer = buildStealthPuppeteer();

function buildTaobaoSearchUrl(keyword, page, sort) {
  const offset = (page - 1) * 44;
  const params = new URLSearchParams({
    q: keyword,
    s: String(offset),
    imgfile: '',
    js: '1',
    stats_click: 'searchbutton',
    spm: 'a21bo.jianhua.201856-taobao-item.1.5af911d9s4Z7qX',
  });
  if (sort && sort !== 'default') {
    const sortMap = { sales: 'sale-desc', priceAsc: 'price-asc', priceDesc: 'price-desc' };
    params.set('sort', sortMap[sort] || 'default');
  }
  return `https://s.taobao.com/search?${params.toString()}`;
}

function extractListItems($, platform = 'taobao') {
  const items = [];
  const cardSelectors = [
    '.Card--doubleCardWrapperLqG0J',
    'div.item',
    '.m-itemlist .items .item',
    '[class*="doubleCard"]',
    '[class*="ItemCard"]',
  ];
  let cards = null;
  for (const sel of cardSelectors) {
    cards = $(sel);
    if (cards.length > 0) {
      break;
    }
  }
  if (!cards || cards.length === 0) {
    return items;
  }
  cards.each((_, el) => {
    const $el = $(el);
    const title = helpers.cleanText($el.find('.title, [class*="title"], h3').first().text());
    const priceText = helpers.cleanText($el.find('.price, [class*="price"]').first().text());
    const priceObj = helpers.extractPrice(priceText);
    const salesText = helpers.cleanText($el.find('.deal-cnt, [class*="sale"], [class*="deal"]').first().text());
    const sales = helpers.extractSales(salesText);
    const imageRaw = $el.find('img').first().attr('src') || $el.find('img').first().attr('data-src');
    const image = helpers.normalizeImageUrl(imageRaw);
    const linkRaw = $el.find('a').first().attr('href') || $el.attr('href');
    const itemUrl = helpers.normalizeItemUrl(linkRaw);
    const shop = helpers.cleanText($el.find('.shop, [class*="shop"], [class*="store"]').first().text());
    const location = helpers.cleanText($el.find('.location, [class*="location"]').first().text());
    const statusText = helpers.cleanText($el.find('.status, [class*="status"]').text());
    if (!title || !itemUrl) return;
    items.push({
      platform,
      title,
      price: priceObj,
      sales,
      image,
      url: itemUrl,
      shop,
      location,
      status: statusText,
      collectedAt: new Date().toISOString(),
    });
  });
  return items;
}

async function extractDetailData(page, url, log) {
  try {
    const title = await page.$eval('h1, [class*="title"], .tb-main-title', (el) => el.innerText.trim()).catch(() => '');
    const priceSelectors = [
      '.tm-price',
      '.tm-promo-price',
      '[class*="price-value"]',
      '.tb-rmb-num',
      '[class*="priceText"]',
    ];
    let priceText = '';
    for (const sel of priceSelectors) {
      priceText = await page.$eval(sel, (el) => el.innerText.trim()).catch(() => '');
      if (priceText) break;
    }
    const shop = await page.$eval('.tb-shop-name, .slogo-shopname, [class*="shop-name"]', (el) => el.innerText.trim()).catch(() => '');
    const params = await page.evaluate(() => {
      const pairs = {};
      document.querySelectorAll('.tb-attribute li, [class*="param"] li, .attributes-list li').forEach((li) => {
        const text = li.innerText.trim();
        const m = text.match(/^([^:：]+)[:：]\s*(.+)$/);
        if (m) pairs[m[1].trim()] = m[2].trim();
      });
      return pairs;
    }).catch(() => ({}));
    const description = await page.evaluate(() => {
      const el = document.querySelector('.tb-detail-bd, [class*="description"], .detail-desc');
      return el ? el.innerText.slice(0, 2000) : '';
    }).catch(() => '');
    return {
      title: helpers.cleanText(title),
      price: helpers.extractPrice(priceText),
      shop: helpers.cleanText(shop),
      params,
      description: helpers.cleanText(description),
      url,
    };
  } catch (e) {
    log.warning(`详情页解析失败 ${url}: ${e.message}`);
    return null;
  }
}

async function createTaobaoCrawler({
  input, proxyConfig, dataset, log, crawleeProxy,
}) {
  const {
    keyword, maxPages, maxItems, crawlDetail,
    useStealth, useHumanBehavior, requestIntervalSecs, randomIntervalJitterSecs,
    pageLoadTimeoutSecs, maxConcurrency, taobaoSort,
    priceMin, priceMax, onlyInStock, saveScreenshots, cookies,
  } = input;

  const seenUrls = new Set();
  let collected = 0;

  const startUrls = [];
  for (let p = 1; p <= maxPages; p++) {
    startUrls.push(buildTaobaoSearchUrl(keyword, p, taobaoSort));
  }

  log.info(`淘宝爬虫启动：关键词 "${keyword}"，${maxPages} 页，最多 ${maxItems || '不限'} 条，详情采集=${crawlDetail}`);

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
      crawlLog.info(`打开淘宝页面：${url}`);
      const baseDelay = stealthUtils.jitteredInterval(requestIntervalSecs, randomIntervalJitterSecs);
      await stealthUtils.randomDelay(baseDelay * 0.5, baseDelay * 1.2);

      try {
        await page.waitForLoadState('networkidle2', { timeout: pageLoadTimeoutSecs * 1000 });
      } catch (e) {
        crawlLog.warning(`页面加载超时，继续尝试解析: ${e.message}`);
      }

      const blocked = await helpers.waitForBlock(page);
      if (blocked) {
        const res = await helpers.handleBlock(page, crawlLog, saveScreenshots);
        await dataset.pushData({ platform: 'taobao', blocked: true, ...res, url });
        throw new Error('BLOCKED: captcha or login required');
      }

      if (useHumanBehavior) {
        await stealthUtils.humanize(page, crawlLog);
      }

      const isDetailPage = url.includes('detail.tmall.com') || url.includes('item.taobao.com') || url.includes('item.taobao.com/item');

      if (isDetailPage) {
        const detail = await extractDetailData(page, url, crawlLog);
        if (detail) {
          await dataset.pushData({
            ...detail,
            platform: 'taobao',
            pageType: 'detail',
            collectedAt: new Date().toISOString(),
          });
        }
        return;
      }

      const rawItems = extractListItems($, 'taobao');
      crawlLog.info(`列表页解析到 ${rawItems.length} 个商品卡片`);

      for (const item of rawItems) {
        if (seenUrls.has(item.url)) continue;
        seenUrls.add(item.url);

        if (!helpers.inPriceRange(item.price, priceMin, priceMax)) {
          crawlLog.debug(`跳过（价格不在范围内）: ${item.title}`);
          continue;
        }
        if (onlyInStock && !helpers.filterInStock(item.status)) {
          crawlLog.debug(`跳过（缺货/下架）: ${item.title}`);
          continue;
        }
        if (maxItems > 0 && collected >= maxItems) {
          crawlLog.info(`已达到 maxItems=${maxItems}，停止采集`);
          return;
        }

        if (crawlDetail) {
          Apify.pushData({
            ...item,
            pageType: 'list',
            needsDetail: true,
          });
        } else {
          await dataset.pushData({
            ...item,
            pageType: 'list',
          });
        }
        collected++;
      }

      if (crawlDetail && collected > 0) {
        crawlLog.info(`已采集 ${collected} 条列表数据，详情页采集请在 workflow 中串联第二个 Actor 或手动处理。`);
      }
    },
    failedRequestHandler: async ({ request, error, log: crawlLog }) => {
      crawlLog.warning(`请求失败 ${request.url}: ${error.message}`);
      await dataset.pushData({
        platform: 'taobao',
        url: request.url,
        error: error.message,
        failed: true,
        collectedAt: new Date().toISOString(),
      });
    },
  });
}

module.exports = {
  createTaobaoCrawler,
  buildTaobaoSearchUrl,
  extractListItems,
  extractDetailData,
};
