import os
import sys

import streamlit as st
import requests
import pandas as pd

# 让根目录能 import 到 core / charts 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.config import API_KEY, CITY_DICT, API_BASE, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button
from charts import line_chart, bar_chart

# 页面基础配置（放在最前面）
st.set_page_config(page_title="气象数据可视化系统", layout="wide", page_icon="🌤️")
apply_theme()

# ================= 登录校验（未登录则只显示登录页） =================
require_login()
ensure_api_key()
# ====================================================================

# ================= 公共侧边栏导航 =================
# 隐藏默认英文菜单
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🧭 系统导航")
    st.page_link("app.py", label="🏠 天气主页", icon="🏠")
    st.page_link("pages/Now.py", label="🌡️ 实况天气", icon="🌡️")
    st.page_link("pages/Life.py", label="💡 生活指数", icon="💡")
    st.page_link("pages/Compare.py", label="📊 城市对比", icon="📊")
    st.page_link("pages/HeatMap.py", label="🗺️ 天气地图", icon="🗺️")
    st.page_link("pages/dashboard.py", label="📈 数据大屏", icon="📈")

logout_button()  # 侧边栏底部「退出登录」
# ================================================

# ================= 2. 主系统（登录成功后显示） =================
st.title("🌤️ 城市气象数据可视化系统")
st.write(f"欢迎回来，{st.session_state.get('username', '管理员')}！本系统基于 Python 开发，实时展示城市天气趋势。")

city_name = st.selectbox("请选择要查看的城市：", list(CITY_DICT.keys()))
city_pinyin = CITY_DICT[city_name]


# ================= 3. 获取天气数据函数 =================
@st.cache_data(ttl=3600)  # 缓存1小时，避免频繁请求
def get_weather_data(city_pinyin, api_key):
    """未来3天预报。返回 (数据, 错误信息)。"""
    url = (
        f"{API_BASE}/daily.json?key={api_key}&location={city_pinyin}"
        f"&language=zh-Hans&unit=c&start=0&days=3"
    )
    try:
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
        if "results" in data:
            return data["results"][0]["daily"], None
        return None, f"接口返回错误：{data.get('status', '未知')}"
    except Exception as e:
        return None, f"网络请求出错：{e}"


# ================= 4. 获取生活指数函数 =================
@st.cache_data(ttl=3600)
def get_life_index(city_pinyin, api_key):
    url = (
        f"{API_BASE.replace('/weather', '')}/life/suggestion.json"
        f"?key={api_key}&location={city_pinyin}&language=zh-Hans"
    )
    try:
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
        if "results" in data:
            return data["results"][0]["suggestion"]
        return None
    except Exception:
        return None


# ================= 5. 数据处理与展示 =================
with st.spinner("正在获取天气数据..."):
    daily_data, weather_err = get_weather_data(city_pinyin, API_KEY)

if daily_data:
    dates = [item["date"] for item in daily_data]
    temp_max = [int(item["high"]) for item in daily_data]
    temp_min = [int(item["low"]) for item in daily_data]
    weather_text = [item["text_day"] for item in daily_data]

    df = pd.DataFrame(
        {"日期": dates, "最高温(℃)": temp_max, "最低温(℃)": temp_min, "天气": weather_text}
    )

    # ---------- 5.1 展示表格 ----------
    st.subheader(f"📊 {city_name} 未来3天天气数据表")
    st.dataframe(df.style.highlight_max(axis=0), use_container_width=True)

    # ---------- 5.2 展示图表（带卡片外框） ----------
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("📈 气温变化趋势图")
            line_chart(
                dates,
                {"最高温": temp_max, "最低温": temp_min},
                height=400,
                x_label="日期",
                y_label="温度(℃)",
            )

    with col2:
        with st.container(border=True):
            st.subheader("📊 天气状况对比")
            bar_chart(
                dates,
                {"最高温": temp_max, "最低温": temp_min},
                height=400,
                x_label="日期",
                y_label="温度(℃)",
            )
else:
    st.error(f"天气数据获取失败：{weather_err}")

# ================= 生活指数模块 =================
st.markdown("---")
st.subheader("💡 今日生活指数")

life_data = get_life_index(city_pinyin, API_KEY)

if life_data:
    idx1, idx2, idx3, idx4 = st.columns(4)
    with idx1:
        st.info(f"👕 **穿衣指数**\n\n{life_data.get('dressing', {}).get('brief', '暂无')}")
    with idx2:
        st.info(f"🏃 **运动指数**\n\n{life_data.get('sport', {}).get('brief', '暂无')}")
    with idx3:
        st.info(f"🧴 **紫外线**\n\n{life_data.get('uv', {}).get('brief', '暂无')}")
    with idx4:
        st.info(f"🚗 **洗车指数**\n\n{life_data.get('car_washing', {}).get('brief', '暂无')}")

    with st.expander("📝 查看详细建议"):
        st.write(f"**穿衣**：{life_data.get('dressing', {}).get('description', '今日穿衣舒适，建议着薄外套或牛仔衫裤。')}")
        st.write(f"**运动**：{life_data.get('sport', {}).get('description', '天气条件较不宜运动，建议在室内进行轻度活动。')}")
        st.write(f"**紫外线**：{life_data.get('uv', {}).get('description', '紫外线强度较弱，无需特别防护。')}")
        st.write(f"**旅游**：{life_data.get('travel', {}).get('description', '天气较好，适合外出旅游。')}")
        st.write(f"**感冒**：{life_data.get('flu', {}).get('description', '昼夜温差较大，请注意适当增减衣服。')}")
        st.write(f"**洗车**：{life_data.get('car_washing', {}).get('description', '天气较适宜洗车，保持车辆清洁。')}")

    st.caption("💡 提示：以上指数由心知天气提供，仅供参考。")
else:
    st.warning("生活指数获取失败，请检查网络或 API Key。")

st.markdown("---")
st.caption("毕业设计项目：基于 Python 的气象数据可视化系统 | 数据来源：心知天气")
