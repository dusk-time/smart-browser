# Smart Browser

Playwright + LLM 智能浏览器助手，基于 Firefox 和 MiniMax-M2.7。

## 文件

- `smart_browser.py` — AI 决策版（推荐）
- `simple_browser.py` — 轻量固定流程版

## 安装

```bash
pip install playwright openai
playwright install firefox
```

## 配置

编辑文件内的 API Key：
```python
api_key='YOUR_MINIMAX_API_KEY'
base_url='https://api.minimaxi.com/v1'
```

## 使用

```bash
python smart_browser.py "打开Google，搜索OpenClaw，返回页面标题"
```

## 依赖

- Python 3.8+
- playwright
- openai
- Firefox（通过 playwright 安装）
- MiniMax API Key（或兼容 OpenAI API 的其他 Key）
