import sys
import os
import time

import streamlit as st
import requests

# 让 pages 目录下的页面能 import 到项目根目录的 core / charts 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import API_KEY, CITY_DICT, API_BASE, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button
from charts import line_chart

st.set_page_config(page_title="城市数据对比", layout="wide")
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
st.title("📊 多城市气象数据对比")

st.markdown("### 🏙️ 请选择要对比的城市（最多3个）")
selected_names = st.multiselect(
    "选择城市：",
    list(CITY_DICT.keys()),
    default=["南京", "上海"],
)


class _CompareFetchFail(Exception):
    """单个城市获取失败（故意抛异常：st.cache_data 不缓存异常，
    失败的城市不会被缓存冻结，下次访问自动重试补齐）。"""


@st.cache_data(ttl=1800, show_spinner=False)
def get_city_daily(city_name, api_key):
    """获取单个城市未来3天预报，成功返回 daily 列表（缓存30分钟）。

    【重要】心知天气免费版不支持一次查询多个地点（location 用 | 会返回
    404 AP010010），所以这里逐个城市请求，再在页面上合并。

    稳定性措施：
    - 最多尝试 4 次，被限流时递增等待（3s / 6s / 8s）
    - 失败抛异常而不返回 None：异常不会被 st.cache_data 缓存，
      因此失败的城市下次刷新会自动重试，不会被冻结 30 分钟
    """
    pinyin = CITY_DICT[city_name]
    url = (
        f"{API_BASE}/daily.json?key={api_key}&location={pinyin}"
        f"&language=zh-Hans&unit=c&start=0&days=3"
    )
    last_err = "未知错误"
    for attempt in range(4):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            if "results" in data:
                return data["results"][0]["daily"]
            # 限流时通常返回 403
            last_err = "limit" if resp.status_code == 403 else str(
                data.get("status", "未知错误")
            )
            time.sleep(min(3 * (attempt + 1), 8))
        except Exception as e:
            last_err = f"网络请求出错：{e}"
            time.sleep(min(3 * (attempt + 1), 8))
    raise _CompareFetchFail(last_err)


if len(selected_names) < 2:
    st.warning("请至少选择 2 个城市进行对比。")
elif len(selected_names) > 3:
    st.warning("最多只能选择 3 个城市哦！")
else:
    compare_data = {}
    failed = []
    limited = False

    with st.spinner("正在逐个获取城市数据..."):
        for name in selected_names:
            try:
                compare_data[name] = get_city_daily(name, API_KEY)
            except _CompareFetchFail as e:
                failed.append(name)
                if str(e) == "limit":
                    limited = True
            # 免费版限额低，逐个请求之间稍作间隔，避免被限流
            time.sleep(0.5)

    if not compare_data:
        if limited:
            st.warning(
                "调用频率超出限制。心知天气免费版额度和频率都较低，"
                "请等待几分钟后再试，或减少同时对比的城市数量。"
            )
        else:
            st.error("获取数据失败，请检查 API Key 是否正确、是否有效。")
    else:
        if failed:
            st.caption(f"⚠️ 以下城市获取失败已跳过：{'、'.join(failed)}")

        st.markdown("---")
        st.subheader("🌡️ 多城市气温对比图")

        dates = [item["date"] for item in list(compare_data.values())[0]]
        series = {
            city_name: [int(item["high"]) for item in daily_list]
            for city_name, daily_list in compare_data.items()
        }

        line_chart(dates, series, height=450, x_label="日期", y_label="最高气温(℃)")

        st.markdown("---")
        st.caption("数据来源：心知天气")
