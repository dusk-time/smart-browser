"""智能浏览器自动化 - 基于 Playwright + MiniMax LLM"""
import asyncio
import json
import re
import sys
from openai import OpenAI
from playwright.async_api import async_playwright

def strip_think(text):
    """去除 MiniMax-M2/M2.7 模型的 <result> 标签包裹的思考内容"""
    text = re.sub(r'<result>.*?</result>', '', text, flags=re.DOTALL).strip()
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace+1]
    return text

def parse_json(text):
    """解析 LLM 返回的 JSON，处理思考标签和嵌套 JSON"""
    cleaned = strip_think(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    depth = 0
    start = -1
    for i, c in enumerate(cleaned):
        if c == '{':
            if start == -1:
                start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(cleaned[start:i+1])
                except:
                    pass
    raise ValueError(f"No valid JSON found in: {cleaned[:100]}")

class SmartBrowser:
    def __init__(self, api_key=None, base_url="https://api.minimaxi.com/v1"):
        self.llm = OpenAI(api_key=api_key, base_url=base_url)
        self.browser = None
        self.page = None
        self.playwright = None
        self.history = []

    async def launch(self, browser_type="firefox"):
        self.playwright = async_playwright()
        self.pw = await self.playwright.__aenter__()
        if browser_type == "firefox":
            self.browser = await self.pw.firefox.launch(headless=True, args=['--no-sandbox'])
        else:
            self.browser = await self.pw.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
        self.page = await self.browser.new_page()
        return self

    async def goto(self, url):
        if 'google.com' in url and 'google.com.hk' not in url:
            url = url.replace('https://www.google.com', 'https://www.google.com.hk')
        await self.page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        self.history.append(f"goto: {url}")

    async def type(self, selector, text):
        try:
            ta = self.page.locator('textarea[name="q"]')
            if await ta.count() > 0:
                await ta.fill(text, timeout=10000)
                self.history.append(f"type: textarea -> {text}")
                return
        except:
            pass
        await self.page.fill(selector, text, timeout=10000)
        self.history.append(f"type: {selector} -> {text}")

    async def click(self, selector):
        await self.page.click(selector, timeout=10000)
        await asyncio.sleep(1)
        self.history.append(f"click: {selector}")

    async def wait(self, seconds=2):
        await asyncio.sleep(seconds)

    async def press(self, keys):
        await self.page.keyboard.press(keys)
        await asyncio.sleep(2)
        self.history.append(f"press: {keys}")

    async def get_title(self):
        return await self.page.title()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.__aexit__(None, None, None)

    def ask_llm(self, instruction, page_context="", max_tokens=200, model="MiniMax-M2.7"):
        resp = self.llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"""你是浏览器助手。当前历史：{self.history[-3:] if self.history else ['无']}
{page_context}

规则：
- Google搜索请用 https://www.google.com.hk
- Google搜索框selector是 textarea[name="q"]（不是input）
- 如果搜索已完成，用done返回结果
- 不要输出思考过程，只返回JSON

JSON格式：
{{"action":"goto","url":"url"}}
{{"action":"click","selector":"css selector"}}
{{"action":"type","selector":"selector","text":"text"}}
{{"action":"press","keys":"Enter"}}
{{"action":"wait","seconds":2}}
{{"action":"done","result":"最终结果文本"}}"""},
                {"role": "user", "content": instruction}
            ],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content

async def main():
    if len(sys.argv) < 2:
        print("用法: python smart_browser.py <任务描述>")
        return

    instruction = ' '.join(sys.argv[1:])
    browser = SmartBrowser()

    try:
        await browser.launch()
        print("浏览器已启动 (Firefox)", flush=True)

        for i in range(10):
            title = await browser.get_title()
            context = f"当前页面标题：{title[:80]}"
            print(f"\n步骤 {i+1}: {context}", flush=True)

            raw = browser.ask_llm(instruction, context)
            print(f"LLM: {raw[:120]}", flush=True)

            try:
                d = parse_json(raw)
                action = d.get('action', '')

                if action == 'done':
                    print(f"\n完成: {d['result']}", flush=True)
                    break
                elif action == 'goto':
                    await browser.goto(d['url'])
                elif action == 'type':
                    await browser.type(d.get('selector', 'textarea[name="q"]'), d['text'])
                elif action == 'click':
                    await browser.click(d['selector'])
                elif action == 'press':
                    await browser.press(d['keys'])
                elif action == 'wait':
                    await browser.wait(d.get('seconds', 2))
                else:
                    print(f"未知动作: {action}", flush=True)
                    break
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}", flush=True)
                break
            except Exception as e:
                print(f"执行失败: {e}", flush=True)
                break
        else:
            print("达到最大步数", flush=True)

    finally:
        await browser.close()
        print("\n浏览器已关闭", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
