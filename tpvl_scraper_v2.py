"""
TPVL 升級版爬蟲 v2.1
修正：從頁面標題和局數表格抓取隊名、比分、總局數
頁面結構：
  - 標題：「台鋼天鷹 vs 桃園雲豹飛將」
  - 局數表格：球隊 | 第一局 | 第二局 | ... | 累計得分 | 總比數
"""

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, os, re, io

SCHEDULE_URL = "https://www.tpvl.tw/schedule/schedule"
TOTAL_PAGES  = 11
PAGE_WAIT    = 4
MATCH_WAIT   = 3
SAVE_PATH    = os.path.join(os.path.expanduser("~"), "Desktop",
                            "tpvl_2025_v2.csv")

KNOWN_TEAMS = ['臺中連莊', '台鋼天鷹', '臺北伊斯特', '桃園雲豹飛將']

def build_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(20)
    return driver

def scroll_bottom(driver, times=2, pause=1.0):
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

# ============================================================
# Phase 1：收集所有 match ID
# ============================================================
def get_all_match_ids(driver):
    print("=" * 55)
    print(f"Phase 1：掃描賽事結果頁（共 {TOTAL_PAGES} 頁）")
    print("=" * 55)

    driver.get(SCHEDULE_URL)
    time.sleep(PAGE_WAIT + 2)
    for xpath in ["//button[contains(text(),'賽事結果')]",
                  "//div[contains(text(),'賽事結果')]"]:
        try:
            btn = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            break
        except Exception:
            continue

    all_ids = set()
    for page in range(1, TOTAL_PAGES + 1):
        driver.get(f"{SCHEDULE_URL}?tab=result&resultPage={page}")
        time.sleep(PAGE_WAIT)
        scroll_bottom(driver)

        ids = set()
        for link in driver.find_elements(By.TAG_NAME, "a"):
            try:
                href = link.get_attribute("href") or ""
                m = re.search(r'/schedule/(\d+)$', href)
                if m:
                    ids.add(int(m.group(1)))
            except Exception:
                continue
        for m in re.finditer(r'/schedule/(\d+)', driver.page_source):
            v = int(m.group(1))
            if v > 1000:
                ids.add(v)

        new = ids - all_ids
        all_ids |= ids
        print(f"  第 {page:2d}/{TOTAL_PAGES} 頁 → 新增 {len(new)} 個 ID")

    result = sorted(all_ids)
    print(f"\n✅ 共 {len(result)} 場\n")
    return result

# ============================================================
# 抓取 meta：從頁面標題和局數表格
# ============================================================
def get_match_meta(driver):
    meta = {
        'away_team': None,
        'home_team': None,
        'away_sets': None,
        'home_sets': None,
        'total_sets': None,
        'result': None,
    }

    try:
        src = driver.page_source

        # ── 1. 抓隊名：多種策略 ────────────────────────────────
        TEAMS = ['臺中連莊', '台鋼天鷹', '臺北伊斯特', '桃園雲豹飛將']

        # 策略A：頁面標題文字「XXX vs YYY」（含 HTML tag 中間夾雜的情況）
        found_teams = []
        for t in TEAMS:
            if t in src:
                # 找出現位置，依序記錄
                pos = src.find(t)
                found_teams.append((pos, t))
        found_teams.sort()  # 依出現位置排序

        if len(found_teams) >= 2:
            # 取前兩個不重複的隊名
            unique = []
            for _, t in found_teams:
                if t not in unique:
                    unique.append(t)
                if len(unique) == 2:
                    break
            if len(unique) == 2:
                # 判斷客/主：看局數表格第一行是哪隊
                # 暫時先按出現順序（通常客隊先出現）
                meta['away_team'] = unique[0]
                meta['home_team'] = unique[1]

        # 策略B：從 h1/h2/h3 標題元素抓「XXX vs YYY」
        if meta['away_team'] is None:
            for tag in ['h1', 'h2', 'h3', 'h4']:
                els = driver.find_elements(By.TAG_NAME, tag)
                for el in els:
                    text = el.text.strip()
                    for t1 in TEAMS:
                        for t2 in TEAMS:
                            if t1 != t2 and t1 in text and t2 in text:
                                meta['away_team'] = t1
                                meta['home_team'] = t2
                                break

        # 策略C：從局數表格第一欄的文字抓隊名（最準確）
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            try:
                html = table.get_attribute("outerHTML")
                if '第一局' in html or '總比數' in html or '累計得分' in html:
                    df = pd.read_html(io.StringIO(html))[0]

                    # 第一欄是球隊名稱
                    first_col = df.iloc[:, 0].astype(str).tolist()
                    row_teams = []
                    for cell in first_col:
                        for t in TEAMS:
                            if t in cell and t not in row_teams:
                                row_teams.append(t)
                    if len(row_teams) >= 2:
                        meta['away_team'] = row_teams[0]
                        meta['home_team'] = row_teams[1]

                    # 最後一欄是「總比數」
                    last_col = df.columns[-1]
                    scores = df[last_col].tolist()
                    valid = [s for s in scores
                            if str(s).strip().replace('.0','').isdigit()
                            and int(float(str(s))) <= 5]
                    if len(valid) >= 2:
                        meta['away_sets'] = int(float(str(valid[0])))
                        meta['home_sets']  = int(float(str(valid[1])))
                        total = meta['away_sets'] + meta['home_sets']
                        if total in [3, 4, 5]:
                            meta['total_sets'] = total
                            meta['result'] = f"{meta['away_sets']}:{meta['home_sets']}"
                    break
            except Exception:
                continue

    except Exception as e:
        pass

    return meta

# ============================================================
# 點選 tab
# ============================================================
def click_tab(driver, tab_name):
    for xpath in [
        f"//button[normalize-space()='{tab_name}']",
        f"//button[contains(text(),'{tab_name}')]",
        f"//div[normalize-space()='{tab_name}']",
        f"//span[normalize-space()='{tab_name}']",
    ]:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except Exception:
            continue
    return False

# ============================================================
# 抓取可見的球員統計表格
# ============================================================
def extract_visible_table(driver, mid, team_type, meta):
    try:
        visible_html = driver.execute_script("""
            var tables = document.querySelectorAll('table');
            for (var t of tables) {
                var style = window.getComputedStyle(t);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    var headers = t.querySelectorAll('th');
                    for (var h of headers) {
                        if (h.textContent.includes('球員')) {
                            return t.outerHTML;
                        }
                    }
                }
            }
            return null;
        """)

        if not visible_html:
            return None

        tables = pd.read_html(io.StringIO(visible_html))
        if not tables:
            return None

        df = tables[0].copy()
        if '球員' not in df.columns:
            return None

        df['match_id'] = mid
        df['隊伍類型'] = team_type
        df['球員名稱'] = (df['球員'].astype(str)
                         .str.split('#').str[0].str.strip())
        df = df[~df['球員名稱'].str.contains('合計|總計|Total|隊伍', na=False)]
        df = df[df['球員名稱'].str.strip() != '']

        # meta 欄位
        df['客隊名稱'] = meta['away_team']
        df['主隊名稱'] = meta['home_team']
        df['比賽結果'] = meta['result']
        df['總局數']   = meta['total_sets']

        if team_type == '客隊':
            df['對手']     = meta['home_team']
            df['本隊勝局'] = meta['away_sets']
            df['對手勝局'] = meta['home_sets']
        else:
            df['對手']     = meta['away_team']
            df['本隊勝局'] = meta['home_sets']
            df['對手勝局'] = meta['away_sets']

        return df.reset_index(drop=True)

    except Exception:
        return None

# ============================================================
# 抓取單場
# ============================================================
def scrape_one_match(driver, mid, retries=2):
    results = []
    for attempt in range(1, retries + 2):
        try:
            driver.get(f"https://www.tpvl.tw/schedule/{mid}")
            time.sleep(MATCH_WAIT)

            meta = get_match_meta(driver)

            # 客隊
            away = extract_visible_table(driver, mid, '客隊', meta)
            if away is not None and len(away) > 0:
                results.append(away)
            else:
                click_tab(driver, '客隊')
                away = extract_visible_table(driver, mid, '客隊', meta)
                if away is not None and len(away) > 0:
                    results.append(away)

            # 主隊
            if click_tab(driver, '主隊'):
                home = extract_visible_table(driver, mid, '主隊', meta)
                if home is not None and len(home) > 0:
                    results.append(home)

            break
        except Exception as e:
            if attempt <= retries:
                time.sleep(3)
            else:
                print(f"    跳過")
    return results

# ============================================================
# 存檔 + 計算每局平均
# ============================================================
def save_results(all_data):
    if not all_data:
        print("沒有任何數據")
        return

    final_df = pd.concat(all_data, ignore_index=True)

    stat_cols = ['攻擊得分','攔網得分','發球得分','接發','防守','舉球','總得分']
    for col in stat_cols:
        if col in final_df.columns:
            final_df[col] = pd.to_numeric(
                final_df[col].astype(str).str.replace('%','').str.strip(),
                errors='coerce').fillna(0)

    final_df['總局數'] = pd.to_numeric(final_df['總局數'], errors='coerce')

    # 每局平均（核心修正）
    for col in stat_cols:
        if col in final_df.columns:
            final_df[f'{col}_每局'] = (
                final_df[col] / final_df['總局數']
            ).round(3)

    final_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')

    has_sets  = final_df['總局數'].notna().sum()
    set_dist  = (final_df.drop_duplicates('match_id')['總局數']
                 .value_counts().sort_index())

    print("\n" + "=" * 55)
    print(f"🎉 完成！")
    print(f"   總筆數  ：{len(final_df)} 筆")
    print(f"   場次數  ：{final_df['match_id'].nunique()} 場")
    print(f"   球員人數：{final_df['球員名稱'].nunique()} 人")
    print(f"   成功抓到局數：{has_sets} 筆")
    print(f"\n   局數分布：")
    labels = {3.0:'3局(3:0)', 4.0:'4局(3:1)', 5.0:'5局(3:2)'}
    for s, c in set_dist.items():
        print(f"     {labels.get(s, f'{s}局')}：{c} 場")
    print(f"\n   存檔：{SAVE_PATH}")
    print("=" * 55)

# ============================================================
# 主程式
# ============================================================
def main():
    driver = build_driver()
    all_data = []

    try:
        match_ids = get_all_match_ids(driver)
        if not match_ids:
            print("找不到任何比賽 ID")
            return

        total = len(match_ids)
        print(f"Phase 2：抓取 {total} 場")
        print("=" * 55)

        for i, mid in enumerate(match_ids, 1):
            data = scrape_one_match(driver, mid)

            if data:
                s = data[0]
                result  = s['比賽結果'].iloc[0] if '比賽結果' in s.columns else '?'
                sets    = s['總局數'].iloc[0]    if '總局數'  in s.columns else '?'
                away    = s['客隊名稱'].iloc[0]  if '客隊名稱' in s.columns else '?'
                home    = s['主隊名稱'].iloc[0]  if '主隊名稱' in s.columns else '?'
                rows    = sum(len(d) for d in data)
                print(f"[{i:3d}/{total}] {mid} | {away} vs {home} | {result}（{sets}局）| {rows}筆")
            else:
                print(f"[{i:3d}/{total}] {mid} | 無數據")

            all_data.extend(data)
            time.sleep(0.8)

        save_results(all_data)

    except KeyboardInterrupt:
        print("\n⚠️  中斷！儲存目前數據...")
        save_results(all_data)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
