#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIGHT MEN ランキングダッシュボード生成スクリプト
- CSVを読み込んでHTMLを生成する
- 毎日 cron で実行: 0 7 * * * python3 "/path/to/generate_ranking.py"
"""

import os, glob, csv, json, calendar, hashlib
from datetime import date, timedelta
from collections import defaultdict

# ── 設定 ──────────────────────────────────────────────────────────────
STAFF_DIR = "/Users/c5ysk6/Dropbox (個人)/01_売上管理/BM csvデータ/スタッフ別_日間"
STORE_DIR = "/Users/c5ysk6/Dropbox (個人)/01_売上管理/BM csvデータ/店舗別_日間"
OUTPUT    = "/Users/c5ysk6/Documents/eight-men-monthly-ranking/index.html"

PASSWORD  = "8"  # ← 変更可能
PW_HASH   = hashlib.sha256(PASSWORD.encode()).hexdigest()

STORES = {
    "BM1148-0664": "渋谷店",
    "BM1405-3363": "吉祥寺店",
    "BM1420-1245": "上野店",
    "BM2824-1079": "博多店",
    "BM3604-3005": "池袋東口店",
    "BM4257-6707": "新宿店",
    "BM4346-1673": "北千住店",
    "BM4459-3057": "池袋西口店",
    "BM6383-5763": "那覇新都心店",
}

# CSVに含まれる人物以外のエントリ
EXCLUDE = {"メモ", "フリー", "EIGHT MEN STYLE"}

def normalize_name(name):
    """名前から注釈を除去する（例: '武富 巧家　★池袋西口店もいます！！' → '武富 巧家'）"""
    # 全角スペース・★以降を除去
    for sep in ['\u3000', '★', '☆', '　']:
        if sep in name:
            name = name[:name.index(sep)]
    return name.strip()

# アシスタント・除外スタッフ（ランキング対象外）← 変更・追加可能
ASSISTANTS = {"青柳 甲太", "吉村 悠真", "新名 悠冬", "井上 陸斗", "工藤 邑輔"}

# ── CSV読み込み ────────────────────────────────────────────────────────
def read_sjis(path):
    try:
        with open(path, encoding='shift-jis', errors='replace') as f:
            return list(csv.DictReader(f))
    except:
        return []

def load_all():
    """全CSVを読み込む"""
    # staff[ym][store_id][date_str][name] = (指名売上, 指名数)
    staff = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0]))))
    # store[ym][store_id][date_str] = 総売上
    store = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for p in glob.glob(os.path.join(STAFF_DIR, "スタッフ別日間_*.csv")):
        parts = os.path.basename(p).replace('.csv', '').split('_')
        if len(parts) < 3 or not parts[1].startswith('BM'):
            continue
        sid, ds = parts[1], parts[2]
        ym = ds[:6]
        for row in read_sjis(p):
            n = normalize_name(row.get('スタッフ', '').strip().strip('"'))
            if not n or n in EXCLUDE:
                continue
            try:
                sales = int(float(row.get('指名売上', 0) or 0))
            except:
                sales = 0
            try:
                noms = int(float(row.get('指名数', 0) or 0))
            except:
                noms = 0
            staff[ym][sid][ds][n][0] += sales
            staff[ym][sid][ds][n][1] += noms

    for p in glob.glob(os.path.join(STORE_DIR, "店舗別日間_*.csv")):
        parts = os.path.basename(p).replace('.csv', '').split('_')
        if len(parts) < 3 or not parts[1].startswith('BM'):
            continue
        sid, ds = parts[1], parts[2]
        ym = ds[:6]
        for row in read_sjis(p):
            try:
                store[ym][sid][ds] += int(float(row.get('総売上', 0) or 0))
            except:
                pass

    return staff, store

# ── ランキング構築 ─────────────────────────────────────────────────────
def build(staff_raw, store_raw):
    today   = date.today()
    yest    = today - timedelta(days=1)
    today_s = today.strftime('%Y%m%d')
    yest_s  = yest.strftime('%Y%m%d')

    all_ym = sorted(set(list(staff_raw.keys()) + list(store_raw.keys())))
    out = {}

    for ym in all_ym:
        y, m = int(ym[:4]), int(ym[4:])
        last_ds = f"{ym}{calendar.monthrange(y, m)[1]:02d}"

        # 完了判定: 月末最終日のCSVが1つでも存在すれば確定
        is_complete = (
            any(last_ds in store_raw[ym].get(sid, {}) for sid in STORES) or
            any(last_ds in staff_raw[ym].get(sid, {}) for sid in STORES)
        )

        # その月の全日付を収集
        all_ds = set()
        for sid in staff_raw[ym]:
            all_ds |= set(staff_raw[ym][sid].keys())
        for sid in store_raw[ym]:
            all_ds |= set(store_raw[ym][sid].keys())

        cut     = last_ds if is_complete else today_s
        cur_ds  = {d for d in all_ds if d <= cut}
        prev_ds = {d for d in all_ds if d <= yest_s} if not is_complete else None

        # 集計期間（表示用）
        actual_dates = sorted(cur_ds)
        date_from = f"{actual_dates[0][:4]}年{int(actual_dates[0][4:6])}月{int(actual_dates[0][6:8])}日" if actual_dates else ''
        date_to   = f"{actual_dates[-1][:4]}年{int(actual_dates[-1][4:6])}月{int(actual_dates[-1][6:8])}日" if actual_dates else ''
        date_range = f"{date_from} 〜 {date_to}" if date_from else ''

        # ── スタッフ集計 ──
        def staff_sum(ds_set):
            tots = defaultdict(lambda: {'sales': 0, 'noms': 0, 'by_store': defaultdict(int)})
            for sid in staff_raw[ym]:
                for ds, names in staff_raw[ym][sid].items():
                    if ds_set is not None and ds not in ds_set:
                        continue
                    for n, (sales, noms) in names.items():
                        tots[n]['sales'] += sales
                        tots[n]['noms']  += noms
                        tots[n]['by_store'][sid] += sales
            # 主所属: 指名売上が最も多い店舗
            for n in tots:
                bs = tots[n]['by_store']
                tots[n]['main_sid'] = max(bs, key=bs.get) if bs else ''
            return tots

        def make_staff_list(tots):
            lst = []
            for n, v in tots.items():
                if v['sales'] <= 0:
                    continue
                if n in ASSISTANTS:
                    continue
                # 売上がある全店舗（兼任表示用）
                active_stores = [sid for sid, s in v['by_store'].items() if s > 0]
                store_name = '・'.join(STORES.get(s, s) for s in active_stores)
                lst.append({
                    'name':      n,
                    'storeIds':  active_stores,            # フィルタリング用
                    'storeId':   v['main_sid'],             # ソート・表示主所属
                    'storeName': store_name,
                    'sales':     v['sales'],
                    'noms':      v['noms'],
                })
            lst.sort(key=lambda x: -x['sales'])
            for i, x in enumerate(lst):
                x['rank'] = i + 1
            return lst

        cur_s  = staff_sum(cur_ds)
        prev_s = staff_sum(prev_ds) if prev_ds is not None else {}

        staff_list      = make_staff_list(cur_s)
        prev_staff_list = make_staff_list(prev_s)
        prev_s_rank     = {x['name']: x['rank'] for x in prev_staff_list}

        # 前月ランク
        pm = f"{y-1:04d}12" if m == 1 else f"{y:04d}{m-1:02d}"
        pm_s_rank  = {x['name']:    x['rank'] for x in out[pm]['staff']} if pm in out else {}
        pm_st_rank = {x['storeId']: x['rank'] for x in out[pm]['store']} if pm in out else {}

        for item in staff_list:
            n = item['name']
            item['prevRank']      = pm_s_rank.get(n) if is_complete else prev_s_rank.get(n)
            item['prevMonthRank'] = pm_s_rank.get(n)

        # ── 店舗集計 ──
        def store_sum(ds_set):
            tots = defaultdict(int)
            for sid in store_raw[ym]:
                for ds, s in store_raw[ym][sid].items():
                    if ds_set is not None and ds not in ds_set:
                        continue
                    tots[sid] += s
            return tots

        # スタイリスト人数（アシスタント除く・売上>0）per 店舗
        stylist_count = defaultdict(int)
        for n, v in cur_s.items():
            if n in ASSISTANTS or v['sales'] <= 0:
                continue
            for sid, s in v['by_store'].items():
                if s > 0:
                    stylist_count[sid] += 1

        def make_store_list(tots):
            lst = []
            for sid, s in tots.items():
                if s <= 0:
                    continue
                cnt = stylist_count.get(sid, 1)
                lst.append({
                    'storeId':      sid,
                    'storeName':    STORES.get(sid, sid),
                    'sales':        s,
                    'stylistCount': cnt,
                    'productivity': round(s / cnt) if cnt else 0,
                })
            lst.sort(key=lambda x: -x['sales'])
            for i, x in enumerate(lst):
                x['rank'] = i + 1
            return lst

        cur_st  = store_sum(cur_ds)
        prev_st = store_sum(prev_ds) if prev_ds is not None else {}

        store_list      = make_store_list(cur_st)
        prev_store_list = make_store_list(prev_st)
        prev_st_rank    = {x['storeId']: x['rank'] for x in prev_store_list}

        for item in store_list:
            sid = item['storeId']
            item['prevRank']      = pm_st_rank.get(sid) if is_complete else prev_st_rank.get(sid)
            item['prevMonthRank'] = pm_st_rank.get(sid)

        out[ym] = {
            'label':      f"{y}年{m}月",
            'isComplete': is_complete,
            'dateRange':  date_range,
            'staff':      staff_list,
            'store':      store_list,
        }

    return out

# ── HTML テンプレート ──────────────────────────────────────────────────
HTML = r'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>ランキング | EIGHT MEN</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;background:#f0f2f5;color:#1a1a1a;min-height:100vh;padding-bottom:30px}
#auth-screen{position:fixed;inset:0;background:#1a1a2e;display:flex;align-items:center;justify-content:center;z-index:999}
.auth-box{background:#fff;border-radius:16px;padding:36px 28px;width:320px;max-width:90vw;text-align:center}
.auth-box h2{font-size:20px;margin-bottom:6px;color:#1a1a2e}
.auth-box p{font-size:12px;color:#aaa;margin-bottom:24px}
.auth-box input{width:100%;padding:13px;border:1px solid #dce0e8;border-radius:10px;font-size:16px;margin-bottom:12px;text-align:center;outline:none}
.auth-box input:focus{border-color:#1a1a2e}
.auth-box button{width:100%;padding:14px;background:#1a1a2e;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer}
.auth-err{color:#ff3b30;font-size:12px;margin-top:10px;min-height:18px}
header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:14px 16px 10px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}
header h1{font-size:16px;font-weight:700}
.header-sub{font-size:11px;color:rgba(255,255,255,.55);margin-top:2px}
.controls{margin:10px 12px;display:flex;gap:8px}
.sel{flex:1;padding:10px 28px 10px 12px;border-radius:10px;border:1px solid #dce0e8;font-size:13px;background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%23999' d='M5 7L0 2h10z'/%3E%3C/svg%3E") no-repeat right 10px center;appearance:none;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.section{background:#fff;margin:10px 12px;border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.sec-hd{background:linear-gradient(135deg,#1a1a2e,#2d2d4e);color:#fff;padding:11px 14px;font-size:13px;font-weight:700}
.date-range{font-size:11px;color:#888;margin:6px 14px 0;padding-bottom:6px}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
thead th{background:#f8f9fb;padding:7px 8px;text-align:right;font-weight:600;border-bottom:1px solid #eef0f3;color:#777;font-size:11px;white-space:nowrap}
thead th:first-child,thead th:nth-child(2){text-align:left}
tbody td{padding:10px 8px;border-bottom:1px solid #f5f6f8;text-align:right;vertical-align:middle;white-space:nowrap}
tbody td:first-child,tbody td:nth-child(2){text-align:left}
tbody tr:last-child td{border-bottom:none}
.rb{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;border-radius:50%;font-size:10px;font-weight:700;flex-shrink:0}
.r1{background:#FFD700;color:#5a4200}.r2{background:#C0C0C0;color:#333}.r3{background:#CD7F32;color:#fff}.rn{background:#eef0f3;color:#888}
.nm{font-weight:500}
.nm-sub{display:block;font-size:10px;color:#888;font-weight:400;margin-top:1px}
.pm{font-size:10px;color:#aaa;font-weight:400;margin-left:4px}
.prod{font-size:10px;color:#888}
.rc-up{color:#30b86c}.rc-dn{color:#ff3b30}.rc-eq{color:#aaa}
footer{text-align:center;padding:16px;font-size:10px;color:#ccc}
/* モバイル最適化 */
@media(max-width:480px){
  .hide-sp{display:none}
  tbody td,.nm{font-size:11px}
  thead th{font-size:10px;padding:6px 5px}
  tbody td{padding:9px 5px}
  .rb{min-width:20px;height:20px;font-size:9px}
}
</style>
</head>
<body>

<div id="auth-screen">
  <div class="auth-box">
    <h2>🏆 EIGHT MEN</h2>
    <p>スタッフ用ランキング</p>
    <input type="password" id="pw" placeholder="パスワードを入力"
           onkeydown="if(event.key==='Enter')checkPw()">
    <button onclick="checkPw()">ログイン</button>
    <div class="auth-err" id="pw-err"></div>
  </div>
</div>

<div id="app" style="display:none">
  <header>
    <h1>🏆 スタッフランキング</h1>
    <div class="header-sub" id="sub"></div>
  </header>
  <div class="controls">
    <select class="sel" id="period" onchange="render()"></select>
    <select class="sel" id="store-sel" onchange="render()">
      <option value="all">全店舗</option>
    </select>
  </div>
  <div id="content"></div>
  <footer id="updated"></footer>
</div>

<script>
const DATA    = __DATA_JSON__;
const PW_HASH = "__PW_HASH__";
const UPDATED = "__UPDATED__";
const STORES  = __STORES_JSON__;

async function sha256(s) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function checkPw() {
  const hash = await sha256(document.getElementById('pw').value);
  if (hash === PW_HASH) {
    sessionStorage.setItem('em_auth', hash);
    showApp();
  } else {
    document.getElementById('pw-err').textContent = 'パスワードが違います';
  }
}
function showApp() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  init();
}
window.onload = () => {
  if (sessionStorage.getItem('em_auth') === PW_HASH) showApp();
};

function init() {
  const months = Object.keys(DATA).sort().reverse();
  const pSel   = document.getElementById('period');
  months.forEach(ym => {
    const o = document.createElement('option');
    o.value = ym; o.textContent = DATA[ym].label;
    pSel.appendChild(o);
  });
  const sSel = document.getElementById('store-sel');
  Object.entries(STORES).forEach(([id, name]) => {
    const o = document.createElement('option');
    o.value = id; o.textContent = name;
    sSel.appendChild(o);
  });
  document.getElementById('updated').textContent = '最終更新: ' + UPDATED;
  render();
}

function render() {
  const ym  = document.getElementById('period').value;
  const sel = document.getElementById('store-sel').value;
  const d   = DATA[ym];
  if (!d) return;

  const isAll  = sel === 'all';
  const cmpHdr = d.isComplete ? '前月比' : '前日比';

  document.getElementById('sub').textContent =
    d.label + (d.isComplete ? '（確定）' : '（集計中）');

  let html = '';

  // ── スタッフランキング ──
  const rows = isAll
    ? d.staff
    : d.staff.filter(x => x.storeIds && x.storeIds.includes(sel));

  html += `<div class="section">
  <div class="sec-hd">👑 スタッフランキング（指名売上）</div>
  <div class="date-range">📅 ${d.dateRange}</div>
  <div class="tbl-wrap"><table>
  <thead><tr>
    <th>順位</th><th>スタッフ</th>
    <th class="hide-sp">指名数</th>
    <th>指名売上</th><th>${cmpHdr}</th>
  </tr></thead><tbody>`;

  rows.forEach(item => {
    const rb = item.rank <= 3
      ? `<span class="rb r${item.rank}">${item.rank}</span>`
      : `<span class="rb rn">${item.rank}</span>`;
    const pm = (!d.isComplete && item.prevMonthRank)
      ? `<span class="pm">先月${item.prevMonthRank}位</span>` : '';
    // スマホでは店舗名を名前の下に表示、PCでは別列
    const storeSub = isAll ? `<span class="nm-sub">${item.storeName}</span>` : '';
    html += `<tr>
      <td>${rb}</td>
      <td><span class="nm">${item.name}</span>${pm}${storeSub}</td>
      <td class="hide-sp">${item.noms}人</td>
      <td>¥${item.sales.toLocaleString()}</td>
      <td>${diff(item.prevRank, item.rank)}</td>
    </tr>`;
  });

  html += '</tbody></table></div></div>';

  // ── 店舗ランキング（全店舗表示時のみ）──
  if (isAll) {
    html += `<div class="section">
    <div class="sec-hd">🏪 店舗ランキング（総売上）</div>
    <div class="date-range">📅 ${d.dateRange}</div>
    <div class="tbl-wrap"><table>
    <thead><tr>
      <th>順位</th><th>店舗</th><th>総売上</th><th class="hide-sp">生産性/人</th><th>${cmpHdr}</th>
    </tr></thead><tbody>`;

    d.store.forEach(item => {
      const rb = item.rank <= 3
        ? `<span class="rb r${item.rank}">${item.rank}</span>`
        : `<span class="rb rn">${item.rank}</span>`;
      // スマホでは生産性を店舗名の下に表示
      const prodSub = `<span class="nm-sub">生産性 ¥${item.productivity.toLocaleString()}（${item.stylistCount}人）</span>`;
      html += `<tr>
        <td>${rb}</td>
        <td>${item.storeName}${prodSub}</td>
        <td>¥${item.sales.toLocaleString()}</td>
        <td class="hide-sp"><span class="prod">¥${item.productivity.toLocaleString()}<br>${item.stylistCount}人</span></td>
        <td>${diff(item.prevRank, item.rank)}</td>
      </tr>`;
    });

    html += '</tbody></table></div></div>';
  }

  document.getElementById('content').innerHTML = html;
}

function diff(prev, cur) {
  if (prev == null) return '<span class="rc-eq">－</span>';
  const d = prev - cur;
  if (d > 0) return `<span class="rc-up">${prev}位 △${d}</span>`;
  if (d < 0) return `<span class="rc-dn">${prev}位 ▽${Math.abs(d)}</span>`;
  return `<span class="rc-eq">${prev}位 －</span>`;
}
</script>
</body>
</html>'''

# ── メイン ────────────────────────────────────────────────────────────
def main():
    print("CSVを読み込み中...")
    staff_raw, store_raw = load_all()

    print("ランキングを計算中...")
    data = build(staff_raw, store_raw)

    updated     = date.today().strftime('%Y年%m月%d日')
    data_json   = json.dumps(data,   ensure_ascii=False, separators=(',', ':'))
    stores_json = json.dumps(STORES, ensure_ascii=False, separators=(',', ':'))

    html = HTML \
        .replace('__DATA_JSON__',   data_json) \
        .replace('__PW_HASH__',     PW_HASH) \
        .replace('__UPDATED__',     updated) \
        .replace('__STORES_JSON__', stores_json)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"完了: {OUTPUT}")

if __name__ == '__main__':
    main()
