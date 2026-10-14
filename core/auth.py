"""
登录认证模块
------------
统一的登录校验，供所有页面调用。

原先的登录检查只写在 app.py 里，用户手动在地址栏输入
    http://localhost:8501/Now
就能绕过登录直接看内页。这里把校验抽成公共函数，
每个页面开头调用一次即可拦住。

用法（在 st.set_page_config 和 apply_theme 之后）：
    from core.auth import require_login
    require_login()
"""

import time

import streamlit as st

# ================= 账号配置 =================
# 需要增删账号，改这个字典即可（用户名 -> 密码）
USERS = {
    "admin": "123456",
}


def _show_login_form():
    """渲染登录表单。"""
    st.markdown(
        "<h1 style='text-align: center;'>🌤️ 气象数据可视化系统</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #8fa3b0;'>请输入账号密码以继续</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("账号", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            submit = st.form_submit_button("🚀 登 录", use_container_width=True)

            if submit:
                if USERS.get(username) == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("登录成功！正在跳转...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("账号或密码错误！")


def require_login():
    """登录守卫：未登录则显示登录页并中断当前页面渲染。

    每个页面在开头调用一次，即可防止用户通过改地址栏绕过登录。
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        _show_login_form()
        st.stop()  # 关键：中断，后面的内容不再渲染


def logout_button():
    """在侧边栏底部显示登录状态与退出按钮。"""
    with st.sidebar:
        st.markdown("---")
        if st.session_state.get("logged_in"):
            user = st.session_state.get("username", "")
            st.caption(f"👤 当前用户：{user}")
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.pop("username", None)
                st.rerun()
