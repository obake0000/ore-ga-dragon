(() => {
  'use strict';
  const evidenceUrl = 'https://obake0000.github.io/ore-ga-dragon/reports/kingdom-six-1118/publication.json';
  const state = document.getElementById('publication-check-state');
  const details = document.getElementById('publication-check-values');
  const sites = document.getElementById('publication-check-sites');
  const usageBox = document.getElementById('publication-check-usage');
  const badges = typeof document.querySelectorAll === 'function'
    ? Array.from(document.querySelectorAll('[data-publication-state], [data-publication-status]')).map(node => ({node, original: node.textContent})) : [];
  const originalTitle = document.title;
  if (!state || !details || !sites) return;
  const pending = '配信の照合記録は公開後に追加します';
  function reset() {
    state.textContent = pending;
    details.hidden = true;
    sites.hidden = true;
    sites.replaceChildren();
    if (usageBox) { usageBox.hidden = true; usageBox.replaceChildren(); }
    for (const item of badges) item.node.textContent = item.original;
    if (typeof originalTitle === 'string') document.title = originalTitle;
  }
  function renderUsage(usage) {
    if (!usageBox || !usage || typeof usage.at !== 'string' || !Number.isFinite(Date.parse(usage.at)) ||
        typeof usage.scope !== 'string' || !usage.scope.trim() || !Array.isArray(usage.rows) || !usage.rows.length) return;
    const keys = ['total_tokens', 'cached_input_tokens', 'uncached_input_tokens', 'output_tokens'];
    const valid = usage.rows.every(row => row && typeof row.label === 'string' && row.label.trim() &&
      typeof row.started_at === 'string' && Number.isFinite(Date.parse(row.started_at)) &&
      typeof row.cutoff === 'string' && Number.isFinite(Date.parse(row.cutoff)) &&
      Date.parse(row.cutoff) >= Date.parse(row.started_at) &&
      keys.every(key => Number.isSafeInteger(row[key]) && row[key] >= 0) &&
      row.cached_input_tokens + row.uncached_input_tokens + row.output_tokens === row.total_tokens);
    if (!valid) return;
    function append(parent, tag, value) {
      const item = document.createElement(tag); item.textContent = value; parent.appendChild(item); return item;
    }
    append(usageBox, 'h3', '公開照合時点までの使用量');
    append(usageBox, 'p', `集計時点：${usage.at}。${usage.scope}`);
    append(usageBox, 'p', '担当セッション区間の集計です。個別のキャラや項目への按分値ではありません。キャッシュ入力は総量の内数です。総量はキャッシュ入力・非キャッシュ入力・出力の3つだけを合算し、入力総量を重ねて足しません。');
    for (const row of usage.rows) {
      const panel = append(usageBox, 'details', '');
      append(panel, 'summary', row.label);
      append(panel, 'p', `区間：${row.started_at} 〜 ${row.cutoff}`);
      const values = append(panel, 'dl', '');
      for (const [label, key] of [['総量', 'total_tokens'], ['キャッシュ入力', 'cached_input_tokens'],
        ['非キャッシュ入力', 'uncached_input_tokens'], ['出力', 'output_tokens']]) {
        append(values, 'dt', label); append(values, 'dd', row[key].toLocaleString('ja-JP'));
      }
    }
    usageBox.hidden = false;
  }
  reset();
  fetch(evidenceUrl, {cache: 'no-store', mode: 'cors', credentials: 'omit'})
    .then(response => {
      if (!response.ok) throw new Error('Evidence unavailable');
      return response.json();
    })
    .then(data => {
      if (data?.published_all !== true || !Array.isArray(data.sites) || data.sites.length !== 3 ||
          typeof data.game_commit !== 'string' || !/^[a-f0-9]{7,64}$/i.test(data.game_commit) ||
          typeof data.verified_at !== 'string' || !Number.isFinite(Date.parse(data.verified_at))) {
        throw new Error('Evidence incomplete');
      }
      const verifiedSites = data.sites.map(site => {
        if (!site || typeof site.label !== 'string' || !site.label.trim() ||
            typeof site.url !== 'string' || !Number.isInteger(site.checked) || site.checked < 1) {
          throw new Error('Site evidence incomplete');
        }
        const url = new URL(site.url);
        const matched = site.ok === true ? site.checked : site.ok;
        if (url.protocol !== 'https:' || !Number.isInteger(matched) || matched !== site.checked) {
          throw new Error('Site mismatch');
        }
        return {label: site.label, url: url.href, checked: site.checked, matched};
      });
      if (new Set(verifiedSites.map(site => site.url)).size !== 3) throw new Error('Duplicate site');
      document.getElementById('publication-check-time').textContent = data.verified_at;
      document.getElementById('publication-check-commit').textContent = data.game_commit;
      for (const site of verifiedSites) {
        const item = document.createElement('li');
        const link = document.createElement('a');
        link.href = site.url;
        link.textContent = site.label;
        item.appendChild(link);
        const count = document.createElement('span');
        count.textContent = `：${site.matched}/${site.checked}件が一致`;
        item.appendChild(count);
        sites.appendChild(item);
      }
      state.textContent = '3つの公開先の配信一致を確認しました。';
      details.hidden = false;
      sites.hidden = false;
      renderUsage(data.usage);
      for (const item of badges) item.node.textContent = '公開済み';
      if (typeof originalTitle === 'string') document.title = originalTitle.replace(/（公開確認待ち）$/, '') + '（公開済み）';
    })
    .catch(reset);
})();
