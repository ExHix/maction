import json
import time
import os
import sys
from playwright.sync_api import sync_playwright

def run():
    # 目标 URL
    base_url = "https://decrypt.day/app/id1489932710"

    print(f"[Script] 启动 Playwright...")
    
    with sync_playwright() as p:
        # 【核心修改 1】添加启动参数，防止在 Docker/Action 中崩溃
        browser = p.firefox.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-software-rasterizer"
            ]
        )

        # 设置 User Agent
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
        
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True
        )

        # 屏蔽 WebDriver 检测
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()
        
        print(f"[Script] 正在打开页面: {base_url}")
        try:
            page.goto(base_url, timeout=90000)
            page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            print(f"[Script] 页面加载超时或失败: {e}")
            # 超时也继续尝试，因为有时候只是资源加载慢

        # Cloudflare 检测
        title = page.title()
        if "Just a moment" in title or "Cloudflare" in title:
            print("\n" + "!"*50)
            print("[!] ⚠️ 检测到 Cloudflare 拦截！")
            print("[!] 请进入 VNC 桌面，在 Firefox 中手动点击验证。")
            print("[!] 脚本将等待 30 秒供您操作...")
            print("!"*50 + "\n")
            time.sleep(30)
        else:
            print("[-] 页面加载正常，继续执行...")

        # 获取下载链接逻辑
        print("[Script] 正在获取下载配置...")
        
        try:
            result = page.evaluate("""
                async () => {
                    const formData = new FormData();
                    formData.append('data', '163,101,97,112,112,73,100,120,25,99,108,57,115,101,52,48,116,113,48,48,97,98,100,111,102,119,113,116,103,111,118,48,122,115,103,118,101,114,115,105,111,110,101,54,46,50,46,48,105,105,115,80,114,101,109,105,101,114,247');

                    const resp = await fetch('$BASE_PAGE_URL$?/files', {
                        method: 'POST',
                        body: formData,
                    });
                    return await resp.text();
                }
            """.replace("$BASE_PAGE_URL$", base_url))

            download_page_req = json.loads(result)
            if download_page_req.get("type") != "success":
                print(f"[!] API 请求未返回 success: {download_page_req}")
            
            dl_page_details = json.loads(download_page_req.get("data"))
            
            free_dl_path = ""
            # 尝试定位 gofile 附近的链接
            try:
                if "gofile.io" in dl_page_details:
                    free_dl_path = dl_page_details[dl_page_details.index("gofile.io") - 3]
            except:
                pass
            
            # Fallback 扫描
            if not free_dl_path:
                print("[!] Fallback: 扫描可用下载路径...")
                for e in dl_page_details:
                    if isinstance(e, str) and len(e) == 21:
                        free_dl_path = e
                        break
            
            if not free_dl_path:
                print("[X] 无法找到下载路径，停止脚本。")
                print(f"调试数据: {dl_page_details}")
                # 不关闭浏览器，方便用户调试
                print(">>> 浏览器保持开启，请进入 VNC 手动操作。")
                while True: time.sleep(10)

            download_page_url = f"{base_url}/dl/{free_dl_path}"
            print(f"[-] 跳转到下载页: {download_page_url}")

            dl_page = context.new_page()
            dl_page.goto(download_page_url, referer=base_url)

            # 点击第一个 "Get download link"
            print("[Script] 寻找 'Get download link' 按钮...")
            try:
                btn = dl_page.locator("button.btn-download").filter(has_text="Get download link")
                btn.wait_for(state="visible", timeout=10000)
                btn.click()
                print("[Script] 点击成功，等待 5 秒...")
                time.sleep(5)
            except Exception as e:
                print(f"[!] 点击第一步失败 (可能是 Cloudflare): {e}")

            # 点击第二个 "Download" 并处理下载
            print(
