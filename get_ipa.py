import json
import time
import playwright
from playwright.sync_api import sync_playwright
import playwright.sync_api

ENABLE_DEBUG_PAUSE = False

def debug_pause(msg: str):
    global ENABLE_DEBUG_PAUSE
    if not ENABLE_DEBUG_PAUSE:
        return
    
    input(f"[DEBUG PAUSE] {msg}")


def run():
    base_url = "https://decrypt.day/app/id1489932710"

    with sync_playwright() as p:
        # Setup 
        browser = p.firefox.launch(
            headless=False
        )

        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
        
        context = browser.new_context(
            user_agent=user_agent,
            #viewport={"width": 1280, "height": 800},
            #locale="zh-CN",
            #timezone_id="Asia/Shanghai"
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Open info page
        page = context.new_page()
        page.goto(base_url, timeout=60000)

        page.wait_for_load_state("domcontentloaded")
        
        if "Just a moment" in page.title() or "Cloudflare" in page.title() or "cf" in page.url:
            print("\n" + "="*50)
            print("[!] 检测到 Cloudflare 验证拦截！")
            print("[!] 请在弹出的 Firefox 窗口中手动完成验证。")
            print("[!] 确认进入正常页面后，请在下方终端按【回车键】继续...")
            print("="*50 + "\n")
            # input(">>> 等待用户操作，完成后按回车继续...")
        else:
            print("[-] 未检测到明显拦截，继续执行...")

        page.wait_for_load_state("domcontentloaded")

        
        debug_pause(">>> 按回车键发送 POST 请求...")

        # fetch download link via JS fetch
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
        # print(type(result))
        # print(result)
        assert isinstance(result, str), f"Invalid response type: {type(result)}"

        try:
            download_page_req = json.loads(result)
            assert download_page_req.get("type") == "success", f"Failed when request download path: {download_page_req}"
            dl_page_details: list = json.loads(download_page_req.get("data"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}\nRequest result: {result}")
        
        free_dl_path = ""
        try:
            free_dl_path = dl_page_details[dl_page_details.index("gofile.io") - 3]
        except IndexError:
            # fallback
            print("[!] Fallback: scanning for valid download path...")
            for e in dl_page_details:
                if not (isinstance(e, str) and len(e) == 21):
                    continue
                free_dl_path = e
                break
        
        # goto download page
        if not free_dl_path:
            raise ValueError(f"Cannot get download page path. Request: {download_page_req}")
    
        download_page_url = f"{base_url}/dl/{free_dl_path}"
        print(f"[-] Download Page: {download_page_url}")

        dl_page = context.new_page()
        dl_page.goto(download_page_url, referer=base_url)
        


        # 3. 定位并点击元素
        # 我们根据 "Get download link" 这个文本来定位父级容器（通常是 button 或 a 标签）
        #download_btn = page.locator("text=Get download link")
        
        # 如果该文字在按钮内，为了更精确，可以指定父级：
        btn = dl_page.locator("button.btn-download").filter(has_text="Get download link")
        btn.click()
        # btn.scroll_into_view_if_needed()
        # box = btn.bounding_box()
        # assert box is not None, "No box found"
    
        # center_x = box["x"] + box["width"] / 2
        # center_y = box["y"] + box["height"] / 2
        # dl_page.mouse.move(center_x, center_y)
        # dl_page.mouse.click(center_x, center_y)

        print("正在点击按钮...")
        time.sleep(5)

        # click button
        def handle_response(response: playwright.sync_api.Response):
            if "https://decrypt.day/" in response.url and response.request.method == "POST":
                print(f"\n[拦截到请求]: {response.url}")
                try:
                    # 获取响应体内容（如果是 JSON）
                    data = response.json()
                    print(f"[响应数据]: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except Exception:
                    print("[响应不是 JSON 格式]")

        # 注册监听
        dl_page.on("response", handle_response)
        btn.click()
        
        time.sleep(5)

        print("二次点击...")
        btn = dl_page.locator("button.btn-download").filter(has_text="Download")
        btn.click()

        debug_pause(">>> 按回车键关闭浏览器...")
        context.close()
        browser.close()

if __name__ == "__main__":
    run()
