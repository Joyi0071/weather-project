"""
图表模块（核心）
----------------
统一封装折线图 / 柱状图 / 饼图的绘制。

【为什么不用 st_pyecharts？】
    原项目用的 `streamlit_echarts` 组件在新版 Streamlit（1.65+）中导入即报错：
        StreamlitAPIException: Component 'streamlit-echarts.streamlit_echarts'
        must be declared in pyproject.toml with asset_dir to use file-backed js.
    而把它降级到兼容版本又要求 numpy<2，与当前 numpy 2.x 环境冲突。

    因此这里改用 Streamlit **原生图表**（st.line_chart / st.bar_chart），
    零第三方组件依赖，任何 Streamlit 版本都能跑。

    如果你将来想切回 ECharts 外观，把 USE_ECHARTS 改成 True 即可
    （需自行安装兼容版本的 streamlit_echarts）。
"""

import pandas as pd
import streamlit as st

USE_ECHARTS = False  # 保持 False：使用原生图表，无兼容性问题


# ================= 折线图 =================
def line_chart(x, series: dict, height=400, x_label="", y_label=""):
    """绘制折线图。

    x: X 轴标签列表
    series: {系列名: 数值列表}
    """
    df = pd.DataFrame(series, index=x)
    st.line_chart(df, height=height, x_label=x_label, y_label=y_label)


# ================= 柱状图 =================
def bar_chart(x, series: dict, height=400, x_label="", y_label=""):
    """绘制柱状图（分组）。

    x: X 轴标签列表
    series: {系列名: 数值列表}
    """
    df = pd.DataFrame(series, index=x)
    st.bar_chart(df, height=height, x_label=x_label, y_label=y_label)


# ================= 饼图（用原生方式模拟：横向条形占比图） =================
def pie_chart(labels, values, height=400):
    """原生 Streamlit 没有饼图，用「占比条形图」表达，信息量等价且更易读。"""
    total = sum(values) or 1
    df = pd.DataFrame(
        {"占比": [v / total * 100 for v in values]},
        index=labels,
    )
    st.bar_chart(df, height=height, horizontal=True, x_label="占比(%)")


# ================= 单系列柱状图 =================
def simple_bar(x, values, height=350, x_label="", y_label="", label="数值"):
    """单系列柱状图，用于「各城市气温对比」。"""
    df = pd.DataFrame({label: values}, index=x)
    st.bar_chart(df, height=height, x_label=x_label, y_label=y_label)
