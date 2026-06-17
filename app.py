import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# 設定
# ============================================================
TEAM_COLORS = {
    "臺中連莊":    "#004D25",
    "桃園雲豹飛將": "#E91E63",
    "台鋼天鷹":    "#005BAC",
    "臺北伊斯特":  "#FF8C00",
}

def hex_to_rgba(hex_color, opacity=0.4):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacity})'

KNOWN_TEAMS = {
    '劉博元':'桃園雲豹飛將','劉鴻敏':'桃園雲豹飛將','利安':'桃園雲豹飛將',
    '甘茂宏':'桃園雲豹飛將','陳政錡':'桃園雲豹飛將','高得益':'桃園雲豹飛將',
    '黃仁威':'桃園雲豹飛將','鄭玉森':'桃園雲豹飛將','穆多':'桃園雲豹飛將',
    '李尼希米':'桃園雲豹飛將','豹爾文':'桃園雲豹飛將','阿薩力':'桃園雲豹飛將',
    '許美中':'桃園雲豹飛將','花村和哉':'桃園雲豹飛將','洪鉦鈞':'桃園雲豹飛將',
    '李權紘':'桃園雲豹飛將','黃意凱':'桃園雲豹飛將',
    '思丹':'台鋼天鷹','陳建禎':'台鋼天鷹','睿克':'台鋼天鷹',
    '柯宗甫':'台鋼天鷹','許睿恩':'台鋼天鷹','禹良聖':'台鋼天鷹',
    '呂慶鴻':'台鋼天鷹','彭浩銘':'台鋼天鷹','馬可':'台鋼天鷹',
    '陳玠廷':'台鋼天鷹','周冠宇':'台鋼天鷹','張庭輔':'台鋼天鷹',
    '林聖恩':'台鋼天鷹','阿巴西':'台鋼天鷹','馬亞拉':'台鋼天鷹',
    '鄭博升':'台鋼天鷹','盧清銓':'台鋼天鷹',
    '雷貝洛':'臺北伊斯特','高偉誠':'臺北伊斯特','安德烈':'臺北伊斯特',
    '申承勳':'臺北伊斯特','洪榮發':'臺北伊斯特','哈雷':'臺北伊斯特',
    '陳冠銘':'臺北伊斯特','曾祥銘':'臺北伊斯特','楊子頡':'臺北伊斯特',
    '趙宇陽':'臺北伊斯特','郭宇祥':'臺北伊斯特','簡顯銘':'臺北伊斯特',
    '范鍾坪圻':'臺北伊斯特','劉少宇':'臺北伊斯特','陳冠中':'臺北伊斯特',
    '漢佳':'臺中連莊','宋柏霆':'臺中連莊','莊哲育':'臺中連莊',
    '施宗諭':'臺中連莊','蔡秉諺':'臺中連莊','薩蘭迪':'臺中連莊',
    '吳宗軒':'臺中連莊','黃謙巽':'臺中連莊','汪秉勳':'臺中連莊',
    '林冠洲':'臺中連莊','張昀亮':'臺中連莊','蘇厚禎':'臺中連莊',
    '許廷恩':'臺中連莊','施琅':'臺中連莊',
}

POS_MAP = {
    'OutsideHitter':'邊線攻擊','OppositeHitter':'對角攻擊',
    'MiddleBlocker':'中間攔網','Setter':'舉球員','Libero':'自由球員',
}

STAT_COLS = ['攻擊得分','攔網得分','發球得分','接發','防守','舉球']
STAT_LABELS = {
    '攻擊得分':'攻擊','攔網得分':'攔網','發球得分':'發球',
    '接發':'接發','防守':'防守','舉球':'舉球'
}

# 每個位置該被突顯的核心指標（順序代表重要性）
POS_KEY_STATS = {
    '邊線攻擊': ['攻擊得分','防守','接發','發球得分'],
    '對角攻擊': ['攻擊得分','發球得分','攔網得分'],
    '中間攔網': ['攔網得分','攻擊得分','發球得分'],
    '舉球員':   ['舉球','防守','攻擊得分'],
    '自由球員': ['接發','防守'],
}

# 每個位置適合計算百分位的指標（排除天生為0的項目）
POS_PERCENTILE_STATS = {
    '邊線攻擊': ['攻擊得分','攔網得分','發球得分','接發','防守'],
    '對角攻擊': ['攻擊得分','攔網得分','發球得分','接發','防守'],
    '中間攔網': ['攻擊得分','攔網得分','發球得分','防守'],
    '舉球員':   ['舉球','防守','攻擊得分','攔網得分','發球得分'],
    '自由球員': ['接發','防守'],
}

# 每個位置的「代表性指標」（取代全位置通用的「場均總得分」）
# 自由球員/舉球員不以得分衡量價值，改用各自的核心職責數據
POS_HEADLINE_LABEL = {
    '邊線攻擊': '場均總得分',
    '對角攻擊': '場均總得分',
    '中間攔網': '場均總得分',
    '舉球員':   '場均舉球',
    '自由球員': '場均接發+防守',
}

def calc_headline_value(row, prefix=''):
    """依位置回傳代表性指標數值。prefix='場均' 用於 season_df，'' 用於逐場 match_df"""
    pos = row['位置中文']
    if pos == '自由球員':
        return row[f'{prefix}接發'] + row[f'{prefix}防守']
    elif pos == '舉球員':
        return row[f'{prefix}舉球']
    else:
        return row[f'{prefix}總得分']

# ============================================================
# 數據載入
# ============================================================
@st.cache_data
def load_data():
    # 依序嘗試多個路徑，方便本機開發與雲端部署共用同一份程式碼：
    #   1. app.py 同層的 data/ 資料夾（部署時把 CSV 放這裡，一起推上 GitHub）
    #   2. app.py 同層（直接放在專案根目錄也可以）
    #   3. 使用者桌面（原本本機開發路徑，向下相容）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")

    candidate_dirs = [
        os.path.join(script_dir, "data"),
        script_dir,
        desktop,
    ]

    def find_file(filename):
        for d in candidate_dirs:
            p = os.path.join(d, filename)
            if os.path.exists(p):
                return p
        return None

    match_path = find_file("tpvl_2025_v2.csv") or find_file("tpvl_2025_single_match_stats.csv")
    match_df = pd.read_csv(match_path, encoding='utf-8-sig') if match_path else None

    if match_df is not None:
        match_df['球員名稱'] = match_df['球員'].astype(str).str.split('#').str[0].str.strip()
        match_df = match_df[~match_df['球員名稱'].str.contains('合計|總計|Total', na=False)]
        match_df['球隊'] = match_df['球員名稱'].map(KNOWN_TEAMS).fillna('未知')
        for mid_type, grp in match_df.groupby(['match_id','隊伍類型']):
            kt = grp[grp['球隊']!='未知']['球隊']
            if len(kt) > 0:
                t = kt.mode()[0]
                mask = ((match_df['match_id']==mid_type[0]) &
                        (match_df['隊伍類型']==mid_type[1]) &
                        (match_df['球隊']=='未知'))
                match_df.loc[mask,'球隊'] = t
        match_df['位置中文'] = match_df['位置'].map(POS_MAP).fillna(match_df['位置'])
        zero_cols = STAT_COLS + ['總得分']
        for c in zero_cols:
            match_df[c] = pd.to_numeric(match_df[c], errors='coerce').fillna(0)
        match_df['有上場'] = match_df[zero_cols].sum(axis=1) > 0
        sorted_ids = sorted(match_df['match_id'].unique())
        match_df['場次序號'] = match_df['match_id'].map(
            {mid: i+1 for i, mid in enumerate(sorted_ids)})

        # v2 特有欄位（局數、對手、每局平均）
        if '總局數' in match_df.columns:
            match_df['總局數'] = pd.to_numeric(match_df['總局數'], errors='coerce')
            for col in STAT_COLS + ['總得分']:
                per_col = f'{col}_每局'
                if per_col not in match_df.columns:
                    match_df[per_col] = (match_df[col] / match_df['總局數']).round(3)
            if '本隊勝局' in match_df.columns:
                match_df['本隊贏'] = (
                    pd.to_numeric(match_df['本隊勝局'], errors='coerce') >
                    pd.to_numeric(match_df['對手勝局'], errors='coerce')
                )
        else:
            match_df['總局數'] = None
            match_df['對手'] = None
            match_df['本隊贏'] = None
            for col in STAT_COLS + ['總得分']:
                match_df[f'{col}_每局'] = None

        match_df = match_df.fillna(0)
        match_df['headline_stat'] = match_df.apply(lambda r: calc_headline_value(r, prefix=''), axis=1)

    return match_df


# ============================================================
# 整季累計 + 衍生指標
# ============================================================
def build_season(match_df):
    agg_dict = dict(
        有效出場=('match_id','nunique'),
        攻擊得分=('攻擊得分','sum'),
        攔網得分=('攔網得分','sum'),
        發球得分=('發球得分','sum'),
        接發=('接發','sum'),
        防守=('防守','sum'),
        舉球=('舉球','sum'),
        總得分=('總得分','sum'),
    )
    # v2 有局數欄位
    has_sets = '總局數' in match_df.columns and match_df['總局數'].notna().any()
    if has_sets:
        agg_dict['總局數'] = ('總局數','sum')

    s = match_df[match_df['有上場']].groupby(['球員名稱','球隊','位置中文']).agg(
        **agg_dict).reset_index()

    for col in STAT_COLS + ['總得分']:
        s[f'場均{col}'] = (s[col] / s['有效出場']).round(2)
        # 每局平均（v2 才有）
        if has_sets and '總局數' in s.columns:
            s[f'{col}_每局'] = (s[col] / s['總局數'].replace(0,1)).round(3)
        else:
            s[f'{col}_每局'] = s[f'場均{col}']  # 退回場均

    # ── 得分佔比 ─────────────────────────────────────────
    team_attack_sum = s.groupby('球隊')['攻擊得分'].sum().to_dict()
    s['攻擊得分佔比%'] = s.apply(
        lambda r: round(r['攻擊得分'] / team_attack_sum[r['球隊']] * 100, 1)
        if team_attack_sum[r['球隊']] > 0 else 0, axis=1)

    team_total_sum = s.groupby('球隊')['總得分'].sum().to_dict()
    s['總得分佔比%'] = s.apply(
        lambda r: round(r['總得分'] / team_total_sum[r['球隊']] * 100, 1)
        if team_total_sum[r['球隊']] > 0 else 0, axis=1)

    # ── 同位置內百分位排名（核心改動）────────────────────
    qualified = s[s['有效出場'] >= 5].copy()
    for col in STAT_COLS:
        avg_col = f'場均{col}'
        pct_col = f'{col}_位置百分位'
        s[pct_col] = 0.0
        for pos in s['位置中文'].unique():
            pos_mask_q = (qualified['位置中文'] == pos)
            pos_mask_s = (s['位置中文'] == pos)
            if pos_mask_q.sum() == 0:
                continue
            ranks = qualified.loc[pos_mask_q, avg_col].rank(pct=True) * 100
            s.loc[pos_mask_q.reindex(s.index, fill_value=False), pct_col] = \
                ranks.reindex(s[pos_mask_s & (s['有效出場']>=5)].index)
        s[pct_col] = s[pct_col].fillna(0).round(0)

    # ── 得分結構比例 ────────────────────────────────────
    total_score = s['攻擊得分'] + s['攔網得分'] + s['發球得分']
    s['結構_強攻%'] = (s['攻擊得分'] / total_score.replace(0,1) * 100).round(1)
    s['結構_攔網%'] = (s['攔網得分'] / total_score.replace(0,1) * 100).round(1)
    s['結構_發球%'] = (s['發球得分'] / total_score.replace(0,1) * 100).round(1)

    # ── 球員角色標籤（依位置給予不同標籤邏輯）──────────────
    def get_role(row):
        pos = row['位置中文']
        roles = []

        if pos == '自由球員':
            if row.get('接發_位置百分位',0) >= 80 and row.get('防守_位置百分位',0) >= 80:
                roles.append('防守鐵閘 🧱')
            elif row.get('接發_位置百分位',0) >= 80:
                roles.append('接發核心 📥')
            elif row.get('防守_位置百分位',0) >= 80:
                roles.append('防守悍將 🛡️')
        elif pos == '舉球員':
            if row.get('舉球_位置百分位',0) >= 80:
                roles.append('場上指揮官 🎮')
            if row.get('防守_位置百分位',0) >= 70:
                roles.append('攻防一體 ⚡')
        elif pos == '中間攔網':
            if row.get('攔網得分_位置百分位',0) >= 80:
                roles.append('長城 🛡️')
            if row.get('攻擊得分_位置百分位',0) >= 80:
                roles.append('快攻火力 🔥')
        else:  # 邊線攻擊 / 對角攻擊
            if row.get('攻擊得分_位置百分位',0) >= 80:
                roles.append('得分機器 🔥')
            if row.get('發球得分_位置百分位',0) >= 80:
                roles.append('發球殺手 🎯')
            if row.get('防守_位置百分位',0) >= 80 and row.get('接發_位置百分位',0) >= 80:
                roles.append('攻守全能 ⭐')

        if not roles:
            roles = ['一般球員']
        return ' / '.join(roles[:2])

    s['球員角色'] = s.apply(get_role, axis=1)

    # ── 綜合位置百分位（用於球探四象限圖）─────────────────
    def composite_pct(row):
        pos = row['位置中文']
        stats = POS_PERCENTILE_STATS.get(pos, STAT_COLS)
        vals = [row.get(f'{c}_位置百分位', 0) for c in stats]
        return round(sum(vals)/len(vals), 1) if vals else 0
    s['綜合位置百分位'] = s.apply(composite_pct, axis=1)

    # ── 代表性指標（依位置：攻擊手看總得分，舉球員看舉球，自由球員看接發+防守）─
    s['headline_value'] = s.apply(lambda r: calc_headline_value(r, prefix='場均'), axis=1)
    s['headline_label'] = s['位置中文'].map(POS_HEADLINE_LABEL).fillna('場均總得分')

    return s


# ============================================================
# 上下半季趨勢比較
# ============================================================
def build_half_season_trend(match_df):
    sorted_ids = sorted(match_df['match_id'].unique())
    mid_point = len(sorted_ids) // 2
    first_half = set(sorted_ids[:mid_point])
    second_half = set(sorted_ids[mid_point:])

    df = match_df[match_df['有上場']].copy()
    df['期間'] = df['match_id'].apply(lambda x: '前半季' if x in first_half else '後半季')

    trend = df.groupby(['球員名稱','期間']).agg(
        場均值=('headline_stat','mean'),
        場次=('match_id','nunique'),
    ).reset_index()

    pivot = trend.pivot(index='球員名稱', columns='期間', values='場均值').reset_index()
    pivot = pivot.fillna(0)
    if '前半季' not in pivot.columns: pivot['前半季'] = 0
    if '後半季' not in pivot.columns: pivot['後半季'] = 0

    pivot['變化量'] = (pivot['後半季'] - pivot['前半季']).round(2)
    pivot['變化率%'] = pivot.apply(
        lambda r: round((r['後半季']-r['前半季'])/r['前半季']*100,1) if r['前半季']>0 else 0,
        axis=1)

    def trend_label(diff):
        if diff >= 2: return '📈 明顯進步'
        if diff <= -2: return '📉 明顯下滑'
        return '➡️ 持平'
    pivot['趨勢'] = pivot['變化量'].apply(trend_label)

    return pivot


# ============================================================
# 對戰分析（v2 限定）
# ============================================================
def build_opponent_analysis(match_df):
    if '對手' not in match_df.columns or match_df['對手'].isna().all():
        return None
    active = match_df[
        match_df['有上場'] &
        match_df['對手'].notna() &
        (match_df['對手'].astype(str) != '0')
    ].copy()
    per_set_cols = {f'{col}_每局均': (f'{col}_每局', 'mean')
                   for col in STAT_COLS + ['總得分']
                   if f'{col}_每局' in active.columns}
    opp = active.groupby(['球員名稱','球隊','位置中文','對手']).agg(
        對戰場次=('match_id','nunique'),
        **per_set_cols
    ).reset_index()
    for col in opp.select_dtypes('float').columns:
        opp[col] = opp[col].round(2)
    return opp


# ============================================================
# 勝負分析（v2 限定）
# ============================================================
def build_win_loss_analysis(match_df):
    if '本隊贏' not in match_df.columns or match_df['本隊贏'].isna().all():
        return None
    active = match_df[
        match_df['有上場'] &
        match_df['本隊贏'].notna() &
        (match_df['本隊贏'].astype(str) != '0')
    ].copy()
    # 重新計算本隊贏（確保是 bool）
    if '本隊勝局' in active.columns:
        active['本隊贏_bool'] = (
            pd.to_numeric(active['本隊勝局'], errors='coerce') >
            pd.to_numeric(active['對手勝局'], errors='coerce')
        )
    else:
        active['本隊贏_bool'] = active['本隊贏'].astype(bool)

    stat_col = '總得分_每局' if '總得分_每局' in active.columns else 'headline_stat'
    wl = active.groupby(['球員名稱','球隊','位置中文','本隊贏_bool'])[stat_col].mean().unstack()
    wl = wl.rename(columns={False:'輸球每局均', True:'贏球每局均'})
    for c in ['輸球每局均','贏球每局均']:
        if c not in wl.columns:
            wl[c] = 0
    wl = wl.reset_index().rename(columns={'本隊贏_bool':'_drop'})
    if '_drop' in wl.columns:
        wl = wl.drop(columns=['_drop'])
    wl['差距'] = (wl['贏球每局均'] - wl['輸球每局均']).round(2)
    wl['贏球每局均'] = wl['贏球每局均'].round(2)
    wl['輸球每局均'] = wl['輸球每局均'].round(2)
    counts = active.groupby('球員名稱')['match_id'].nunique().reset_index()
    counts.columns = ['球員名稱','有效出場']
    wl = wl.merge(counts, on='球員名稱', how='left')
    return wl


# ============================================================
# 頁面設定
# ============================================================
st.set_page_config(page_title="TPVL 戰力分析平台", layout="wide", page_icon="🏐")
match_df = load_data()

if match_df is None:
    st.error("找不到數據檔案，請確認桌面有 tpvl_2025_single_match_stats.csv")
    st.stop()

season_df = build_season(match_df)
trend_df = build_half_season_trend(match_df)
season_df = season_df.merge(
    trend_df[['球員名稱','前半季','後半季','變化量','變化率%','趨勢']],
    on='球員名稱', how='left'
)
opponent_df = build_opponent_analysis(match_df)
win_loss_df  = build_win_loss_analysis(match_df)
HAS_V2 = opponent_df is not None  # 是否有 v2 數據
all_teams = sorted(TEAM_COLORS.keys())
all_positions = ['全部位置'] + list(POS_KEY_STATS.keys())

# ============================================================
# 導覽輔助：點擊卡片直接跳轉頁面並設定篩選器
# ============================================================
# Streamlit 規定：widget 一旦被渲染，當輪不能再修改其 session_state[key]。
# 所以 goto() 只記錄「待處理的導航請求」，下一輪開始時（widget 渲染前）才套用。
def goto(page=None, team=None, position=None, player=None):
    nav = {}
    if page is not None:
        nav['page'] = page
    if team is not None:
        nav['team'] = team
    if position is not None:
        nav['position'] = position
    if player is not None:
        nav['player'] = player
    else:
        nav['clear_player'] = True
    st.session_state['_pending_nav'] = nav
    st.rerun()

# 在任何 widget 渲染之前，套用上一輪點擊卡片產生的導航請求
if '_pending_nav' in st.session_state:
    _nav = st.session_state.pop('_pending_nav')
    if 'page' in _nav:
        st.session_state['sb_page'] = _nav['page']
    if 'team' in _nav:
        st.session_state['sb_team'] = _nav['team']
    if 'position' in _nav:
        st.session_state['sb_position'] = _nav['position']
    if 'player' in _nav:
        st.session_state['sb_player'] = _nav['player']
    elif _nav.get('clear_player'):
        st.session_state.pop('sb_player', None)

# ============================================================
# 側邊欄
# ============================================================
def _section_header(icon, title, color):
    """側邊欄區塊標題：彩色徽章 + 標題文字"""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:9px;margin:2px 0 12px 0;">
      <div style="width:26px;height:26px;border-radius:7px;background:{color}1A;
                  border:1px solid {color}40;
                  display:flex;align-items:center;justify-content:center;font-size:13px;">{icon}</div>
      <span style="font-size:14px;font-weight:700;color:#2b2b2b;letter-spacing:0.3px;">{title}</span>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    # 預讀上一輪的球隊主題色，用於本輪視覺樣式（選擇變更後下一輪會即時更新）
    theme = TEAM_COLORS[st.session_state.get('sb_team', all_teams[0])]

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:2px 0 18px 0;">
      <div style="width:38px;height:38px;border-radius:10px;background:{theme};
                  display:flex;align-items:center;justify-content:center;font-size:19px;
                  box-shadow:0 2px 6px {theme}55;">🏐</div>
      <div>
        <div style="font-size:16px;font-weight:800;color:#1a1a1a;line-height:1.25;">TPVL 分析平台</div>
        <div style="font-size:11px;color:#999;letter-spacing:0.5px;">2025-26 SEASON</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 卡片一：分析頁面導覽（放最上面，先決定要去哪）────────
    PAGE_INFO = {
        "聯盟總覽": {
            "icon": "🏠",
            "desc": "從這裡開始：點擊球隊卡片瀏覽，再點擊球員卡片看詳細分析",
            "filters": "無（純瀏覽入口）",
        },
        "球員個人分析": {
            "icon": "👤",
            "desc": "單一球員詳細數據、同位置百分位排名、整季趨勢",
            "filters": "位置 + 球隊 + 標記球員（即分析對象）",
        },
        "球隊總覽": {
            "icon": "🏆",
            "desc": "球隊整體數據、與聯盟平均比較、隊內貢獻佔比",
            "filters": "位置 + 球隊",
        },
        "位置排行榜": {
            "icon": "📋",
            "desc": "各位置 TOP10 排行，跨球隊比較同位置球員",
            "filters": "標記球員（會在排行中標亮）",
        },
        "跨隊比較": {
            "icon": "⚡",
            "desc": "四隊整體戰力對決，場均數據逐項比較",
            "filters": "球隊（會在圖中標亮）",
        },
        "球探中心": {
            "icon": "🎯",
            "desc": "誰值得簽？球探快速清單、對手效率、勝負關鍵",
            "filters": "位置（全聯盟球員）",
        },
    }

    with st.container(border=True):
        _section_header("📑", "分析頁面", theme)

        page = st.radio(
            "分析頁面",
            list(PAGE_INFO.keys()),
            format_func=lambda p: f"{PAGE_INFO[p]['icon']}　{p}",
            label_visibility="collapsed",
            key='sb_page',
        )

        _info = PAGE_INFO[page]
        st.markdown(f"""
        <div style="font-size:12px; color:#888; line-height:1.7; margin-top:10px;
                    padding-top:10px; border-top:1px solid rgba(0,0,0,0.06);">
          {_info['desc']}<br>
          <span style="color:{theme}; font-weight:700;">🔧 套用篩選：</span>{_info['filters']}
        </div>
        """, unsafe_allow_html=True)

    # ── 卡片二：瀏覽範圍篩選（依頁面決定顯示什麼）────────────
    if page in ("聯盟總覽", "位置排行榜"):
        # 這兩頁完全不需要瀏覽範圍卡片
        # 位置排行榜本身有分頁，聯盟總覽靠卡片點擊
        selected_position = st.session_state.get('sb_position', '全部位置')
        selected_team = st.session_state.get('sb_team', all_teams[0])
        player_pool = season_df[season_df['球隊']==selected_team]
        if selected_position != '全部位置':
            player_pool = player_pool[player_pool['位置中文']==selected_position]
        team_players = sorted(player_pool['球員名稱'].unique())
        _saved_player = st.session_state.get('sb_player')
        selected_player = (_saved_player
                           if (_saved_player and _saved_player in team_players
                               and _saved_player != '（請選擇球員）')
                           else None)

        if page == "聯盟總覽":
            st.markdown(f"""
            <div style="background:{theme}10; border:1px dashed {theme}40; border-radius:12px;
                        padding:12px 14px; font-size:12.5px; color:#777; line-height:1.7;">
              💡 點擊下方的<b>球隊卡片</b>或<b>球員卡片</b>即可瀏覽，<br>
              左側篩選器會在你進入其他頁面時自動同步。
            </div>
            """, unsafe_allow_html=True)
        # 位置排行榜：完全不顯示任何瀏覽範圍卡片

    elif page == "跨隊比較":
        # 跨隊比較只需要「標記球隊」
        with st.container(border=True):
            _section_header("⭐", "標記球隊", theme)
            selected_team = st.selectbox("球隊", all_teams, key='sb_team')
            theme = TEAM_COLORS[selected_team]
            selected_position = st.session_state.get('sb_position', '全部位置')
            selected_player = None
            st.caption("選中的球隊會在圖表中以金色外框標示")
    else:
        # 判斷這頁需不需要球員選擇器
        pages_without_player = {"球隊總覽", "球探中心"}
        pages_without_team = {"球探中心"}
        with st.container(border=True):
            _section_header("🔍", "瀏覽範圍", theme)

            selected_position = st.selectbox("位置", all_positions, key='sb_position')

            if page not in pages_without_team:
                selected_team = st.selectbox("球隊", all_teams, key='sb_team')
                theme = TEAM_COLORS[selected_team]
            else:
                selected_team = st.session_state.get('sb_team', all_teams[0])
                theme = TEAM_COLORS[selected_team]

            player_pool = season_df[season_df['球隊']==selected_team]
            if selected_position != '全部位置':
                player_pool = player_pool[player_pool['位置中文']==selected_position]
            team_players = sorted(player_pool['球員名稱'].unique())

            # 球探評估／對戰分析：球員選單應涵蓋全聯盟（球探是跨球隊找人的）
            pages_global_player = {"球探中心"}
            if page in pages_global_player:
                global_pool = season_df.copy()
                if selected_position != '全部位置':
                    global_pool = global_pool[global_pool['位置中文']==selected_position]
                all_players_league = sorted(global_pool['球員名稱'].unique())
            else:
                all_players_league = team_players

            if page not in pages_without_player:
                if all_players_league:
                    player_options = ['（請選擇球員）'] + all_players_league
                    _saved = st.session_state.get('sb_player')
                    _default_idx = (player_options.index(_saved)
                                    if _saved in player_options else 0)
                    label = "標記球員（圖表中標亮）" if page not in pages_global_player else "標記球員（全聯盟）"
                    _player_sel = st.selectbox(label,
                                               player_options,
                                               index=_default_idx,
                                               key='sb_player')
                    selected_player = None if _player_sel == '（請選擇球員）' else _player_sel
                else:
                    selected_player = None
                    st.warning("此位置無球員")
            else:
                selected_player = None

            qualified_count = season_df[season_df['有效出場']>=5]
            if selected_position != '全部位置':
                qualified_count = qualified_count[qualified_count['位置中文']==selected_position]

            st.markdown(f"""
            <div style="background:{theme}12; border:1px solid {theme}30; border-radius:9px;
                        padding:8px 11px; font-size:12px; color:#555; margin-top:6px; line-height:1.6;">
              📊 <b style="color:{theme};">{selected_position}</b>　·　
              符合資格球員　<b style="color:{theme};">{len(qualified_count)}</b> 人
              <span style="color:#999;">（出場≥5場）</span>
            </div>
            """, unsafe_allow_html=True)

st.markdown(f"""
<style>
.stApp {{ background-color: {theme}15; }}
h1,h2,h3 {{ color: {theme}; }}

/* ===================== 側邊欄整體 ===================== */
section[data-testid="stSidebar"] {{
    background-color: #F3F4F7;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding-top: 1.2rem;
}}

/* 卡片容器：白底、陰影、圓角，取代預設灰框 */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: #FFFFFF !important;
    border-radius: 14px !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    padding: 14px 14px 12px 14px;
    margin-bottom: 14px;
}}

/* ===================== 下拉選單 ===================== */
/* 標籤文字：小寫灰字、字距加寬，像表單欄位標籤 */
section[data-testid="stSidebar"] .stSelectbox label p {{
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #9A9DA6 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 2px !important;
}}
/* 選單本體 */
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    border-radius: 9px !important;
    border-color: #E4E5EA !important;
    background-color: #FAFAFC !important;
    min-height: 40px !important;
    transition: all 0.15s ease;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {{
    border-color: {theme}99 !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {{
    border-color: {theme} !important;
    box-shadow: 0 0 0 3px {theme}22 !important;
    background-color: #FFFFFF !important;
}}
/* 拉近欄位之間的垂直間距 */
section[data-testid="stSidebar"] .stSelectbox {{
    margin-bottom: 2px;
}}

/* ===================== 分析頁面：自訂導覽按鈕 ===================== */
section[data-testid="stSidebar"] div[role="radiogroup"] {{
    gap: 5px;
}}
/* 完全隱藏原生圓點 */
section[data-testid="stSidebar"] div[role="radiogroup"] label svg {{
    display: none !important;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
    display: flex;
    align-items: center;
    width: 100%;
    padding: 10px 12px;
    border-radius: 9px;
    border: 1px solid transparent;
    background-color: #F3F4F7;
    transition: all 0.15s ease;
    cursor: pointer;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
    background-color: {theme}18;
    border-color: {theme}40;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{
    font-size: 13.5px;
    font-weight: 500;
    color: #444;
    margin: 0;
}}
/* 被選中的項目：實心主題色 + 陰影，像當前頁籤 */
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
    background-color: {theme};
    box-shadow: 0 3px 8px {theme}50;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {{
    color: #FFFFFF;
    font-weight: 700;
}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 共用：位置內百分位橫條圖
# ============================================================
def percentile_bar_chart(row, theme_color, stats_to_show, title=""):
    cats = [STAT_LABELS[c] for c in stats_to_show]
    vals = [row.get(f'{c}_位置百分位', 0) for c in stats_to_show]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=vals, y=cats, orientation='h',
        marker=dict(
            color=vals,
            colorscale=[[0,'#e0e0e0'],[0.5,hex_to_rgba(theme_color,0.5)],[1,theme_color]],
            cmin=0, cmax=100,
        ),
        text=[f'{int(v)}th' for v in vals],
        textposition='outside',
        hovertemplate='%{y}：同位置前 %{x:.0f}%<extra></extra>'
    ))
    fig.add_vline(x=50, line_dash='dash', line_color='gray', opacity=0.5,
                   annotation_text='同位置平均')
    fig.update_layout(
        title=title,
        xaxis=dict(range=[0,105], title='百分位 (越右越強，僅與同位置球員比較)'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
        height=max(220, 60*len(stats_to_show)), margin=dict(l=20,r=40,t=40,b=40),
        yaxis=dict(autorange='reversed')
    )
    return fig

# ============================================================
# 頁面 0：聯盟總覽（瀏覽入口）
# ============================================================
if page == "聯盟總覽":
    st.title("🏐 TPVL 聯盟總覽")
    st.caption("點擊球隊卡片進入該隊球員名單，再點擊球員卡片查看詳細分析 — 由大到小慢慢探索")

    qualified_all = season_df[season_df['有效出場']>=5].copy()

    st.subheader("🏆 四支球隊")
    cols = st.columns(4)
    for i, team in enumerate(all_teams):
        color = TEAM_COLORS[team]
        t_df = season_df[season_df['球隊']==team]
        total_pts = int(t_df['總得分'].sum())
        top_scorer = t_df.nlargest(1, '總得分').iloc[0] if not t_df.empty else None

        with cols[i]:
            st.markdown(f"""
            <div style="background:{color}; color:white; padding:14px 16px;
                        border-radius:12px 12px 0 0; text-align:center;">
              <div style="font-size:17px; font-weight:700;">{team}</div>
            </div>
            <div style="border:1.5px solid {color}; border-top:none;
                        border-radius:0 0 12px 12px; padding:14px 16px; background:white;
                        min-height:120px;">
              <div style="font-size:12px; color:#888;">整季團隊總得分</div>
              <div style="font-size:26px; font-weight:800; color:{color}; line-height:1.3;">{total_pts}</div>
              <div style="font-size:12px; color:#888; margin-top:8px;">頭號得分手</div>
              <div style="font-size:14px; font-weight:600;">
                {top_scorer['球員名稱'] if top_scorer is not None else '-'}
                （{int(top_scorer['總得分']) if top_scorer is not None else 0} 分）
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"📂 進入 {team}", key=f"go_team_{team}", use_container_width=True):
                goto(page='球隊總覽', team=team, position='全部位置')

    st.divider()

    st.subheader("🔥 本季焦點球員")
    st.caption("依「同位置綜合百分位」排名，跨位置找出表現最突出的球員，點擊卡片直接看詳細分析")
    top_players = qualified_all.nlargest(8, '綜合位置百分位').reset_index(drop=True)

    for row_start in (0, 4):
        cols2 = st.columns(4)
        for j in range(4):
            idx = row_start + j
            if idx >= len(top_players):
                continue
            p = top_players.iloc[idx]
            color = TEAM_COLORS.get(p['球隊'], '#888888')
            with cols2[j]:
                st.markdown(f"""
                <div style="border:1.5px solid {color}; border-radius:12px;
                            padding:12px 14px; margin-bottom:6px; min-height:118px;">
                  <div style="font-size:15px; font-weight:700;">{p['球員名稱']}</div>
                  <div style="font-size:12px; color:#888;">{p['球隊']} · {p['位置中文']}</div>
                  <div style="font-size:12px; margin-top:6px;">{p['球員角色']}</div>
                  <div style="font-size:13px; color:{color}; font-weight:700; margin-top:4px;">
                    同位置前 {int(p['綜合位置百分位'])}%
                  </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看詳情 →", key=f"go_player_{p['球員名稱']}", use_container_width=True):
                    goto(page='球員個人分析', team=p['球隊'], position=p['位置中文'], player=p['球員名稱'])

    st.divider()
    st.info("💡 想直接找特定球隊或位置？也可以用左側「選擇位置／選擇球隊」篩選，"
            "再切換到「位置排行榜」「跨隊比較」「球探評估」做進階分析")

# ============================================================
# 頁面 1：球員個人分析
# ============================================================
elif page == "球員個人分析":
    if selected_player is None:
        st.title("👤 球員個人分析")
        st.info("👈 請先在左側「瀏覽範圍」選擇球隊和球員，或從「聯盟總覽」點擊球員卡片進入。")
        # 顯示各隊球員快速選單
        st.subheader("各隊球員快速選擇")
        cols = st.columns(4)
        for i, team in enumerate(all_teams):
            color = TEAM_COLORS[team]
            t_players = sorted(season_df[season_df['球隊']==team]['球員名稱'].unique())
            with cols[i]:
                st.markdown(f"<div style='font-weight:700;color:{color};margin-bottom:6px;'>{team}</div>",
                           unsafe_allow_html=True)
                for p in t_players:
                    if st.button(p, key=f"quick_{p}", use_container_width=True):
                        pos = season_df[season_df['球員名稱']==p]['位置中文'].iloc[0]
                        goto(page='球員個人分析', team=team, position=pos, player=p)
        st.stop()

    st.title(f"🏐 {selected_player} 個人分析")

    p_season = season_df[season_df['球員名稱']==selected_player]
    p_match  = match_df[(match_df['球員名稱']==selected_player) & match_df['有上場']].sort_values('場次序號')

    if p_season.empty:
        st.warning("找不到該球員數據")
        st.stop()

    row = p_season.iloc[0]
    pos = row['位置中文']

    st.markdown(f"**位置：{pos}**　|　### {row['球員角色']}")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("有效出場", f"{int(row['有效出場'])} 場")
    c2.metric("整季總得分", f"{int(row['總得分'])}")
    c3.metric("場均總得分", f"{row['場均總得分']}")
    c4.metric("位置", pos)
    c5.metric("球隊得分佔比", f"{row['總得分佔比%']}%")
    st.divider()

    col_left, col_right = st.columns([1,1])

    # ── 百分位橫條圖：只顯示該位置相關的指標 ────────────────
    with col_left:
        st.subheader(f"📊 {pos} 同位置百分位排名")
        st.caption(f"與聯盟所有「{pos}」球員比較（出場≥5場）")
        relevant_stats = POS_PERCENTILE_STATS.get(pos, STAT_COLS)
        fig_p = percentile_bar_chart(row, theme, relevant_stats)
        st.plotly_chart(fig_p, width='stretch')

    # ── 每場走勢（依位置自動切換指標）──────────────────────────
    with col_right:
        headline_label = POS_HEADLINE_LABEL.get(pos, '場均總得分')
        trend_col = 'headline_stat' if 'headline_stat' in p_match.columns else '總得分'
        trend_title = {
            '自由球員': '整季每場接發+防守走勢',
            '舉球員':   '整季每場舉球走勢',
        }.get(pos, '整季每場得分走勢')

        st.subheader(f"📈 {trend_title}")
        st.caption(f"指標：{headline_label}（自動依位置選擇最能代表該球員的數據）")

        if len(p_match) == 0:
            st.info("無單場數據")
        else:
            y_vals = p_match[trend_col]
            avg = y_vals.mean()
            # hover 格式
            unit = '分' if pos not in ['自由球員','舉球員'] else ''
            hover_tpl = f'第%{{x}}場：%{{y:.1f}}{unit}<extra></extra>'

            fig_l = go.Figure()
            fig_l.add_trace(go.Scatter(
                x=p_match['場次序號'], y=y_vals,
                mode='lines+markers',
                line=dict(color=theme, width=2),
                marker=dict(size=7, color=theme),
                fill='tozeroy',
                fillcolor=hex_to_rgba(theme, 0.15),
                name=headline_label,
                hovertemplate=hover_tpl
            ))
            fig_l.add_hline(y=avg, line_dash='dash',
                            line_color='gray', opacity=0.6,
                            annotation_text=f"場均 {avg:.1f}")
            fig_l.update_layout(
                xaxis_title='場次', yaxis_title=headline_label,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0.02)',
                height=max(220, 60*len(relevant_stats)),
                margin=dict(l=20,r=20,t=40,b=40),
                xaxis=dict(gridcolor='rgba(0,0,0,0.08)'),
                yaxis=dict(gridcolor='rgba(0,0,0,0.08)')
            )
            st.plotly_chart(fig_l, width='stretch')

    # ── 位置核心指標卡片 ────────────────────────────────────
    st.subheader(f"🎯 {pos} 核心數據")
    st.caption("每局平均" if HAS_V2 else "場均")
    key_stats = POS_KEY_STATS.get(pos, STAT_COLS)
    kc = st.columns(len(key_stats))
    for i, stat in enumerate(key_stats):
        per_set_col = f'{stat}_每局'
        if HAS_V2 and per_set_col in row.index:
            val = f"{row[per_set_col]:.2f}"
            label = f"{STAT_LABELS[stat]}（每局）"
        else:
            val = f"{row[f'場均{stat}']}"
            label = f"場均{STAT_LABELS[stat]}"
        kc[i].metric(
            label, val,
            f"位置前{int(row.get(f'{stat}_位置百分位',0))}%"
        )

    # ── 得分結構比例（自由球員不顯示，因為沒得分結構）────────
    if pos != '自由球員':
        st.subheader("🥧 得分來源結構")
        st.caption("這位球員的得分中，強攻 / 攔網 / 發球各佔多少比例")
        struct_data = pd.DataFrame({
            '類型': ['強攻得分','攔網得分','發球得分'],
            '比例': [row['結構_強攻%'], row['結構_攔網%'], row['結構_發球%']]
        })
        fig_struct = px.pie(
            struct_data, values='比例', names='類型', hole=0.45,
            color_discrete_sequence=[theme, hex_to_rgba(theme,0.6), hex_to_rgba(theme,0.3)]
        )
        fig_struct.update_traces(textinfo='label+percent')
        fig_struct.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', height=320,
            margin=dict(l=20,r=20,t=10,b=10), showlegend=False
        )
        st.plotly_chart(fig_struct, width='stretch')
    else:
        st.info("💡 自由球員不參與攻擊／發球，主要評估接發與防守表現")

# ============================================================
# 頁面 2：球隊總覽
# ============================================================
elif page == "球隊總覽":
    st.title(f"🏆 {selected_team} 球隊總覽")
    if selected_position != '全部位置':
        st.caption(f"目前篩選位置：{selected_position}")

    team_df = season_df[season_df['球隊']==selected_team].copy()
    if selected_position != '全部位置':
        team_df = team_df[team_df['位置中文']==selected_position]

    if team_df.empty:
        st.warning("此篩選條件下無球員數據")
        st.stop()

    # ── 依位置篩選的逐場數據 ────────────────────────────────
    pos_match_df = match_df[match_df['有上場']]
    if selected_position != '全部位置':
        pos_match_df = pos_match_df[pos_match_df['位置中文']==selected_position]
        scope_label = f"「{selected_position}」"
    else:
        scope_label = "全隊"

    # v2 才有局數，用每局平均取代場均
    use_per_set = HAS_V2 and '總局數' in pos_match_df.columns and pos_match_df['總局數'].notna().any()
    metric_label = "每局平均" if use_per_set else "場均"

    # ── 球隊數據 vs 聯盟平均 ────────────────────────────────
    st.subheader(f"⚔️ {scope_label}{metric_label}數據 vs 聯盟平均")
    if use_per_set:
        st.caption(f"以「每局平均」計算（消除不同場次局數差異），比「場均」更公平。"
                   + (f"僅計算「{selected_position}」球員的貢獻。" if selected_position!='全部位置' else ""))
    else:
        st.caption(f"{scope_label}球員「場均」表現總和，已校正場次數差異，可直接公平比較")

    league_avg = {}
    team_avg = {}
    has_data = True

    for col in STAT_COLS:
        if use_per_set:
            # 每局平均：每場比賽加總後除以局數，再取平均
            grp = pos_match_df.groupby(['球隊','match_id']).agg(
                col_sum=(col,'sum'),
                sets=('總局數','first')
            ).reset_index()
            grp['per_set'] = grp['col_sum'] / grp['sets'].replace(0,1)
            if grp.empty:
                has_data = False; break
            league_avg[col] = grp['per_set'].mean()
            team_subset = grp[grp['球隊']==selected_team]
            team_avg[col] = team_subset['per_set'].mean() if not team_subset.empty else 0
        else:
            per_match = pos_match_df.groupby(['球隊','match_id'])[col].sum().reset_index()
            if per_match.empty:
                has_data = False; break
            league_avg[col] = per_match[col].mean()
            team_subset = per_match[per_match['球隊']==selected_team]
            team_avg[col] = team_subset[col].mean() if not team_subset.empty else 0

    if not has_data:
        st.info("此篩選條件下無數據")
    else:
        cols_disp = st.columns(6)
        for i, col in enumerate(STAT_COLS):
            diff = team_avg[col] - league_avg[col]
            cols_disp[i].metric(
                STAT_LABELS[col],
                f"{team_avg[col]:.2f}" if use_per_set else f"{team_avg[col]:.1f}",
                f"{diff:+.2f} vs 聯盟均" if use_per_set else f"{diff:+.1f} vs 聯盟均",
                delta_color="normal"
            )

    st.divider()

    # ── 六個獨立小圖 ────────────────────────────────────────
    st.subheader(f"📊 各項數據 — 全聯盟逐項比較（{scope_label}{metric_label}，獨立刻度）")
    st.caption("每個項目用自己的刻度，避免大數據掩蓋小數據的差距")

    if use_per_set:
        # 每局平均版本
        grp_all = pos_match_df.groupby(['球隊','match_id']).agg(
            **{col: (col,'sum') for col in STAT_COLS},
            sets=('總局數','first')
        ).reset_index()
        for col in STAT_COLS:
            grp_all[col] = grp_all[col] / grp_all['sets'].replace(0,1)
        team_match_avg = grp_all.groupby('球隊')[STAT_COLS].mean().reset_index()
    else:
        team_match_avg = (pos_match_df
                          .groupby(['球隊','match_id'])[STAT_COLS].sum()
                          .reset_index()
                          .groupby('球隊')[STAT_COLS].mean()
                          .reset_index())

    if team_match_avg.empty:
        st.info("此篩選條件下無數據")
    else:
        if selected_position != '全部位置':
            display_cols = POS_PERCENTILE_STATS.get(selected_position, STAT_COLS)
        else:
            display_cols = STAT_COLS

        cols3 = st.columns(3)
        for i, col in enumerate(display_cols):
            with cols3[i % 3]:
                sorted_teams = team_match_avg.sort_values(col, ascending=True)
                colors = [TEAM_COLORS[t] if t==selected_team else '#D0D0D0'
                         for t in sorted_teams['球隊']]
                fig_s = go.Figure(go.Bar(
                    x=sorted_teams[col], y=sorted_teams['球隊'],
                    orientation='h', marker_color=colors,
                    text=[f'{v:.1f}' for v in sorted_teams[col]],
                    textposition='outside'
                ))
                fig_s.update_layout(
                    title=f"{STAT_LABELS[col]}（場均）",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                    height=220, margin=dict(l=10,r=40,t=40,b=20),
                    xaxis=dict(gridcolor='rgba(0,0,0,0.08)')
                )
                st.plotly_chart(fig_s, width='stretch')

    st.divider()

    # ── 球員貢獻佔比（依位置切換指標）──────────────────────
    pie_source = season_df[season_df['球隊']==selected_team]
    if selected_position != '全部位置':
        pie_source = pie_source[pie_source['位置中文']==selected_position]

    if selected_position == '自由球員':
        # 自由球員不以得分衡量，改用「接發+防守」總量
        pie_source = pie_source.copy()
        pie_source['防守貢獻量'] = pie_source['接發'] + pie_source['防守']
        pie_metric = '防守貢獻量'
        pie_title = "🥧 隊內接發+防守貢獻佔比"
        pie_caption = "自由球員不參與得分，改以「接發+防守」總量衡量隊內貢獻比例"
    elif selected_position == '舉球員':
        pie_metric = '舉球'
        pie_title = "🥧 隊內舉球量佔比"
        pie_caption = "舉球員的核心職責是舉球，以舉球總量衡量隊內貢獻比例"
    else:
        pie_metric = '總得分'
        pie_title = "🥧 隊內得分佔比"
        pie_caption = "每位球員的總得分佔全隊（或該位置）得分的比例 — 看出球隊依賴誰"

    st.subheader(pie_title)
    st.caption(pie_caption)
    pie_df = pie_source[pie_source[pie_metric]>0].sort_values(pie_metric, ascending=False)

    if pie_df.empty:
        st.info("此分類下無有效數據可呈現")
    else:
        fig_pie = px.pie(
            pie_df, values=pie_metric, names='球員名稱', hole=0.4,
            color_discrete_sequence=px.colors.sequential.Greens_r if selected_team=='臺中連莊'
                                    else px.colors.sequential.Blues_r if selected_team=='台鋼天鷹'
                                    else px.colors.sequential.RdPu_r if selected_team=='桃園雲豹飛將'
                                    else px.colors.sequential.Oranges_r
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=420,
                              margin=dict(l=20,r=20,t=10,b=10))
        st.plotly_chart(fig_pie, width='stretch')

    # ── 球員名單卡片：點擊直接進入個人分析 ────────────────────
    st.divider()
    st.subheader("👥 球員名單")
    st.caption("依位置分組，點擊「查看」進入該球員的詳細分析")

    pos_order = list(POS_KEY_STATS.keys())
    for pos in pos_order:
        pos_players = team_df[team_df['位置中文']==pos].sort_values('總得分', ascending=False)
        if pos_players.empty:
            continue
        st.markdown(f"**{pos}**")
        ncols = min(4, len(pos_players))
        cols_p = st.columns(ncols)
        for idx, (_, p) in enumerate(pos_players.iterrows()):
            col = cols_p[idx % ncols]
            with col:
                hl_label = p['headline_label'].replace('場均','')
                st.markdown(f"""
                <div style="border:1px solid {theme}66; border-radius:10px;
                            padding:10px 12px; margin-bottom:4px; min-height:88px;
                            background:rgba(255,255,255,0.6);">
                  <div style="font-weight:700; font-size:14px;">{p['球員名稱']}</div>
                  <div style="font-size:11px; color:#888; margin:2px 0;">{p['球員角色']}</div>
                  <div style="font-size:12px; color:{theme}; font-weight:700;">
                    {hl_label} {p['headline_value']:.1f}
                  </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看 →", key=f"go_p_{selected_team}_{p['球員名稱']}", use_container_width=True):
                    goto(page='球員個人分析', team=selected_team, position=pos, player=p['球員名稱'])

    # ── 球員數據表 ──────────────────────────────────────────
    st.divider()
    st.subheader("📋 完整數據表")
    show_cols = ['球員名稱','位置中文','球員角色','有效出場',
                 '場均攻擊得分','場均攔網得分','場均發球得分',
                 '場均接發','場均防守','場均舉球','總得分','總得分佔比%']
    st.dataframe(
        team_df[show_cols].rename(columns={'球員名稱':'球員','位置中文':'位置'})
                          .sort_values('總得分',ascending=False)
                          .reset_index(drop=True),
        width='stretch', height=400
    )

# ============================================================
# 頁面 3：位置排行榜（取代原全聯盟排行）
# ============================================================
elif page == "位置排行榜":
    st.title("🏅 位置排行榜")
    st.caption("依位置分類，僅顯示該位置真正重要的指標（至少出場 5 場）")
    if selected_player:
        st.caption(f"⭐ 標記球員「{selected_player}」若進入 TOP10，會以金色外框標示")

    qualified = season_df[season_df['有效出場']>=5].copy()

    pos_tabs = st.tabs(list(POS_KEY_STATS.keys()))

    for i, pos in enumerate(POS_KEY_STATS.keys()):
        with pos_tabs[i]:
            pos_df = qualified[qualified['位置中文']==pos]
            key_stats = POS_KEY_STATS[pos]

            if pos_df.empty:
                st.info("此位置暫無符合條件的球員")
                continue

            st.markdown(f"#### {pos} — 核心指標排行")

            sub_cols = st.columns(len(key_stats))
            for j, stat in enumerate(key_stats):
                avg_col = f'場均{stat}'
                with sub_cols[j]:
                    top10 = pos_df.nlargest(10, avg_col).reset_index(drop=True)
                    colors = [TEAM_COLORS.get(t,'#888888') for t in top10['球隊']]
                    # 標記球員：金色外框凸顯
                    line_colors = ['#FFD700' if n==selected_player else 'rgba(0,0,0,0)'
                                   for n in top10['球員名稱']]
                    line_widths = [3 if n==selected_player else 0 for n in top10['球員名稱']]
                    labels = [f"⭐ {n}" if n==selected_player else n for n in top10['球員名稱']]
                    fig = go.Figure(go.Bar(
                        x=top10[avg_col], y=labels,
                        orientation='h',
                        marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                        text=top10[avg_col], textposition='outside',
                        hovertemplate='%{y}：場均%{x}<extra></extra>'
                    ))
                    fig.update_layout(
                        title=f"場均{STAT_LABELS[stat]} TOP10",
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                        height=380, yaxis=dict(autorange='reversed'),
                        margin=dict(l=10,r=50,t=40,b=20),
                        xaxis=dict(gridcolor='rgba(0,0,0,0.08)')
                    )
                    st.plotly_chart(fig, width='stretch')

            st.divider()
            st.markdown(f"#### {pos} 全部球員數據")
            show_cols = ['球員名稱','球隊','球員角色','有效出場'] + [f'場均{s}' for s in key_stats] + ['場均總得分']
            table_df = (pos_df[show_cols].rename(columns={'球員名稱':'球員'})
                                 .sort_values(f'場均{key_stats[0]}', ascending=False)
                                 .reset_index(drop=True))
            if selected_player:
                table_df['球員'] = table_df['球員'].apply(
                    lambda n: f"⭐ {n}" if n==selected_player else n)
            st.dataframe(table_df, width='stretch', height=350)

# ============================================================
# 頁面 4：跨隊比較
# ============================================================
elif page == "跨隊比較":
    st.title("⚡ 四隊戰力比較")
    st.caption("所有數據皆為「場均」，已校正場次數差異")
    st.caption(f"⭐ 目前標記球隊：**{selected_team}**（會在圖中以金色外框／加粗線條標示）")

    team_match_avg = (match_df[match_df['有上場']]
                      .groupby(['球隊','match_id'])[STAT_COLS].sum()
                      .reset_index()
                      .groupby('球隊')[STAT_COLS].mean()
                      .reset_index())

    st.subheader("📊 六大項目場均對決")
    cols3 = st.columns(3)
    for i, col in enumerate(STAT_COLS):
        with cols3[i % 3]:
            sorted_teams = team_match_avg.sort_values(col, ascending=True)
            colors = [TEAM_COLORS[t] for t in sorted_teams['球隊']]
            line_colors = ['#FFD700' if t==selected_team else 'rgba(0,0,0,0)'
                           for t in sorted_teams['球隊']]
            line_widths = [4 if t==selected_team else 0 for t in sorted_teams['球隊']]
            y_labels = [f"⭐ {t}" if t==selected_team else t for t in sorted_teams['球隊']]
            fig_s = go.Figure(go.Bar(
                x=sorted_teams[col], y=y_labels,
                orientation='h',
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=[f'{v:.1f}' for v in sorted_teams[col]],
                textposition='outside'
            ))
            fig_s.update_layout(
                title=f"{STAT_LABELS[col]}（場均）",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                height=240, margin=dict(l=10,r=40,t=40,b=20),
                xaxis=dict(gridcolor='rgba(0,0,0,0.08)')
            )
            st.plotly_chart(fig_s, width='stretch')

    st.divider()

    st.subheader("⬡ 球隊綜合輪廓（聯盟內排名校正）")
    st.caption("以聯盟最大值=100% 校正後比較形狀")

    labels = [STAT_LABELS[c] for c in STAT_COLS]
    fig_cmp = go.Figure()
    for team, color in TEAM_COLORS.items():
        t_row = team_match_avg[team_match_avg['球隊']==team]
        if t_row.empty: continue
        vals = []
        for c in STAT_COLS:
            max_v = team_match_avg[c].max()
            vals.append((t_row[c].values[0]/max_v*100) if max_v>0 else 0)
        is_selected = (team == selected_team)
        fig_cmp.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=labels+[labels[0]],
            fill='toself', name=f"⭐ {team}" if is_selected else team,
            fillcolor=hex_to_rgba(color, 0.35 if is_selected else 0.12),
            line=dict(color=color, width=4 if is_selected else 1.5,
                      dash='solid' if is_selected else 'dot'),
        ))
    fig_cmp.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        paper_bgcolor='rgba(0,0,0,0)',
        height=480, legend=dict(orientation='h', y=-0.1),
        margin=dict(l=80,r=80,t=30,b=60)
    )
    st.plotly_chart(fig_cmp, width='stretch')

    st.divider()

    st.subheader("🥧 各隊得分結構（強攻/攔網/發球）")
    cols4 = st.columns(4)
    for i, (team, color) in enumerate(TEAM_COLORS.items()):
        t_df = season_df[season_df['球隊']==team]
        atk = t_df['攻擊得分'].sum()
        blk = t_df['攔網得分'].sum()
        srv = t_df['發球得分'].sum()
        struct = pd.DataFrame({
            '類型':['強攻','攔網','發球'],
            '值':[atk,blk,srv]
        })
        fig_p = px.pie(struct, values='值', names='類型',
                       title=team, hole=0.35,
                       color_discrete_sequence=[color, hex_to_rgba(color,0.6), hex_to_rgba(color,0.3)])
        fig_p.update_traces(textinfo='percent', textposition='inside')
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                            height=280, margin=dict(l=10,r=10,t=40,b=10),
                            showlegend=False)
        cols4[i].plotly_chart(fig_p, width='stretch')


# ============================================================
# 球探中心（整合球探評估 + 對戰分析）
# ============================================================
elif page == "球探中心":
    st.title("🎯 球探中心")
    st.caption("整合效率排名、趨勢、穩定度、對戰表現，直接回答「這個球員值不值得簽？」")

    if not HAS_V2:
        st.info("完整球探中心需要 v2 數據，部分功能可能受限")

    TEAM_LIST = list(TEAM_COLORS.keys())

    # ── 建立球探核心數據表 ─────────────────────────────────────
    @st.cache_data
    def build_scout_report(_match_df, _season_df):
        active = _match_df[_match_df['有上場']].copy()
        qualified = _season_df[_season_df['有效出場']>=5].copy()

        # 每局得分
        if '總局數' in qualified.columns and pd.to_numeric(qualified['總局數'], errors='coerce').notna().any():
            qualified = qualified.copy()
            qualified['每局得分'] = (qualified['總得分'] / pd.to_numeric(qualified['總局數'], errors='coerce').replace(0,1)).round(2)
        else:
            qualified = qualified.copy()
            qualified['每局得分'] = qualified['場均總得分']

        # 同位置百分位
        qualified = qualified.copy()
        qualified['位置百分位'] = 0.0
        for pos in qualified['位置中文'].unique():
            mask = qualified['位置中文']==pos
            qualified.loc[mask,'位置百分位'] = (
                qualified.loc[mask,'每局得分'].rank(pct=True)*100
            ).round(0)

        # 趨勢：season_df 已經從 build_half_season_trend 合併了趨勢欄位
        # 直接用，不重複計算，避免欄位衝突
        has_trend = '趨勢' in qualified.columns and '趨勢變化' in qualified.columns
        if not has_trend:
            # fallback：自行計算
            sorted_ids = sorted(_match_df['match_id'].unique())
            mid_pt = len(sorted_ids)//2
            first_half = set(sorted_ids[:mid_pt])
            active2 = active.copy()
            active2['期間'] = active2['match_id'].apply(
                lambda x: '前半季' if x in first_half else '後半季')
            stat_col2 = '總得分_每局' if '總得分_每局' in active2.columns else 'headline_stat'
            trend_raw = active2.groupby(['球員名稱','期間'])[stat_col2].mean().unstack().fillna(0)
            if '前半季' not in trend_raw.columns: trend_raw['前半季'] = 0.0
            if '後半季' not in trend_raw.columns: trend_raw['後半季'] = 0.0
            trend_raw['趨勢變化'] = (trend_raw['後半季'] - trend_raw['前半季']).round(2)
            trend_raw['趨勢'] = trend_raw['趨勢變化'].apply(
                lambda v: '📈 上升' if v>=1.0 else ('📉 下滑' if v<=-1.0 else '➡️ 持平'))
            trend_df_local = trend_raw[['趨勢','趨勢變化']].reset_index()
            qualified = qualified.merge(trend_df_local, on='球員名稱', how='left')

        # 穩定度
        stat_col = '總得分_每局' if '總得分_每局' in active.columns else 'headline_stat'
        stab = active.groupby('球員名稱')[stat_col].agg(['mean','std']).reset_index()
        stab.columns = ['球員名稱','_mean','_std']
        stab['cv'] = (stab['_std'] / stab['_mean'].replace(0,1)).round(2)
        stab['穩定度'] = stab['cv'].apply(
            lambda x: '🟢 穩定' if x<0.5 else ('🟡 中等' if x<0.8 else '🔴 起伏大'))

        # 合併穩定度
        report = qualified.merge(stab[['球員名稱','穩定度','cv']], on='球員名稱', how='left')

        # 確保欄位存在
        if '趨勢' not in report.columns: report['趨勢'] = '➡️ 持平'
        if '趨勢變化' not in report.columns: report['趨勢變化'] = 0.0
        if '穩定度' not in report.columns: report['穩定度'] = '🟡 中等'

        report['趨勢'] = report['趨勢'].fillna('➡️ 持平')
        report['趨勢變化'] = report['趨勢變化'].fillna(0.0)
        report['穩定度'] = report['穩定度'].fillna('🟡 中等')

        # 球探建議
        def rec(row):
            pct = float(row.get('位置百分位') or 0)
            t = str(row.get('趨勢') or '')
            s = str(row.get('穩定度') or '')
            if pct>=80 and '上升' in t and '穩定' in s: return '⭐ 強力推薦'
            if pct>=70 and ('上升' in t or '穩定' in s): return '✅ 值得簽下'
            if pct>=55 and '上升' in t: return '👀 潛力觀察'
            if pct>=70 and '下滑' in t: return '⚠️ 謹慎評估'
            if pct<35: return '❌ 暫不考慮'
            return '📋 一般水準'

        report['球探建議'] = report.apply(rec, axis=1)
        return report

    scout_df = build_scout_report(match_df, season_df)

    # 位置篩選
    pos_sel = selected_position if selected_position != '全部位置' else None
    if pos_sel:
        scout_view = scout_df[scout_df['位置中文']==pos_sel].copy()
    else:
        scout_view = scout_df.copy()

    # ── Tab 結構 ───────────────────────────────────────────────
    tab_list = ["📋 球探快速清單", "🎯 價值四象限", "📈 趨勢與穩定度"]
    if HAS_V2:
        tab_list.append("⚔️ 對手效率")
        tab_list.append("🏆 勝負關鍵")
    tabs = st.tabs(tab_list)

    # ── Tab 1：球探快速清單 ──────────────────────────────────
    with tabs[0]:
        st.subheader("📋 球探快速清單")
        st.caption("整合效率、趨勢、穩定度，直接給出建議。適合快速掃視「這季有哪些球員值得關注」。")

        # 建議分類按鈕
        all_recs = ['全部', '⭐ 強力推薦', '✅ 值得簽下', '👀 潛力觀察', '⚠️ 謹慎評估', '❌ 暫不考慮']
        rec_filter = st.radio("篩選建議", all_recs, horizontal=True, key='scout_rec_filter')

        show = scout_view.copy()
        if rec_filter != '全部':
            show = show[show['球探建議']==rec_filter]

        if show.empty:
            st.info("此篩選條件下無球員")
        else:
            # 彩色卡片
            rec_colors = {
                '⭐ 強力推薦': '#1B5E20',
                '✅ 值得簽下': '#2E7D32',
                '👀 潛力觀察': '#1565C0',
                '⚠️ 謹慎評估': '#E65100',
                '❌ 暫不考慮': '#757575',
                '📋 一般水準': '#9E9E9E',
            }
            show_sorted = show.sort_values('位置百分位', ascending=False).reset_index(drop=True)
            cols = st.columns(3)
            for i, (_, r) in enumerate(show_sorted.iterrows()):
                team_color = TEAM_COLORS.get(r['球隊'], '#888')
                rec_color = rec_colors.get(r['球探建議'], '#888')
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="border:1.5px solid {team_color}44; border-radius:12px;
                                padding:12px 14px; margin-bottom:10px;
                                background:rgba(255,255,255,0.7);">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                          <div style="font-size:15px;font-weight:700;">{r['球員名稱']}</div>
                          <div style="font-size:11px;color:#888;">{r['球隊']} · {r['位置中文']}</div>
                        </div>
                        <div style="background:{rec_color}; color:white; font-size:11px;
                                    padding:3px 8px; border-radius:20px; white-space:nowrap;">
                          {r['球探建議']}
                        </div>
                      </div>
                      <div style="margin-top:8px; display:flex; gap:12px; font-size:12px;">
                        <span>每局 <b style="color:{team_color};">{r['每局得分']:.2f}</b></span>
                        <span>位置前 <b>{int(r['位置百分位'])}%</b></span>
                        <span>{r.get('趨勢','')}</span>
                        <span>{r.get('穩定度','')}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("詳細 →", key=f"scout_goto_{r['球員名稱']}", use_container_width=True):
                        pos = r['位置中文']
                        goto(page='球員個人分析', team=r['球隊'], position=pos, player=r['球員名稱'])

    # ── Tab 2：價值四象限 ────────────────────────────────────
    with tabs[1]:
        x_label = POS_HEADLINE_LABEL.get(pos_sel, '場均總得分') if pos_sel else '代表性數據（依位置切換）'
        st.subheader(f"🎯 價值四象限")
        st.caption(f"橫軸＝{x_label}（知名度），縱軸＝同位置效率百分位。左上＝被低估潛力股，右上＝續約必爭明星。")
        if not pos_sel:
            st.caption("⚠️ 建議先選位置，避免不同位置的代表性數據混在一起比較。")

        q_df = scout_view[scout_view['有效出場']>=5].copy()
        if q_df.empty:
            st.info("無數據")
        else:
            x_med = q_df['headline_value'].median()
            y_med = q_df['綜合位置百分位'].median()
            gems_mask = (q_df['headline_value']<x_med) & (q_df['綜合位置百分位']>y_med)
            top_eff = q_df.nlargest(5,'綜合位置百分位')['球員名稱'].tolist()
            top_known = q_df.nlargest(5,'headline_value')['球員名稱'].tolist()
            label_names = set(q_df[gems_mask]['球員名稱']) | set(top_eff) | set(top_known)
            if selected_player: label_names.add(selected_player)

            fig_q = go.Figure()
            for team, color in TEAM_COLORS.items():
                t_df = q_df[q_df['球隊']==team]
                if t_df.empty: continue
                text_labels = [n if n in label_names else '' for n in t_df['球員名稱']]
                fig_q.add_trace(go.Scatter(
                    x=t_df['headline_value'], y=t_df['綜合位置百分位'],
                    mode='markers+text', text=text_labels, textposition='top center',
                    textfont=dict(size=10),
                    marker=dict(size=12, color=color, line=dict(width=1, color='white')),
                    name=team,
                    customdata=t_df[['球員名稱','位置中文','球探建議','有效出場','headline_label']],
                    hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[4]}：%{x:.1f}'
                                  '<br>位置百分位：%{y:.0f}th<br>建議：%{customdata[2]}<extra></extra>'
                ))
            if selected_player and selected_player in q_df['球員名稱'].values:
                hl = q_df[q_df['球員名稱']==selected_player].iloc[0]
                fig_q.add_trace(go.Scatter(
                    x=[hl['headline_value']], y=[hl['綜合位置百分位']],
                    mode='markers+text', text=[f"⭐ {selected_player}"],
                    textposition='top center',
                    textfont=dict(size=14, color='#B8860B', family='Arial Black'),
                    marker=dict(size=22, color='rgba(255,215,0,0.35)',
                                line=dict(width=3, color='#FFD700'), symbol='star'),
                    showlegend=False
                ))
            fig_q.add_vline(x=x_med, line_dash='dash', line_color='gray', opacity=0.5)
            fig_q.add_hline(y=y_med, line_dash='dash', line_color='gray', opacity=0.5)
            x_max = q_df['headline_value'].max()*1.1
            fig_q.add_annotation(x=x_med*0.3, y=95, text="💎 被低估潛力股", showarrow=False,
                                 font=dict(size=13,color='#2E7D32'), bgcolor='rgba(46,125,50,0.1)')
            fig_q.add_annotation(x=x_max*0.85, y=95, text="⭐ 續約必爭明星", showarrow=False,
                                 font=dict(size=13,color='#C0392B'), bgcolor='rgba(192,57,43,0.1)')
            fig_q.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                height=520, margin=dict(l=20,r=20,t=20,b=40),
                xaxis=dict(gridcolor='rgba(0,0,0,0.08)', title=x_label),
                yaxis=dict(gridcolor='rgba(0,0,0,0.08)', range=[-5,105], title='同位置效率百分位'),
                legend=dict(orientation='h', y=-0.12)
            )
            st.plotly_chart(fig_q, width='stretch')

    # ── Tab 3：趨勢與穩定度 ─────────────────────────────────
    with tabs[2]:
        st.subheader("📈 趨勢與穩定度")

        t_df = scout_view[scout_view['有效出場']>=5].copy()
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**上升趨勢球員（後半季比前半季進步）**")
            rising = t_df[t_df['趨勢']=='📈 上升'].sort_values('趨勢變化',ascending=False)
            if rising.empty:
                st.info("無")
            else:
                for _, r in rising.iterrows():
                    color = TEAM_COLORS.get(r['球隊'],'#888')
                    st.markdown(f"<span style='color:{color};font-weight:700;'>{r['球員名稱']}</span>"
                               f"（{r['球隊'][:2]}）+{r['趨勢變化']:.1f}/局　{r.get('穩定度','')}",
                               unsafe_allow_html=True)

        with c2:
            st.markdown("**下滑警示球員（後半季比前半季退步）**")
            falling = t_df[t_df['趨勢']=='📉 下滑'].sort_values('趨勢變化')
            if falling.empty:
                st.info("無")
            else:
                for _, r in falling.iterrows():
                    color = TEAM_COLORS.get(r['球隊'],'#888')
                    st.markdown(f"<span style='color:{color};font-weight:700;'>{r['球員名稱']}</span>"
                               f"（{r['球隊'][:2]}）{r['趨勢變化']:.1f}/局　{r.get('穩定度','')}",
                               unsafe_allow_html=True)

    # ── Tab 4：對手效率（v2 限定）───────────────────────────
    if HAS_V2:
        with tabs[3]:
            st.subheader("⚔️ 對手效率")
            st.caption("選一支對手球隊，看各球員打這隊時的每局效率排行。教練/球探參考用。")

            opponent_sel = st.selectbox("選擇對手球隊", TEAM_LIST, key='scout_opp')
            active_v2 = match_df[
                match_df['有上場'] &
                match_df['對手'].notna() &
                (match_df['對手'].astype(str)!='0')
            ].copy()
            if pos_sel:
                active_v2 = active_v2[active_v2['位置中文']==pos_sel]

            vs_opp = active_v2[active_v2['對手']==opponent_sel].groupby(
                ['球員名稱','球隊','位置中文'])['總得分_每局'].agg(
                每局得分=('mean'), 對戰場次=('count')).reset_index()
            vs_opp['每局得分'] = vs_opp['每局得分'].round(2)
            vs_opp = vs_opp[vs_opp['對戰場次']>=3].sort_values('每局得分',ascending=False)

            if vs_opp.empty:
                st.info("對戰場次不足")
            else:
                colors = [TEAM_COLORS.get(t,'#888') for t in vs_opp['球隊']]
                labels = vs_opp['球員名稱']+'（'+vs_opp['球隊'].str[:2]+'·'+vs_opp['位置中文']+'）'
                fig_opp = go.Figure(go.Bar(
                    x=vs_opp['每局得分'], y=labels, orientation='h',
                    marker_color=colors,
                    text=[f"{v:.2f}" for v in vs_opp['每局得分']],
                    textposition='outside',
                    hovertemplate='%{y}：%{x:.2f}/局<extra></extra>'
                ))
                fig_opp.update_layout(
                    title=f"打「{opponent_sel}」每局得分排行",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                    height=max(300, 30*len(vs_opp)),
                    margin=dict(l=20,r=60,t=40,b=20),
                    yaxis=dict(autorange='reversed'),
                    xaxis=dict(gridcolor='rgba(0,0,0,0.08)')
                )
                st.plotly_chart(fig_opp, width='stretch')

        # ── Tab 5：勝負關鍵 ───────────────────────────────────
        with tabs[4]:
            st.subheader("🏆 勝負關鍵球員")
            st.caption("贏球時和輸球時的每局表現差距越大，代表這個球員對球隊勝負影響越直接。")

            if win_loss_df is not None:
                wl = win_loss_df.copy()
                if pos_sel:
                    wl = wl[wl['位置中文']==pos_sel]
                wl = wl[wl['有效出場']>=5].sort_values('差距',ascending=False)

                if not wl.empty:
                    fig_wl = go.Figure()
                    for _, r in wl.iterrows():
                        color = TEAM_COLORS.get(r['球隊'],'#888')
                        label = f"{r['球員名稱']}（{r['球隊'][:2]}）"
                        fig_wl.add_trace(go.Scatter(
                            x=[r['輸球每局均'], r['贏球每局均']], y=[label, label],
                            mode='lines', line=dict(color=color, width=2.5),
                            showlegend=False, hoverinfo='skip'
                        ))
                        fig_wl.add_trace(go.Scatter(
                            x=[r['輸球每局均']], y=[label], mode='markers',
                            marker=dict(size=10, color='white', line=dict(width=2,color=color)),
                            showlegend=False,
                            hovertemplate=f"{label} 輸球：{r['輸球每局均']:.2f}/局<extra></extra>"
                        ))
                        fig_wl.add_trace(go.Scatter(
                            x=[r['贏球每局均']], y=[label], mode='markers',
                            marker=dict(size=10, color=color),
                            showlegend=False,
                            hovertemplate=f"{label} 贏球：{r['贏球每局均']:.2f}/局<extra></extra>"
                        ))
                    fig_wl.update_layout(
                        title="○ 輸球時　● 贏球時（線段越長＝影響勝負越關鍵）",
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)',
                        height=max(400, 28*len(wl)),
                        margin=dict(l=20,r=20,t=40,b=20),
                        yaxis=dict(autorange='reversed'),
                        xaxis=dict(gridcolor='rgba(0,0,0,0.08)', title='每局得分')
                    )
                    st.plotly_chart(fig_wl, width='stretch')