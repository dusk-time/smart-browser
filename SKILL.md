---
name: smart-browser
description: 智能浏览器自动化，使用 Playwright + MiniMax LLM 实现自然语言驱动的网页浏览与搜索。当需要执行网页搜索、内容提取、自动化表单填写、多步骤网页操作时使用。触发场景：(1) 用户要求搜索某个主题并总结结果 (2) 需要从网页提取特定信息 (3) 执行需要多步骤交互的网页自动化任务 (4) 爬取需要 JS 渲染的页面。核心价值：LLM 作为大脑理解页面并决策下一步动作，Playwright 作为执行器操作浏览器。
---

# Smart Browser Skill

基于 Playwright + MiniMax LLM 的智能浏览器自动化框架。

## 架构

```
用户指令 → MiniMax LLM → JSON Action → Playwright 执行 → 页面反馈 → LLM 决策 → ...
```

## 核心工具函数

### parse_json(text)

解析 LLM 返回的 JSON，处理两种干扰情况：
1. **`<result>think</result>` 标签包裹**：MiniMax 模型用 `<result>` 标签包裹思考过程
2. **嵌套 JSON**：模型可能输出多行，其中只有一部分是目标 JSON

```python
def strip_think(text):
    """去除 <result> 标签包裹的思考内容"""
    text = re.sub(r'<result>.*?</result>', '', text, flags=re.DOTALL).strip()
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace+1]
    return text

def parse_json(text):
    cleaned = strip_think(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 提取第一个完整 JSON 对象
        depth, start = 0, -1
        for i, c in enumerate(cleaned):
            if c == '{':
                if start == -1: start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    return json.loads(cleaned[start:i+1])
    raise ValueError(f"No valid JSON found")
```

### SmartBrowser 类

```python
class SmartBrowser:
    def __init__(self, api_key, base_url="https://api.minimaxi.com/v1"):
        self.llm = OpenAI(api_key=api_key, base_url=base_url)
        self.history = []

    async def launch(self, browser_type="firefox"):
        """启动浏览器，browser_type 可选 firefox 或 chromium"""
        self.playwright = async_playwright()
        self.pw = await self.playwright.__aenter__()
        if browser_type == "firefox":
            self.browser = await self.pw.firefox.launch(headless=True, args=['--no-sandbox'])
        else:
            self.browser = await self.pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        self.page = await self.browser.new_page()
        return self

    async def goto(self, url): ...
    async def type(self, selector, text): ...
    async def click(self, selector): ...
    async def press(self, keys): ...
    async def wait(self, seconds=2): ...
    async def get_title(self): ...
    async def close(self): ...

    def ask_llm(self, instruction, page_context="", max_tokens=200, model="MiniMax-M2.7"):
        """让 LLM 根据页面状态决定下一步动作"""
        resp = self.llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"""你是浏览器助手。当前历史：{self.history[-3:]}
{page_context}
规则：
- Google搜索用 https://www.google.com.hk（避免重定向）
- Google搜索框selector是 textarea[name="q"]（不是input）
- 搜索完成后用done返回结果
- 只返回JSON，不输出思考过程
JSON格式：{{"action":"goto","url":"url"}} / {{"action":"click","selector":"css"}} / {{"action":"type","selector":"css","text":"text"}} / {{"action":"press","keys":"Enter"}} / {{"action":"wait","seconds":2}} / {{"action":"done","result":"结果文本"}}"""},
                {"role": "user", "content": instruction}
            ],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content
```

## LLM Action 协议

每次 LLM 调用返回以下 JSON action 之一：

| action | 参数 | 说明 |
|--------|------|------|
| goto | url | 导航到 URL |
| type | selector, text | 在元素中输入文本 |
| click | selector | 点击元素 |
| press | keys | 按键盘按键（如 Enter） |
| wait | seconds | 等待秒数 |
| done | result | 任务完成，返回结果 |

## 执行循环

```python
for i in range(max_steps=10):
    title = await browser.get_title()
    context = f"当前页面标题：{title[:80]}"
    raw = browser.ask_llm(instruction, context)
    d = parse_json(raw)
    action = d.get('action', '')
    if action == 'done':
        print(d['result'])
        break
    elif action == 'goto': await browser.goto(d['url'])
    elif action == 'click': await browser.click(d['selector'])
    elif action == 'type': await browser.type(d['selector'], d['text'])
    elif action == 'press': await browser.press(d['keys'])
    elif action == 'wait': await browser.wait(d.get('seconds', 2))
```

## 已知问题与解决方案

### 1. MiniMax 模型输出 `<result>` 标签包裹的思考过程

**问题**：MiniMax-M2/M2.7 模型用 `<result>` 标签包裹思考过程，导致 `json.loads()` 直接解析失败。

**解决**：使用 `strip_think()` 预处理。

### 2. Chrome v136+ CDP 安全限制

**问题**：browser-use 0.12.5 在 Chrome v136+ 下，`on_BrowserStartEvent` 超时。Issue #2941, #2993, #3196, #4291 均未修复。

**解决**：改用 Firefox（`browser_type="firefox"`），或使用 `simple_browser.py` 的同步 Playwright 方式。

### 3. Google 搜索框 selector

**注意**：Google 搜索框实际是 `<textarea name="q">`，不是 `<input>`。用 `textarea[name="q"]` 选择器。

## 脚本文件

- `scripts/smart_browser.py` - 完整实现（需要 `playwright`, `openai` 包）
- `scripts/simple_browser.py` - 轻量版本，仅做页面导航（需要 `playwright` 包）

## 环境要求

```bash
pip install playwright openai
playwright install firefox  # 或 chromium
```

或使用 uv：
```bash
uv run --with playwright --with openai python3.13 smart_browser.py "任务描述"
```
