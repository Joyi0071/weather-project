import hashlib
import sys
import os
import time
from datetime import date

import pandas as pd
import requests
import streamlit as st

# 让 pages 目录下的页面能 import 到项目根目录的 core / charts 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import (
    API_KEY,
    CITY_DICT,
    FOCUS_CITIES,
    MUST_REAL_CITIES,
    API_BASE,
    REQUEST_TIMEOUT,
    ensure_api_key,
)
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


# ================= 数据获取（真实数据优先，失败用模拟数据兜底） =================
class _CityFetchFail(Exception):
    """单个城市获取失败（故意抛异常：st.cache_data 不缓存异常，
    这样失败的城市下次访问会自动重新查询，直到补齐）。"""


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_one_city(name, pinyin, api_key, retries):
    """查询单个城市实况。成功结果缓存 30 分钟；失败抛异常（不缓存，下次自动重试）。

    - 普通城市重试 2 次，重点城市（无锡）重试 4 次
    - 收到 403 等非 200 响应时直接判失败（多为免费版限流，重试无意义，避免卡住页面）
    """
    url = (
        f"{API_BASE}/now.json?key={api_key}&location={pinyin}"
        f"&language=zh-Hans&unit=c"
    )
    last_err = ""
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                res = resp.json()
                if "results" in res:
                    now = res["results"][0]["now"]
                    return {
                        "temperature": now.get("temperature"),
                        "text": now.get("text", "未知"),
                        "mock": False,
                    }
                last_err = res.get("status", "返回异常")
                break  # 接口正常返回但无数据，重试意义不大
            else:
                last_err = f"HTTP {resp.status_code}"
                break  # 限流/鉴权问题，立即失败转兜底，不拖慢页面
        except Exception as e:
            last_err = str(e)
            time.sleep(1.5)
    raise _CityFetchFail(f"{name}: {last_err or '重试后仍失败'}")


@st.cache_data(ttl=600, show_spinner=False)
def _mock_city(name, today_str):
    """模拟数据兜底：按「城市 + 日期」生成确定性的演示天气（同一天数值固定不乱跳）。

    缓存 10 分钟，10 分钟后会自动重新尝试真实接口，成功即用真实数据替换模拟值。
    气温按月份基准 + 伪随机抖动，天气现象从常见类型中按伪随机选取。
    """
    seed = int(hashlib.md5(f"{name}-{today_str}".encode("utf-8")).hexdigest(), 16)
    month_base = [4, 6, 11, 17, 22, 26, 30, 29, 25, 19, 12, 6]
    temp = month_base[int(today_str[5:7]) - 1] + (seed % 9) - 4
    text = ["晴", "多云", "阴", "小雨", "多云", "晴", "阴", "雷阵雨", "小雨", "中雨"][
        seed % 10
    ]
    return {"temperature": str(temp), "text": text, "mock": True}


def fetch_cities_now(names, api_key):
    """逐个城市获取实况（带各自缓存）。

    返回 ({城市名: 数据}, [必须真实但失败的城市名])。
    - 普通城市失败 → 自动用模拟数据兜底，保证大屏永远有完整数据
    - 无锡等 MUST_REAL_CITIES 失败 → 不兜底，记录下来在页面明确提示
    """
    result = {}
    must_real_errors = []
    today_str = date.today().isoformat()
    for name in names:
        pinyin = CITY_DICT.get(name)
        if not pinyin:
            continue
        retries = 4 if name in MUST_REAL_CITIES else 2
        try:
            result[name] = _fetch_one_city(name, pinyin, api_key, retries)
        except _CityFetchFail:
            if name in MUST_REAL_CITIES:
                must_real_errors.append(name)  # 保证真实：失败不造假
            else:
                result[name] = _mock_city(name, today_str)
        time.sleep(0.4)  # 请求间隔，防限流
    return result, must_real_errors


mock_count_total = len(FOCUS_CITIES) - len(MUST_REAL_CITIES)
with st.spinner(
    f"正在获取全国 {len(FOCUS_CITIES)} 个城市的气象数据"
    f"（真实数据优先，首次约需 30~60 秒，之后 30 分钟内秒开）..."
):
    now_map, fetch_errors = fetch_cities_now(FOCUS_CITIES, API_KEY)

mock_names = [n for n, v in now_map.items() if v.get("mock")]

if fetch_errors:
    st.error(
        f"⚠️ {'、'.join(fetch_errors)} 实况获取失败（该城市保证使用真实数据，不用模拟值代替）。"
        f"**刷新页面会自动重试**，通常是免费接口暂时限流，稍等片刻即可恢复。"
    )

if mock_names:
    st.caption(
        f"ℹ️ 本次有 {len(mock_names)}/{len(FOCUS_CITIES)} 个城市为模拟演示数据（明细表已标注），"
        f"其余均为心知天气真实数据；系统每 10 分钟自动重试，取到真实数据后会自动替换。"
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
    st.subheader("📈 全国主要城市实时气温排行")
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
                "数据来源": "模拟演示" if now_map[n].get("mock") else "心知天气",
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
st.caption(
    "数据来源：心知天气（标注「模拟演示」的城市为程序生成的演示数据，"
    "用于接口限流时的展示兜底；无锡始终使用真实数据）"
)
