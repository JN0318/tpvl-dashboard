"""
TPVL 單場數據爬蟲 - 主客隊完整版
關鍵修正：主隊表格預設 display:none，需點擊 tab 後才能抓取
流程：
  每場先抓客隊（預設顯示）→ 點擊主隊 tab → 再抓主隊
"""

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, os, re

# ============================================================
# 設定
# ============================================================
SCHEDULE_URL = "https://www.tpvl.tw/schedule/schedule"
TOTAL_PAGES  = 11
PAGE_WAIT    = 4
MATCH_WAIT   = 3
SAVE_PATH    = os.path.join(os.path.expanduser("~"), "Desktop",
                            "tpvl_2025_single_match_stats.csv")

# ============================================================
# Driver
# ============================================================
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

def scroll_bottom(driver, times=2, pause=1.2):
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

# ============================================================
# Phase 1：收集所有 match ID（共 11 頁）
# ============================================================
def get_all_match_ids(driver) -> list[int]:
    print("=" * 55)
    print(f"Phase 1：掃描賽事結果頁（共 {TOTAL_PAGES} 頁）")
    print("=" * 55)

    # 先進入頁面點擊「賽事結果」tab，讓 session 狀態正確
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

        # 從所有 <a href> 和 page_source 撈 ID
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
    print(f"\n✅ 共 {len(result)} 場，ID 範圍：{result[0]} ~ {result[-1]}\n")
    return result

# ============================================================
# Phase 2：逐場抓取主客兩隊數據
# ============================================================

def click_tab(driver, tab_name: str) -> bool:
    """點擊主隊或客隊 tab，成功回傳 True"""
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


def extract_visible_table(driver, mid: int, team_type: str) -> pd.DataFrame | None:
    """
    抓取目前頁面可見的球員統計表格。
    用 JavaScript 只讀取 display 不是 none 的 table。
    """
    try:
        # 用 JS 找到可見的表格 HTML
        visible_table_html = driver.execute_script("""
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

        if not visible_table_html:
            return None

        import io
        tables = pd.read_html(io.StringIO(visible_table_html))
        if not tables:
            return None

        df = tables[0].copy()
        if '球員' not in df.columns:
            return None

        df['match_id']  = mid
        df['隊伍類型']  = team_type
        df['球員名稱']  = (df['球員'].astype(str)
                           .str.split('#').str[0].str.strip())
        df = df[~df['球員名稱'].str.contains('合計|總計|Total|隊伍', na=False)]
        df = df[df['球員名稱'].str.strip() != '']
        return df.reset_index(drop=True)

    except Exception as e:
        return None


def scrape_one_match(driver, mid: int, retries: int = 2) -> list[pd.DataFrame]:
    results = []

    for attempt in range(1, retries + 2):
        try:
            driver.get(f"https://www.tpvl.tw/schedule/{mid}")
            time.sleep(MATCH_WAIT)

            # ── 客隊（預設顯示）─────────────────────────
            away = extract_visible_table(driver, mid, "客隊")
            if away is not None and len(away) > 0:
                results.append(away)
            else:
                # 嘗試直接點客隊 tab
                click_tab(driver, "客隊")
                away = extract_visible_table(driver, mid, "客隊")
                if away is not None and len(away) > 0:
                    results.append(away)

            # ── 主隊（點擊切換）─────────────────────────
            if click_tab(driver, "主隊"):
                home = extract_visible_table(driver, mid, "主隊")
                if home is not None and len(home) > 0:
                    results.append(home)
                else:
                    print(f"    ⚠️  主隊表格抓取失敗")
            else:
                print(f"    ⚠️  找不到主隊 tab")

            break  # 成功

        except Exception as e:
            if attempt <= retries:
                print(f"    重試 {attempt}/{retries}：{e}")
                time.sleep(3)
            else:
                print(f"    跳過（達重試上限）")

    return results

# ============================================================
# Phase 3：存檔
# ============================================================
def save_results(all_data: list[pd.DataFrame]):
    if not all_data:
        print("沒有任何數據可存檔")
        return

    final_df = pd.concat(all_data, ignore_index=True)

    for col in ['攻擊得分', '攔網得分', '發球得分', '接發', '防守', '舉球', '總得分']:
        if col in final_df.columns:
            final_df[col] = pd.to_numeric(
                final_df[col].astype(str).str.replace('%', '').str.strip(),
                errors='coerce'
            ).fillna(0)

    final_df.to_csv(SAVE_PATH, index=False, encoding="utf-8-sig")

    # 統計摘要
    away = final_df[final_df['隊伍類型'] == '客隊']['match_id'].nunique()
    home = final_df[final_df['隊伍類型'] == '主隊']['match_id'].nunique()

    print("\n" + "=" * 55)
    print(f"🎉 完成！")
    print(f"   總筆數  ：{len(final_df)} 筆")
    print(f"   場次數  ：{final_df['match_id'].nunique()} 場")
    print(f"   球員人數：{final_df['球員名稱'].nunique()} 人")
    print(f"   客隊場次：{away} 場")
    print(f"   主隊場次：{home} 場")
    print(f"   存檔：{SAVE_PATH}")
    print("=" * 55)

# ============================================================
# 主程式
# ============================================================
def main():
    driver = build_driver()
    all_data = []

    try:
        # Phase 1
        match_ids = get_all_match_ids(driver)
        if not match_ids:
            print("找不到任何比賽 ID，程式結束")
            return

        # Phase 2
        total = len(match_ids)
        print(f"Phase 2：抓取 {total} 場（每場主客兩隊）")
        print("=" * 55)

        for i, mid in enumerate(match_ids, 1):
            print(f"[{i:3d}/{total}] ID {mid}", end=" → ")
            data = scrape_one_match(driver, mid)
            rows  = sum(len(d) for d in data)
            teams = len(data)
            types = [d['隊伍類型'].iloc[0] for d in data]
            print(f"{rows} 筆 / {teams} 隊 {types}")
            all_data.extend(data)
            time.sleep(0.8)

        # Phase 3
        save_results(all_data)

    except KeyboardInterrupt:
        print("\n⚠️  中斷！儲存目前數據...")
        save_results(all_data)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()