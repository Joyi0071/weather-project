import sys
import os

import streamlit as st
import requests

# 让 pages 目录下的页面能 import 到项目根目录的 core 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import API_KEY, CITY_DICT, API_BASE, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button

st.set_page_config(page_title="实况天气", layout="wide")
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
st.title("🌡️ 实时天气实况")

city_name = st.selectbox("请选择要查看的城市：", list(CITY_DICT.keys()))
city_pinyin = CITY_DICT[city_name]


@st.cache_data(ttl=1800)
def get_now_weather(city_pinyin, api_key):
    url = (
        f"{API_BASE}/now.json?key={api_key}&location={city_pinyin}"
        f"&language=zh-Hans&unit=c"
    )
    try:
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
        if "results" in data:
            return data["results"][0]["now"]
        return None
    except Exception:
        return None


with st.spinner("正在获取实况天气..."):
    now_data = get_now_weather(city_pinyin, API_KEY)

if now_data:
    st.subheader(f"📍 {city_name} 当前天气")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🌡️ 当前温度", value=f"{now_data.get('temperature', '--')} ℃")
    with col2:
        st.metric(label="🌤️ 天气现象", value=now_data.get("text", "--"))
    with col3:
        st.metric(
            label="💨 风向风速",
            value=f"{now_data.get('wind_direction', '--')} {now_data.get('wind_scale', '--')}级",
        )

    st.caption("数据来源：心知天气")
else:
    st.warning("实况天气获取失败，请检查私钥或网络。")
