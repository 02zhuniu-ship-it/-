const Apify = require('apify');
const { createTaobaoCrawler } = require('./platforms/taobao');
const { createXianyuCrawler } = require('./platforms/xianyu');
const { buildProxyConfiguration, verifyProxy } = require('./utils/proxy');

async function main() {
  const input = await Apify.getInput();
  const log = Apify.utils.log;

  if (!input || !input.platform || !input.keyword) {
    log.error('缺少必要输入参数：platform（平台） 和 keyword（关键词）');
    process.exit(1);
  }

  log.info('=== 淘宝 / 闲鱼 公开商品采集器 ===');
  log.info(`平台: ${input.platform}`);
  log.info(`关键词: "${input.keyword}"`);
  log.info(`最大页数: ${input.maxPages}, 最多商品数: ${input.maxItems || '不限'}`);
  log.info(`Stealth 反爬: ${input.useStealth ? '开启' : '关闭'}, 真人行为模拟: ${input.useHumanBehavior ? '开启' : '关闭'}`);
  log.info(`请求间隔: ${input.requestIntervalSecs}s ± ${input.randomIntervalJitterSecs}s, 并发: ${input.maxConcurrency}`);

  const proxyConfig = buildProxyConfiguration(input);
  await verifyProxy(proxyConfig, log);

  const dataset = await Apify.openDataset();

  let crawler;
  if (input.platform === 'taobao') {
    crawler = await createTaobaoCrawler({
      input, proxyConfig, dataset, log,
      crawleeProxy: proxyConfig,
    });
  } else if (input.platform === 'xianyu') {
    crawler = await createXianyuCrawler({
      input, proxyConfig, dataset, log,
      crawleeProxy: proxyConfig,
    });
  } else {
    log.error(`不支持的 platform: ${input.platform}`);
    process.exit(1);
  }

  await crawler.run();

  const info = await dataset.getInfo();
  log.info('=== 采集完成 ===');
  log.info(`成功采集: ${info.itemCount} 条数据`);
  log.info(`数据集 ID: ${dataset.id}`);
  log.info(`数据集 URL: https://console.apify.com/storage/datasets/${dataset.id}`);
}

main().catch((err) => {
  Apify.utils.log.error(`Actor 异常退出: ${err.message}`);
  Apify.utils.log.error(err.stack);
  process.exit(1);
});
