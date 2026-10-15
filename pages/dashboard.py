import sys
import os
import time

import pandas as pd
import requests
import streamlit as st

# 让 pages 目录下的页面能 import 到项目根目录的 core / charts 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import API_KEY, CITY_DICT, FOCUS_CITIES, API_BASE, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button
from charts import simple_bar, pie_chart

st.set_page_config(page_title="气象数据大屏", layout="wide")
apply_theme()
require_login()
ensure_api_key()  # 登录守卫：未登录访问此页会被拦回登录界面
# ================= 公共侧边栏 =================
# 隐藏默认英文菜单
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# 中文导航菜单
with st.sidebar:
    st.header("🧭 系统导航")
    st.page_link("app.py", label="🏠 天气主页", icon="🏠")
    st.page_link("pages/Now.py", label="🌡️ 实况天气", icon="🌡️")
    st.page_link("pages/Life.py", label="💡 生活指数", icon="💡")
    st.page_link("pages/Compare.py", label="📊 城市对比", icon="📊")
    st.page_link("pages/HeatMap.py", label="🗺️ 天气地图", icon="🗺️")
    st.page_link("pages/dashboard.py", label="📈 数据大屏", icon="📈")

logout_button()  # 侧边栏底部「退出登录」
# ==============================================
st.title("📊 全国气象数据可视化大屏")


# ================= 数据获取（按城市单独缓存，失败自动补查） =================
class _CityFetchFail(Exception):
    """单个城市获取失败（故意抛异常：st.cache_data 不缓存异常，
    这样失败的城市下次访问会自动重新查询，直到补齐）。"""


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_one_city(name, pinyin, api_key):
    """查询单个城市实况。成功结果缓存 30 分钟；失败抛异常（不缓存，下次自动重试）。

    根源修复：以前是 5 个城市"打包缓存"，1 个失败整个失败结果被冻结 30 分钟，
    期间刷新也不会补查失败的城市。现在按城市单独记账：
    - 成功的城市 30 分钟内不再请求（省额度）
    - 失败的城市不进缓存，下次访问自动重试补齐
    """
    url = (
        f"{API_BASE}/now.json?key={api_key}&location={pinyin}"
        f"&language=zh-Hans&unit=c"
    )
    last_err = ""
    for attempt in range(4):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            res = resp.json()
            if "results" in res:
                now = res["results"][0]["now"]
                return {
                    "temperature": now.get("temperature"),
                    "text": now.get("text", "未知"),
                }
            # 心知免费版限流常见返回：403 或 status 字段带错误
            time.sleep(min(3 * (attempt + 1), 8))  # 3s -> 6s -> 8s 递增等待
        except Exception as e:
            last_err = str(e)
            time.sleep(min(3 * (attempt + 1), 8))
    raise _CityFetchFail(f"{name}: {last_err or '重试后仍失败'}")


def fetch_cities_now(names, api_key):
    """逐个城市获取实况（带各自缓存），返回 ({城市名: 数据}, [失败城市名])。"""
    result = {}
    errors = []
    for name in names:
        pinyin = CITY_DICT.get(name)
        if not pinyin:
            continue
        try:
            result[name] = _fetch_one_city(name, pinyin, api_key)
        except _CityFetchFail:
            errors.append(name)
        time.sleep(0.5)  # 请求间隔，防限流
    return result, errors


with st.spinner(f"正在获取全国 {len(FOCUS_CITIES)} 个主要城市的气象数据（首次约需 20 秒，之后 30 分钟内秒开）..."):
    now_map, fetch_errors = fetch_cities_now(FOCUS_CITIES, API_KEY)

if fetch_errors and not now_map:
    st.error(
        "获取数据失败，请检查 API Key 是否有效，或是否已超出调用频率限制"
        "（心知天气免费版限额较低，稍等几分钟后重试）。"
    )
    st.stop()

if fetch_errors:
    st.warning(
        f"⚠️ 以下城市本次获取失败已跳过：{'、'.join(fetch_errors)}。"
        f"**刷新页面会自动重试补齐**，全部成功后 30 分钟内不再重复请求。"
    )

# ================= 顶部：4个统计卡片（基于真实数据） =================
sunny = sum(1 for v in now_map.values() if v["text"] in ("晴", "晴天"))
rainy = sum(1 for v in now_map.values() if "雨" in v["text"])
temps = [int(v["temperature"]) for v in now_map.values() if str(v["temperature"]).lstrip("-").isdigit()]
avg_temp = round(sum(temps) / len(temps), 1) if temps else 0

# 最热 / 最冷城市（免费版实况接口不返回风速，故用气温极值作指标）
hottest = max(now_map.items(), key=lambda kv: int(kv[1]["temperature"])) if now_map else None
coldest = min(now_map.items(), key=lambda kv: int(kv[1]["temperature"])) if now_map else None

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="☀️ 晴天城市", value=f"{sunny} / {len(now_map)}")
with col2:
    st.metric(label="🌧️ 雨天城市", value=f"{rainy} / {len(now_map)}")
with col3:
    st.metric(label="🌡️ 平均气温", value=f"{avg_temp} ℃")
with col4:
    if hottest and coldest:
        st.metric(
            label="🔥 最热 / ❄️ 最冷",
            value=f"{hottest[0]} {hottest[1]['temperature']}℃",
            help=f"最冷：{coldest[0]} {coldest[1]['temperature']}℃",
        )
    else:
        st.metric(label="🔥 最热 / ❄️ 最冷", value="--")

if fetch_errors:
    st.caption(
        f"⚠️ 有 {len(fetch_errors)} 个城市本次未取到（{'、'.join(fetch_errors)}），"
        f"刷新页面会自动重试补齐。"
    )

st.markdown("---")

# ================= 中间：气温排行（横向，城市较多时更易读） =================
# 按气温从高到低排序，形成"最热城市排行"
if now_map:
    ranked = sorted(
        ((n, int(v["temperature"])) for n, v in now_map.items()
         if str(v["temperature"]).lstrip("-").isdigit()),
        key=lambda x: x[1],
        reverse=True,
    )
    st.subheader(f"📈 全国主要城市实时气温排行（共 {len(ranked)} 城）")
    simple_bar(
        [n for n, _ in ranked],
        [t for _, t in ranked],
        height=max(320, 22 * len(ranked)),
        x_label="温度(℃)",
        label="当前气温(℃)",
        horizontal=True,
    )
else:
    st.info("暂无城市数据，无法绘制气温对比图。")

st.markdown("---")

# ================= 下方：天气占比 + 城市明细表 =================
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("☁️ 天气状况占比")
    weather_counts = {}
    for v in now_map.values():
        weather_counts[v["text"]] = weather_counts.get(v["text"], 0) + 1

    if weather_counts:
        pie_chart(
            list(weather_counts.keys()),
            list(weather_counts.values()),
            height=max(320, 60 * len(weather_counts)),
        )
    else:
        st.info("暂无天气状况数据。")

with right_col:
    st.subheader("📋 各城市实时天气明细")
    if now_map:
        detail_rows = [
            {
                "城市": n,
                "天气": now_map[n]["text"],
                "气温(℃)": int(now_map[n]["temperature"])
                if str(now_map[n]["temperature"]).lstrip("-").isdigit()
                else "--",
            }
            for n, _ in ranked
        ]
        st.dataframe(
            pd.DataFrame(detail_rows),
            use_container_width=True,
            hide_index=True,
            height=max(320, 38 * len(detail_rows)),
        )
    else:
        st.info("暂无城市明细数据。")

st.markdown("---")
st.caption("数据来源：心知天气")
