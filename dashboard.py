import sys
import os

import requests
import streamlit as st
import requests

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


# ================= 数据获取（带缓存，只请求一次） =================
@st.cache_data(ttl=1800)
def fetch_cities_now(names, api_key):
    """一次性抓取多个城市的实况，返回 {城市名: {temperature, text, wind_scale}}。

    抽成单次循环 + 缓存，避免原来两段代码重复请求同一批城市，
    既浪费额度又容易触发限流。
    """
    result = {}
    errors = []
    for name in names:
        pinyin = CITY_DICT.get(name)
        if not pinyin:
            continue
        url = (
            f"{API_BASE}/now.json?key={api_key}&location={pinyin}"
            f"&language=zh-Hans&unit=c"
        )
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT).json()
            if "results" in res:
                now = res["results"][0]["now"]
                result[name] = {
                    "temperature": now.get("temperature"),
                    "text": now.get("text", "未知"),
                    "wind_scale": now.get("wind_scale", "--"),
                }
            else:
                errors.append(res.get("status", "未知错误"))
        except Exception as e:
            errors.append(str(e))
    return result, errors


with st.spinner("正在获取全国气象数据..."):
    now_map, fetch_errors = fetch_cities_now(FOCUS_CITIES, API_KEY)

if fetch_errors and not now_map:
    st.error(
        "获取数据失败，请检查 API Key 是否有效，或是否已超出调用频率限制"
        "（心知天气免费版限额较低，稍等几分钟后重试）。"
    )
    st.stop()

# ================= 顶部：4个统计卡片（基于真实数据） =================
sunny = sum(1 for v in now_map.values() if v["text"] in ("晴", "晴天"))
rainy = sum(1 for v in now_map.values() if "雨" in v["text"])
temps = [int(v["temperature"]) for v in now_map.values() if str(v["temperature"]).lstrip("-").isdigit()]
winds = [
    float(v["wind_scale"])
    for v in now_map.values()
    if str(v["wind_scale"]).replace(".", "", 1).isdigit()
]
avg_temp = round(sum(temps) / len(temps), 1) if temps else 0
avg_wind = round(sum(winds) / len(winds), 1) if winds else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="☀️ 晴天城市", value=f"{sunny} / {len(now_map)}")
with col2:
    st.metric(label="🌧️ 雨天城市", value=f"{rainy} / {len(now_map)}")
with col3:
    st.metric(label="🌡️ 平均气温", value=f"{avg_temp} ℃")
with col4:
    st.metric(label="💨 平均风速", value=f"{avg_wind} 级")

if fetch_errors:
    st.caption(f"⚠️ 有 {len(fetch_errors)} 个城市数据获取失败，已跳过。")

st.markdown("---")

# ================= 中间：左右两个图表 =================
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📈 主要城市实时气温对比")
    if now_map:
        compare_names = list(now_map.keys())
        compare_temps = [int(now_map[n]["temperature"]) for n in compare_names]
        simple_bar(
            compare_names,
            compare_temps,
            height=350,
            x_label="城市",
            y_label="温度(℃)",
            label="当前气温(℃)",
        )
    else:
        st.info("暂无城市数据，无法绘制气温对比图。")

with right_col:
    st.subheader("☁️ 主要城市天气状况占比")
    weather_counts = {}
    for v in now_map.values():
        weather_counts[v["text"]] = weather_counts.get(v["text"], 0) + 1

    if weather_counts:
        pie_chart(list(weather_counts.keys()), list(weather_counts.values()), height=350)
    else:
        st.info("暂时获取不到天气状况数据，请稍后再试。")

st.markdown("---")
st.caption("数据来源：心知天气")
