"""
集中配置模块
------------
所有页面从这里取 API Key 和城市字典，避免密钥在多个文件里重复硬编码。

API Key 读取优先级（从上到下，先找到先用）：
1. st.secrets          —— 推荐！Streamlit 官方密钥管理
                          密钥文件：.streamlit/secrets.toml（不会提交到 git）
2. 环境变量 SENIVERSE_KEY —— 部署到云平台时用（如 Streamlit Cloud / 服务器）
3. key.txt             —— 本地临时使用（不要提交到 git）
4. DEFAULT_API_KEY     —— 兜底占位，默认留空

【重要】代码里不写任何真实密钥。
换密钥时只需改 .streamlit/secrets.toml，代码一行都不用动。
"""

import os

# 兜底值：故意留空，避免密钥出现在代码里。
# 如果所有来源都没配，程序会提示用户去配置。
DEFAULT_API_KEY = ""

_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "key.txt")


def _load_api_key() -> str:
    """按优先级读取 API Key，返回空串表示未配置。"""

    # ---------- 1. st.secrets（推荐） ----------
    try:
        import streamlit as st
        # 方式一：secrets.toml 里写 apikey = "xxx"
        if "apikey" in st.secrets:
            key = str(st.secrets["apikey"]).strip()
            if key:
                return key
        # 方式二：secrets.toml 里写 [seniverse] apikey = "xxx"
        if "seniverse" in st.secrets and "apikey" in st.secrets["seniverse"]:
            key = str(st.secrets["seniverse"]["apikey"]).strip()
            if key:
                return key
    except Exception:
        # secrets.toml 不存在或不在 Streamlit 运行时，静默跳过
        pass

    # ---------- 2. 环境变量 ----------
    env_key = os.environ.get("SENIVERSE_KEY", "").strip()
    if env_key:
        return env_key

    # ---------- 3. key.txt ----------
    try:
        with open(_KEY_FILE, "r", encoding="utf-8") as f:
            file_key = f.read().strip()
            if file_key:
                return file_key
    except OSError:
        pass

    # ---------- 4. 兜底（默认空） ----------
    return DEFAULT_API_KEY


API_KEY = _load_api_key()


def ensure_api_key():
    """检查密钥是否已配置。

    未配置时给出清晰的引导并中断页面，避免出现一堆看不懂的报错。
    在 require_login() 之后调用。
    """
    if API_KEY:
        return

    import streamlit as st

    st.error(
        "### ⚠️ 尚未配置心知天气密钥\n\n"
        "请按以下任一方式配置后重试：\n\n"
        "**方式一（本地）**：在项目根目录新建 `key.txt`，把密钥粘进去保存。\n\n"
        "**方式二（云端部署）**：在应用的 **Settings → Secrets** 中填入：\n"
        "```toml\n"
        'apikey = "你的密钥"\n'
        "```\n\n"
        "**方式三（环境变量）**：设置 `SENIVERSE_KEY` 环境变量。\n\n"
        "> 密钥在心知天气官网「控制台 → 我的密钥」获取（以 S 开头的是私钥）。"
    )
    st.stop()


# ================= 城市字典（唯一数据源） =================
# 键为中文城市名，值为心知天气的城市拼音/ID
# 覆盖：直辖市 + 全部省会 + 主要经济强市，共 42 城
CITY_DICT = {
    # ---- 直辖市 / 一线城市 ----
    "北京": "beijing",
    "上海": "shanghai",
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "天津": "tianjin",
    "重庆": "chongqing",
    # ---- 江苏省（含重点关注城市：无锡，大屏保证无锡为真实数据） ----
    "南京": "nanjing",
    "无锡": "wuxi",
    "苏州": "suzhou",
    "常州": "changzhou",
    # ---- 华东 ----
    "杭州": "hangzhou",
    "宁波": "ningbo",
    "温州": "wenzhou",
    "合肥": "hefei",
    "福州": "fuzhou",
    "厦门": "xiamen",
    "南昌": "nanchang",
    "济南": "jinan",
    "青岛": "qingdao",
    # ---- 华南 / 华中 ----
    "东莞": "dongguan",
    "佛山": "foshan",
    "武汉": "wuhan",
    "长沙": "changsha",
    "郑州": "zhengzhou",
    "南宁": "nanning",
    "海口": "haikou",
    # ---- 华北 / 东北 ----
    "石家庄": "shijiazhuang",
    "太原": "taiyuan",
    "呼和浩特": "huhehaote",
    "沈阳": "shenyang",
    "大连": "dalian",
    "长春": "changchun",
    "哈尔滨": "haerbin",
    # ---- 西南 / 西北 ----
    "成都": "chengdu",
    "贵阳": "guiyang",
    "昆明": "kunming",
    "拉萨": "lasa",
    "西安": "xian",
    "兰州": "lanzhou",
    "西宁": "xining",
    "银川": "yinchuan",
    "乌鲁木齐": "wulumuqi",
}

# 大屏 / 对比默认关注的城市（全部城市上大屏）
FOCUS_CITIES = list(CITY_DICT.keys())

# 必须使用真实数据的城市（不允许用模拟数据兜底，失败时页面会明确提示）
MUST_REAL_CITIES = {"无锡"}

# ================= 其他常量 =================
API_BASE = "https://api.seniverse.com/v3/weather"
REQUEST_TIMEOUT = 8  # 单次请求超时（秒）
MAX_RETRIES = 3  # 最大重试次数
