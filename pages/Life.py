import sys
import os

import streamlit as st
import requests

# 让 pages 目录下的页面能 import 到项目根目录的 core 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import API_KEY, CITY_DICT, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button

st.set_page_config(page_title="生活指数", layout="wide")
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
st.title("💡 生活指数查询")
st.write("根据实时天气，为你提供穿衣、运动、紫外线等生活建议。")

city_name = st.selectbox("请选择要查看的城市：", list(CITY_DICT.keys()))
city_pinyin = CITY_DICT[city_name]


@st.cache_data(ttl=3600)
def get_life_index(city_pinyin, api_key):
    """返回 (生活指数, 错误说明)。失败时错误说明会显示在页面上，方便排查。"""
    url = (
        f"https://api.seniverse.com/v3/life/suggestion.json"
        f"?key={api_key}&location={city_pinyin}&language=zh-Hans"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if "results" in data:
            return data["results"][0]["suggestion"], ""
        # 接口正常响应但拒绝请求：把心知天气返回的原始错误带出来
        return None, f"HTTP {resp.status_code} ｜ 接口返回：{str(data)[:300]}"
    except Exception as e:
        return None, f"请求异常：{type(e).__name__}: {str(e)[:300]}"


@st.cache_data(ttl=1800)
def get_today_weather(city_pinyin, api_key):
    """获取实况温度 + 今日最高/最低温/天气现象，用于计算穿搭建议。"""
    result = {}
    try:
        url = (
            f"https://api.seniverse.com/v3/weather/now.json"
            f"?key={api_key}&location={city_pinyin}&language=zh-Hans&unit=c"
        )
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
        if "results" in data:
            now = data["results"][0]["now"]
            result["temp_now"] = int(now["temperature"])
            result["text_now"] = now.get("text", "")
        else:
            result.setdefault("_err", f"实况接口返回：{str(data)[:200]}")
    except Exception as e:
        result.setdefault("_err", f"实况接口异常：{type(e).__name__}: {str(e)[:200]}")
    try:
        url = (
            f"https://api.seniverse.com/v3/weather/daily.json"
            f"?key={api_key}&location={city_pinyin}&language=zh-Hans&unit=c&start=0&days=1"
        )
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()
        if "results" in data:
            daily = data["results"][0]["daily"][0]
            result["high"] = int(daily["high"])
            result["low"] = int(daily["low"])
            result["text_day"] = daily.get("text_day", "")
            result["wind_scale"] = daily.get("wind_scale", "")
        else:
            result.setdefault("_err", f"预报接口返回：{str(data)[:200]}")
    except Exception as e:
        result.setdefault("_err", f"预报接口异常：{type(e).__name__}: {str(e)[:200]}")
    return result


def _temp_to_outfit(temp):
    """按温度给出具体衣物清单。temp 取一天中最有代表性的温度。"""
    if temp >= 30:
        return ("炎热 ☀️", ["短袖T恤", "短裤/短裙", "凉鞋", "遮阳帽"],
                "天气炎热，选透气轻薄的面料，注意防晒补水。")
    if temp >= 26:
        return ("偏热 🌤️", ["短袖", "薄长裤/薄裙", "凉鞋或单鞋"],
                "温度偏高，短袖即可，怕晒可以加一件防晒衣。")
    if temp >= 21:
        return ("舒适 🙂", ["短袖或薄长袖", "长裤", "薄外套备着"],
                "体感舒适，早晚可能偏凉，随身带件薄外套更稳妥。")
    if temp >= 16:
        return ("微凉 🍂", ["长袖衬衫", "薄毛衣", "夹克/卫衣", "长裤"],
                "需要长袖了，卫衣或夹克正合适。")
    if temp >= 11:
        return ("凉 🧥", ["毛衣", "夹克/风衣", "厚长裤"],
                "天气转凉，毛衣+外套的组合保暖又好穿脱。")
    if temp >= 5:
        return ("较冷 🧥🧣", ["厚毛衣", "大衣/棉服", "围巾"],
                "气温较低，出门穿上大衣或棉服，围巾也安排上。")
    if temp >= -3:
        return ("寒冷 ❄️", ["羽绒服", "厚毛衣", "保暖内衣", "围巾手套"],
                "寒冬模式，羽绒服是标配，里层再加件毛衣更暖。")
    return ("严寒 🥶", ["厚羽绒服", "保暖内衣", "毛衣", "帽子围巾手套", "雪地靴"],
            "气温极低，全副武装，尽量减少户外停留时间。")


def clothing_advice(weather):
    """综合温度、天气现象、风力，生成穿搭推荐文案。"""
    if not weather:
        return None

    # 用「今日低温」决定基础穿搭，用「实况温度」修正：白天热就按实况推荐
    base_temp = weather.get("temp_now", weather.get("high"))
    if base_temp is None:
        return None
    low = weather.get("low")
    high = weather.get("high")
    text = weather.get("text_now") or weather.get("text_day") or ""
    wind_scale = weather.get("wind_scale", "")

    level, items, reason = _temp_to_outfit(base_temp)

    # 天气现象追加提示
    tips = []
    rainy_kw = ("雨", "雷", "阵雨")
    if any(k in text for k in rainy_kw):
        tips.append("☔ 今天有雨，记得带伞，穿防水的鞋子")
        items.append("雨伞")
    if "雪" in text:
        tips.append("❄️ 有雪路滑，穿防滑保暖的鞋子")
    if "雾" in text or "霾" in text:
        tips.append("😷 能见度低/空气差，建议戴口罩")
    try:
        if wind_scale and int(wind_scale) >= 5:
            tips.append(f"💨 风力{wind_scale}级偏大，外套选防风的")
    except ValueError:
        pass

    # 早晚温差提醒
    if low is not None and high is not None and (high - low) >= 9:
        tips.append(f"🌡️ 早晚温差大（{low}℃~{high}℃），早晚出门加件外套")

    return {"level": level, "items": items, "reason": reason, "tips": tips,
            "temp_now": weather.get("temp_now"), "low": low, "high": high}


with st.spinner("正在获取生活指数..."):
    life_data, life_err = get_life_index(city_pinyin, API_KEY)

# ---------- 今日穿搭推荐 ----------
with st.spinner("正在生成穿搭建议..."):
    today = get_today_weather(city_pinyin, API_KEY)
advice = clothing_advice(today)

if advice:
    st.subheader(f"🧥 {city_name} 今日穿搭推荐")

    temp_line = []
    if advice["temp_now"] is not None:
        temp_line.append(f"实时 {advice['temp_now']}℃")
    if advice["low"] is not None and advice["high"] is not None:
        temp_line.append(f"今日 {advice['low']}℃ ~ {advice['high']}℃")
    temp_str = " ｜ ".join(temp_line)

    # 用带边框容器做一张"穿搭卡片"
    with st.container(border=True):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:44px;font-weight:700;color:#c94f43;'>"
                f"{advice['temp_now'] if advice['temp_now'] is not None else '--'}℃</div>"
                f"<div style='font-size:15px;color:#7a6a55;'>{advice['level']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_b:
            # 衣物清单渲染成"标签"
            chips = " ".join(
                f"<span style='display:inline-block;margin:3px 4px;padding:4px 12px;"
                f"background:#fdf6ec;border:1px solid #e8d9c0;border-radius:14px;"
                f"font-size:13px;color:#6b5b45;'>{it}</span>"
                for it in advice["items"]
            )
            st.markdown(
                f"<div style='font-size:14px;color:#5a4a38;'>{temp_str}</div>"
                f"<div style='margin-top:6px;'>{chips}</div>"
                f"<div style='margin-top:8px;font-size:13px;color:#8a7a65;'>{advice['reason']}</div>",
                unsafe_allow_html=True,
            )
        # 额外提醒（下雨/大风/温差等）
        for tip in advice["tips"]:
            st.markdown(
                f"<div style='margin-top:4px;padding:6px 12px;background:#fff7e0;"
                f"border-radius:8px;font-size:13px;color:#8a6d1f;'>{tip}</div>",
                unsafe_allow_html=True,
            )

# ---------- 原有四大生活指数 ----------
if life_data:
    st.subheader(f"📍 {city_name} 今日生活建议")
    idx1, idx2, idx3, idx4 = st.columns(4)
    with idx1:
        st.info(f"👕 **穿衣指数**\n\n{life_data.get('dressing', {}).get('brief', '暂无')}")
    with idx2:
        st.info(f"🏃 **运动指数**\n\n{life_data.get('sport', {}).get('brief', '暂无')}")
    with idx3:
        st.info(f"🧴 **紫外线**\n\n{life_data.get('uv', {}).get('brief', '暂无')}")
    with idx4:
        st.info(f"🚗 **洗车指数**\n\n{life_data.get('car_washing', {}).get('brief', '暂无')}")
    st.caption("数据来源：心知天气")
else:
    st.warning("生活指数获取失败，请检查私钥或网络。")
    # ---------- 诊断信息（排查云端问题用，正常时不显示） ----------
    with st.expander("🔧 技术细节（排查用）"):
        st.write("**当前密钥**：前缀 `" + (API_KEY[:2] or "空") + "…`，长度 "
                 + str(len(API_KEY)) + "（私钥应以 S 开头）")
        st.write("**生活指数接口报错**：" + (life_err or "无"))
        st.write("**实况/预报接口报错**：" + (today.get("_err") or "无（接口正常）"))
        st.write("**运行环境**：云端服务器所在的网络可能无法访问 api.seniverse.com")
        st.code(
            "诊断提示：\n"
            "- 前缀为 P → 填的是「公钥」，服务器调用必须用 S 开头的私钥\n"
            "- 前缀为 S 但报「请求异常 Timeout/ConnectionError」→ 云端到心知天气网络不通 "
            "（Streamlit Cloud 服务器在海外），本地正常不代表云端正常\n"
            "- 返回 JSON 里有 status 字段 → 照 status 的原文对照心知天气文档",
            language="text",
        )
