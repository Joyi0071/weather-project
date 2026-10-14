"""
天气地图页：中国各省实时气温热力图
----------------------------------
思路：
1. 逐个查询各省会城市的实时气温（心知天气免费版不支持多城市，必须逐个请求）
2. 把省会气温近似为该省气温
3. 用 pyecharts 的中国地图渲染热力图，通过 components.html 嵌入
   （不用 streamlit_echarts，避开兼容性问题）
"""

import sys
import os
import time

import streamlit as st
import streamlit.components.v1 as components
import requests
from pyecharts import options as opts
from pyecharts.charts import Map

# 让 pages 目录下的页面能 import 到项目根目录的 core 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import API_KEY, API_BASE, REQUEST_TIMEOUT, ensure_api_key
from core.theme import apply_theme
from core.auth import require_login, logout_button

st.set_page_config(page_title="天气地图", layout="wide")
apply_theme()
require_login()
ensure_api_key()  # 登录守卫

# ================= 公共侧边栏 =================
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

    logout_button()
# ==============================================
st.title("🗺️ 全国气温热力地图")
st.caption("颜色越红气温越高，颜色越黄气温越低。数据约每 30 分钟更新一次。")


# ================= 省份 -> 省会城市（心知天气 location 用） =================
# 心知天气支持直接用中文城市名查询，这里用「省会中文名」最稳妥
PROVINCE_CAPITALS = {
    "北京": "北京", "天津": "天津", "上海": "上海", "重庆": "重庆",
    "河北": "石家庄", "山西": "太原", "辽宁": "沈阳", "吉林": "长春",
    "黑龙江": "哈尔滨", "江苏": "南京", "浙江": "杭州", "安徽": "合肥",
    "福建": "福州", "江西": "南昌", "山东": "济南", "河南": "郑州",
    "湖北": "武汉", "湖南": "长沙", "广东": "广州", "海南": "海口",
    "四川": "成都", "贵州": "贵阳", "云南": "昆明", "陕西": "西安",
    "甘肃": "兰州", "青海": "西宁", "广西": "南宁", "内蒙古": "呼和浩特",
    "宁夏": "银川", "新疆": "乌鲁木齐", "西藏": "拉萨",
    "台湾": "台北", "香港": "香港", "澳门": "澳门",
}

# pyecharts 中国地图里的省份名是【全称】（如"黑龙江省"、"内蒙古自治区"），
# 数据里的名字必须和地图完全一致才能上色，否则整张地图都是白的。
PROVINCE_FULL_NAME = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省",
    "广西": "广西壮族自治区", "内蒙古": "内蒙古自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    "西藏": "西藏自治区",
    "台湾": "台湾省", "香港": "香港特别行政区", "澳门": "澳门特别行政区",
}


import json
import time
from pathlib import Path

# 本地缓存文件：按省份单独记录，只补查缺失/过期的省份
# 注意：部署到云平台后文件系统可能不可写，此时自动降级为内存缓存
_CACHE_FILE = Path(__file__).parent.parent / ".heatmap_cache.json"
_CACHE_TTL = 1800  # 每个省份的缓存有效期（秒），30 分钟
_MEM_CACHE = {}    # 文件不可写时的兜底内存缓存


def _load_cache():
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        # 读不到文件（云端环境）就用内存缓存
        return dict(_MEM_CACHE)


def _save_cache(cache):
    try:
        _CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        # 写不进文件（云端只读文件系统）也不报错，改写内存
        _MEM_CACHE.clear()
        _MEM_CACHE.update(cache)


def _query_one(capital, api_key):
    """查询单个省会温度，成功返回 int，失败返回 None（内部自动重试一次）。"""
    url = (
        f"{API_BASE}/now.json?key={api_key}&location={capital}"
        f"&language=zh-Hans&unit=c"
    )
    for attempt in range(2):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            if "results" in data:
                return int(data["results"][0]["now"]["temperature"])
            if resp.status_code == 403:
                time.sleep(2)  # 被限流，等一等再重试
        except Exception:
            pass
        if attempt == 0:
            time.sleep(2)
    return None


def fetch_province_temps(api_key):
    """获取全部省份实况温度，返回 {省份名: 温度int}。

    缓存策略（关键）：
    - 每个省份独立缓存到本地文件 .heatmap_cache.json
    - 有效期内的直接用缓存，不耗 API 额度
    - 过期或缺失的才重新查询
    - 这样即使某次限流导致部分省份失败，下次刷新只补查失败的那几个，
      直到 34 个全部补齐
    """
    now = time.time()
    cache = _load_cache()
    result = {}

    # 第一遍：先用缓存里有效的数据
    to_query = []
    for province, capital in PROVINCE_CAPITALS.items():
        entry = cache.get(province)
        if entry and now - entry.get("ts", 0) < _CACHE_TTL:
            result[province] = entry["temp"]
        else:
            to_query.append((province, capital))

    # 第二遍：只查询缺失/过期的省份，每查到一个就立刻写盘
    for i, (province, capital) in enumerate(to_query):
        temp = _query_one(capital, api_key)
        if temp is not None:
            result[province] = temp
            cache[province] = {"temp": temp, "ts": now}
            _save_cache(cache)  # 立刻落盘，中途被限流也不丢已查到的
        # 免费版限额低，请求之间稍作间隔
        time.sleep(0.4)

    return result


with st.spinner("正在查询 34 个省会的实时气温（约需 15 秒，每 30 分钟缓存一次）..."):
    province_temps = fetch_province_temps(API_KEY)

if not province_temps:
    st.error(
        "所有省会数据都获取失败：请检查 API Key 是否有效，"
        "或免费额度是否已用完（等几分钟再试）。"
    )
    st.stop()

failed = [p for p in PROVINCE_CAPITALS if p not in province_temps]
if failed:
    st.caption(f"⚠️ 以下地区获取失败已留白：{'、'.join(failed)}")

# ================= 统计卡片 =================>
c1, c2, c3 = st.columns(3)
hottest = max(province_temps, key=province_temps.get)
coldest = min(province_temps, key=province_temps.get)
avg = round(sum(province_temps.values()) / len(province_temps), 1)
with c1:
    st.metric("🔥 最热省份", f"{hottest} {province_temps[hottest]}℃")
with c2:
    st.metric("❄️ 最冷省份", f"{coldest} {province_temps[coldest]}℃")
with c3:
    st.metric("🌡️ 全国平均", f"{avg} ℃")

# ================= 中国地图热力图 =================
map_chart = (
    Map()
    .add(
        "实时气温(℃)",
        [
            [PROVINCE_FULL_NAME[p], t]  # 转成地图全称，否则匹配不上不上色
            for p, t in province_temps.items()
        ],
        maptype="china",
        is_map_symbol_show=False,
        label_opts=opts.LabelOpts(is_show=True, font_size=9, color="#5a4636"),
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(title="中国地图热力图", pos_left="center"),
        visualmap_opts=opts.VisualMapOpts(
            min_=min(province_temps.values()),
            max_=max(province_temps.values()),
            is_piecewise=False,
            range_color=["#fdf6d8", "#f6c46a", "#e88b5a", "#c94f43", "#8f2d30"],
            pos_left="3%", pos_bottom="8%",
        ),
        tooltip_opts=opts.TooltipOpts(
            formatter="{b}<br/>气温：{c} ℃",
            background_color="rgba(255,255,255,.92)",
            border_color="#cfd8dc",
            textstyle_opts=opts.TextStyleOpts(color="#4a5a66"),
        ),
    )
)

# 把 pyecharts 渲染成独立 HTML，用 iframe 嵌入（绕开 streamlit_echarts 兼容性问题）
chart_html = map_chart.render_embed()
components.html(chart_html, height=560, scrolling=False)

st.markdown("---")
st.caption("数据来源：心知天气（省会实况近似省级气温）")
