// Paste into the browser on an heb.com search page (javascript_tool), after navigate + ~5 s wait.
// Returns the search, then up to 8 short lines: name | regular price (sale) | unit price | W=by weight | product id
// Product URL = https://www.heb.com/product-detail/x/<id>
(() => {
  const d = JSON.parse(document.getElementById('__NEXT_DATA__').textContent);
  const items = d.props.pageProps.layout.visualComponents.flatMap((c) => c.items || []);
  return [new URLSearchParams(location.search).get('q'), ...items.slice(0, 8).map((it) => {
    const p = it.SKUs?.[0]?.contextPrices?.find((c) => c.context === 'ONLINE') || it.SKUs?.[0]?.contextPrices?.[0];
    const sale = p?.isOnSale || p?.isPriceCut ? ` (sale ${p.salePrice.amount})` : '';
    return ` ${it.fullDisplayName.slice(0, 70)} | ${p?.listPrice.amount}/${p?.listPrice.unit}${sale} | ${p?.unitListPrice?.amount}/${p?.unitListPrice?.unit}${it.pricedByWeight ? ' W' : ''} | ${it.productPageURL.split('/').pop()}`;
  })].join('\n');
})()
