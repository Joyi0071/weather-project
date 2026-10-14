"""
Aether 风格主题模块
-------------------
给整套系统加「手绘梦幻天空」视觉：清透天空渐变（浅蓝→奶油色）、
云朵 / 太阳 / 月亮 / 雨滴 / 小伞装饰、柔和卡片阴影。

使用方法（每个页面在 st.set_page_config 之后加两行即可）：
    from core.theme import apply_theme
    apply_theme()

不改动任何业务逻辑与数据代码。
"""

import streamlit as st
import base64

# ================= 手绘风顶部横幅（内嵌 SVG） =================
def _banner_svg() -> str:
    """手绘感天空横幅：渐变天空 + 云朵 + 太阳月亮雨滴小伞。"""
    return """
<svg viewBox="0 0 1000 260" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;border-radius:18px;">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#c9e6f5"/>
      <stop offset="55%" stop-color="#e3f1f2"/>
      <stop offset="100%" stop-color="#faf5e8"/>
    </linearGradient>
    <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f9e08a" stop-opacity="0.95"/>
      <stop offset="60%" stop-color="#f7d976" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#f7d976" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="1000" height="260" rx="18" fill="url(#sky)"/>

  <!-- 太阳 + 光晕 -->
  <circle cx="800" cy="85" r="95" fill="url(#sunGlow)"/>
  <circle cx="800" cy="85" r="46" fill="#f7d976"/>
  <circle cx="800" cy="85" r="46" fill="none" stroke="#efc75e" stroke-width="2" opacity="0.6"/>

  <!-- 月牙 -->
  <path d="M 660 52 a 17 17 0 1 0 14 27 a 21 21 0 1 1 -14 -27 Z" fill="#f3d9a4" opacity="0.9"/>

  <!-- 云朵：多组椭圆拼合，错落分布 -->
  <g fill="#ffffff" opacity="0.95">
    <g transform="translate(120,95)">
      <ellipse cx="0"   cy="0"  rx="62" ry="30"/>
      <ellipse cx="-45" cy="12" rx="42" ry="22"/>
      <ellipse cx="48"  cy="12" rx="46" ry="24"/>
    </g>
    <g transform="translate(430,60)" opacity="0.9">
      <ellipse cx="0"   cy="0"  rx="52" ry="25"/>
      <ellipse cx="-40" cy="10" rx="35" ry="18"/>
      <ellipse cx="42"  cy="10" rx="38" ry="20"/>
    </g>
    <g transform="translate(910,175)" opacity="0.95">
      <ellipse cx="0"   cy="0"  rx="70" ry="30"/>
      <ellipse cx="-52" cy="13" rx="45" ry="22"/>
      <ellipse cx="55"  cy="13" rx="50" ry="24"/>
    </g>
    <g transform="translate(300,190)" opacity="0.85">
      <ellipse cx="0"   cy="0"  rx="46" ry="21"/>
      <ellipse cx="38"  cy="9"  rx="33" ry="16"/>
    </g>
  </g>

  <!-- 雨滴（奶油色调） -->
  <g fill="#bcd8e6">
    <path d="M 585 150 q 6 10 0 15 q -6 -5 0 -15 Z"/>
    <path d="M 615 175 q 6 10 0 15 q -6 -5 0 -15 Z"/>
    <path d="M 645 155 q 6 10 0 15 q -6 -5 0 -15 Z"/>
  </g>
  <!-- 雪花点 -->
  <g fill="#e8f2f5" stroke="#c3d9e3" stroke-width="1">
    <circle cx="700" cy="185" r="4"/>
    <circle cx="725" cy="200" r="3"/>
  </g>

  <!-- 小伞 1（右上，倾斜） -->
  <g transform="translate(872,118) rotate(18)">
    <path d="M 0 -26 C -26 -26 -34 -4 -34 0 L 34 0 C 34 -4 26 -26 0 -26 Z"
          fill="#e9b7b4" stroke="#d69a97" stroke-width="1.6"/>
    <path d="M 0 -26 C -12 -26 -17 -4 -17 0 M 0 -26 C 12 -26 17 -4 17 0"
          fill="none" stroke="#d69a97" stroke-width="1.4"/>
    <path d="M 0 0 L 0 22 q 0 8 -8 8" fill="none" stroke="#8a7f76" stroke-width="2.4" stroke-linecap="round"/>
  </g>

  <!-- 小伞 2（右下） -->
  <g transform="translate(760,215) rotate(-12) scale(0.75)">
    <path d="M 0 -26 C -26 -26 -34 -4 -34 0 L 34 0 C 34 -4 26 -26 0 -26 Z"
          fill="#f0cdb2" stroke="#dcb28f" stroke-width="1.6"/>
    <path d="M 0 -26 C -12 -26 -17 -4 -17 0 M 0 -26 C 12 -26 17 -4 17 0"
          fill="none" stroke="#dcb28f" stroke-width="1.4"/>
    <path d="M 0 0 L 0 22 q 0 8 8 8" fill="none" stroke="#8a7f76" stroke-width="2.4" stroke-linecap="round"/>
  </g>
</svg>
"""


def apply_theme():
    """注入全局主题样式 + 顶部装饰横幅。"""

    # ---------- 顶部横幅 ----------
    st.markdown(_banner_svg(), unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ---------- 全局样式 ----------
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&display=swap');

/* 页面整体：天空→奶油 渐变背景 */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #cfe8f5 0%, #e6f2f3 34%, #f7f2e4 72%, #faf6ec 100%);
    background-attachment: fixed;
}
/* 顶栏透明，融入天空 */
[data-testid="stHeader"] { background: transparent; }

/* 侧边栏：半透明奶油玻璃 */
[data-testid="stSidebar"] {
    background: rgba(252, 249, 240, 0.88);
    border-right: 1px solid rgba(180, 200, 210, 0.35);
}
[data-testid="stSidebar"] * { color: #4a5a66 !important; }

/* 标题字体：衬线，手账感 */
h1, .stApp h1, [data-testid="stMarkdownContainer"] h1 {
    font-family: 'Noto Serif SC', serif !important;
    color: #46647a !important;
}
h2, h3 {
    font-family: 'Noto Serif SC', serif !important;
    color: #557186 !important;
}

/* metric 卡片：云朵白 + 柔和描边阴影 */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(175, 205, 220, 0.45);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 4px 14px rgba(120, 150, 170, 0.12);
}
[data-testid="stMetricLabel"] p { color: #6b7f8c !important; }
[data-testid="stMetricValue"] { color: #3f5d70 !important; }

/* info 卡片：淡云蓝 */
div[data-testid="stAlert"] {
    background: rgba(255,255,255,0.66);
    border: 1px solid rgba(175, 205, 220, 0.45);
    border-radius: 14px;
    color: #4a5a66;
}

/* 输入框 / 下拉框：云白圆角 */
div[data-baseweb="select"], div[data-baseweb="input"], div[data-baseweb="textarea"] {
    border-radius: 12px !important;
}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: rgba(255,255,255,0.85) !important;
    border-color: rgba(160, 195, 215, 0.5) !important;
}

/* 按钮：奶油底 + 圆角 */
.stButton > button, .stFormSubmitButton > button {
    background: linear-gradient(180deg, #fdf8ec, #f7edd6) !important;
    color: #6b5d3f !important;
    border: 1px solid #e5d5b3 !important;
    border-radius: 999px !important;
    font-weight: 600;
    box-shadow: 0 3px 10px rgba(180, 160, 110, 0.18);
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(180, 160, 110, 0.28);
}

/* 主内容区透明化，露出天空渐变 */
.block-container { padding-top: 1.4rem; }
[data-testid="stVerticalBlockBorderWrapper"] { background: transparent; }
</style>
""",
        unsafe_allow_html=True,
    )


def page_footer():
    """统一的页脚署名（可选调用）。"""
    st.markdown(
        """
<div style='text-align:center;color:#8fa3b0;font-size:0.85rem;
            border-top:1px dashed rgba(160,195,215,.4);margin-top:2.5rem;padding-top:.9rem;'>
  🌤️ 毕业设计 · 基于 Python 的气象数据可视化系统 · 数据来源：心知天气
</div>
""",
        unsafe_allow_html=True,
    )
