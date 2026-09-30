const Apify = require('apify');

function buildProxyConfiguration(input) {
  const { proxyConfiguration, customProxyUrls } = input;

  const customUrls = (customProxyUrls || '')
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s && s.startsWith('http'));

  if (customUrls.length > 0) {
    return Apify.proxyConfiguration({
      proxyUrls: customUrls,
    });
  }

  if (proxyConfiguration && proxyConfiguration.useApifyProxy === false) {
    return null;
  }

  const groups = (proxyConfiguration && proxyConfiguration.apifyProxyGroups)
    ? proxyConfiguration.apifyProxyGroups
    : ['RESIDENTIAL'];
  const country = (proxyConfiguration && proxyConfiguration.apifyProxyCountry)
    ? proxyConfiguration.apifyProxyCountry
    : 'CN';

  return Apify.proxyConfiguration({
    groups,
    country,
  });
}

async function verifyProxy(proxyConfig, log) {
  if (!proxyConfig) {
    log.warning('未配置任何代理。淘宝/闲鱼反爬严格，纯数据中心IP大概率直接被封。建议在 INPUT_SCHEMA 里配置住宅代理。');
    return null;
  }
  try {
    const url = await proxyConfig.newUrl();
    log.info(`代理已就绪：${url.replace(/:\/\/([^:]+):([^@]+)@/, '://$1:***@')}`);
    return url;
  } catch (e) {
    log.warning(`代理创建失败：${e.message}。将尝试无代理运行`);
    return null;
  }
}

module.exports = {
  buildProxyConfiguration,
  verifyProxy,
};
