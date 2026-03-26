"""轻量浏览器自动化 - 使用系统Chrome"""
import os
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('all_proxy', None)
os.environ.pop('ALL_PROXY', None)

from playwright.sync_api import sync_playwright
import sys

def browse(url, action=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        page = browser.new_page()
        page.goto(url, timeout=30000)
        
        if action:
            result = action(page)
        else:
            result = {
                'title': page.title(),
                'url': page.url,
                'content': page.content()[:500]
            }
        
        browser.close()
        return result

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.baidu.com'
    result = browse(url)
    print("Title:", result.get('title', 'N/A'))
    print("URL:", result.get('url', 'N/A'))
    if 'content' in result:
        print("Content preview:", result['content'][:200])
