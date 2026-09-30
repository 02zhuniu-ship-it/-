function extractPrice(text) {
  if (!text) return null;
  const cleaned = String(text).replace(/[^\d.~～-]/g, '');
  const rangeMatch = cleaned.match(/(\d+(?:\.\d+)?)\s*[~～-]\s*(\d+(?:\.\d+)?)/);
  if (rangeMatch) {
    return {
      type: 'range',
      min: parseFloat(rangeMatch[1]),
      max: parseFloat(rangeMatch[2]),
      text: `${rangeMatch[1]}~${rangeMatch[2]}`,
    };
  }
  const singleMatch = cleaned.match(/\d+(?:\.\d+)?/);
  if (singleMatch) {
    return {
      type: 'single',
      value: parseFloat(singleMatch[0]),
      text: singleMatch[0],
    };
  }
  return null;
}

function extractSales(text) {
  if (!text) return null;
  const match = String(text).match(/(\d+(?:\.\d+)?)\s*(万|千)?\s*(人付款|人已买|月销|已售|销量|成交)/);
  if (match) {
    let num = parseFloat(match[1]);
    if (match[2] === '万') num *= 10000;
    else if (match[2] === '千') num *= 1000;
    return Math.round(num);
  }
  const plain = String(text).match(/(\d+)(?!\.\d)/);
  return plain ? parseInt(plain[1], 10) : null;
}

function normalizeImageUrl(url) {
  if (!url) return null;
  let cleaned = url.trim();
  if (cleaned.startsWith('//')) cleaned = 'https:' + cleaned;
  cleaned = cleaned.replace(/^http:\/\//, 'https://');
  const sizeSuffixes = [
    /_\d+x\d+\./g,
    /_s\.jpg/g,
    /_m\.jpg/g,
    /_b\.jpg/g,
    /_\d{2,3}x\d{2,3}\.jpg/g,
  ];
  for (const re of sizeSuffixes) {
    cleaned = cleaned.replace(re, '.');
  }
  return cleaned;
}

function normalizeItemUrl(url) {
  if (!url) return null;
  let cleaned = url.trim();
  if (cleaned.startsWith('//')) cleaned = 'https:' + cleaned;
  if (cleaned.startsWith('/')) {
    cleaned = 'https://item.taobao.com' + cleaned;
  }
  const hashIdx = cleaned.indexOf('#');
  if (hashIdx > 0) cleaned = cleaned.substring(0, hashIdx);
  const paramIdx = cleaned.indexOf('?');
  if (paramIdx > 0) cleaned = cleaned.substring(0, paramIdx);
  return cleaned;
}

function cleanText(text) {
  if (!text) return '';
  return String(text).replace(/\s+/g, ' ').trim();
}

function inPriceRange(priceObj, min, max) {
  if (!priceObj || (!min && !max)) return true;
  const val = priceObj.type === 'range' ? priceObj.min : priceObj.value;
  if (min && val < min) return false;
  if (max && val > max) return false;
  return true;
}

function uuid() {
  return 'id-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

function filterInStock(statusText) {
  if (!statusText) return true;
  const blocked = ['已下架', '缺货', '暂无库存', '售罄', '已售完'];
  return !blocked.some((kw) => statusText.includes(kw));
}

function waitForBlock(page, timeoutSec = 8) {
  const selectors = [
    '#baxia-dialog',
    '#nc_1_wrapper',
    '.nc-container',
    '#login-div',
    '.J_Slider',
  ];
  return Promise.race(selectors.map((s) =>
    page.$(s).then((el) => (el ? true : null)).catch(() => null)
  )).then((found) => found || false).catch(() => false);
}

async function handleBlock(page, log, saveScreenshots = true) {
  const url = page.url();
  log.warning(`检测到反爬/登录拦截。当前URL: ${url}`);
  if (saveScreenshots && page.screenshot) {
    try {
      const ts = Date.now();
      const shot = await page.screenshot({ fullPage: true, encoding: 'base64' });
      log.info(`已保存拦截截图（${shot.length} bytes base64），可在 Dataset 的 error 字段中查看或手动 Storage 上传`);
    } catch (e) {
      log.warning(`截图失败: ${e.message}`);
    }
  }
  return { blocked: true, url, reason: 'captcha_or_login' };
}

module.exports = {
  extractPrice,
  extractSales,
  normalizeImageUrl,
  normalizeItemUrl,
  cleanText,
  inPriceRange,
  uuid,
  filterInStock,
  waitForBlock,
  handleBlock,
};
