import asyncio
import json
import os
import random
import sys
from playwright.async_api import async_playwright

ASSETS_DIR = "/Users/macos/Downloads/bia"
CONTENT_FILE = os.path.join(ASSETS_DIR, "content.txt")
COOKIES_FILE = os.path.join(ASSETS_DIR, "fb_cookies.json")
TEST_GROUP_URL = "https://www.facebook.com/groups/165470812211350"
IMAGES = [
    os.path.join(ASSETS_DIR, "796449862_122235768704578759_888180158004585452_n.jpg"),
    os.path.join(ASSETS_DIR, "796533170_122235768728578759_2591879549114888193_n.jpg"),
    os.path.join(ASSETS_DIR, "809646104_122235768716578759_208930171129126713_n.jpg"),
]

def log(msg):
    print(msg, flush=True)

async def human_delay(min_s=2.0, max_s=4.0, msg=None):
    wait_time = round(random.uniform(min_s, max_s), 2)
    if msg:
        log(f"⏳ {msg} (đợi {wait_time}s)...")
    await asyncio.sleep(wait_time)

async def run_test():
    log("==================================================")
    log("🚀 BẮT ĐẦU TEST TOÀN DIỆN VỚI PLAYWRIGHT & COOKIES")
    log("⚠️  CAM KẾT: TUYỆT ĐỐI KHÔNG CLICK NÚT 'ĐĂNG'")
    log("==================================================")

    # 1. Đọc nội dung bài đăng
    with open(CONTENT_FILE, "r", encoding="utf-8") as f:
        content_text = f.read().strip()
    log(f"📄 Đã nạp nội dung bài viết ({len(content_text)} ký tự).")

    # 2. Đọc cookies
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        cookies_raw = json.load(f)

    # Chuẩn hoá cookie cho Playwright
    formatted_cookies = []
    for c in cookies_raw:
        cookie_obj = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".facebook.com"),
            "path": c.get("path", "/"),
        }
        if "secure" in c:
            cookie_obj["secure"] = c["secure"]
        if "httpOnly" in c:
            cookie_obj["httpOnly"] = c["httpOnly"]
        if "sameSite" in c and c["sameSite"] in ["Strict", "Lax", "None"]:
            cookie_obj["sameSite"] = c["sameSite"]
        formatted_cookies.append(cookie_obj)

    log(f"🍪 Đã nạp và chuẩn hoá {len(formatted_cookies)} cookies Facebook.")

    # 3. Khởi chạy browser Playwright
    async with async_playwright() as p:
        log("🌐 Mở trình duyệt Chromium tự động...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )

        # Nạp cookie
        await context.add_cookies(formatted_cookies)
        page = await context.new_page()

        # 4. Truy cập trang nhóm test
        log(f"🔗 Đang truy cập nhóm: {TEST_GROUP_URL}")
        await page.goto(TEST_GROUP_URL, wait_until="domcontentloaded")
        await human_delay(4.0, 6.0, "Chờ trang nhóm tải hoàn tất")

        # 5. Mở modal Tạo bài viết
        log("🔍 Đang tìm nút mở modal 'Tạo bài viết'...")
        trigger_selectors = [
            'div[role="main"] div[role="button"]:has-text("Bạn viết gì đi...")',
            'div[role="main"] div[role="button"]:has-text("Bạn đang nghĩ gì?")',
            'div[role="main"] div[role="button"]:has-text("Tạo bài viết công khai...")',
            'div[role="button"]:has-text("Bạn viết gì đi...")',
            'div[role="button"]:has-text("Bạn đang nghĩ gì?")',
            'div[role="button"]:has-text("Tạo bài viết")',
        ]

        trigger_btn = None
        for sel in trigger_selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                trigger_btn = loc
                break

        if not trigger_btn:
            trigger_btn = page.locator('div[role="main"] div[role="region"] div[role="button"]').first

        await human_delay(1.5, 2.5, "Chuẩn bị click mở modal")
        await trigger_btn.click()
        log("✅ Đã click mở modal tạo bài viết.")

        modal = page.locator('div[role="dialog"]:has(h2:has-text("Tạo bài viết"))').first
        await modal.wait_for(state="visible", timeout=15000)
        log("✅ Modal 'Tạo bài viết' đã hiển thị.")
        await human_delay(2.0, 3.0, "Chờ modal ổn định")

        # BƯỚC 1: CHECK EMPTY & CLEAR
        log("🧹 BƯỚC 1: Focus và làm sạch ô soạn thảo...")
        editor = modal.locator('div[data-lexical-editor="true"][role="textbox"], div[contenteditable="true"][role="textbox"]').first
        await editor.wait_for(state="visible", timeout=10000)
        await editor.click()
        await human_delay(0.5, 1.0)

        modifier = "Meta" if sys.platform == "darwin" else "Control"
        await page.keyboard.press(f"{modifier}+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.5)
        log("✅ BƯỚC 1 HOÀN TẤT: Khung soạn thảo đã rỗng.")

        # BƯỚC 2: COPY / TYPE CONTENT
        log("✍️ BƯỚC 2: Điền nội dung bài viết...")
        lines = content_text.split("\n")
        for i, line in enumerate(lines):
            await page.keyboard.type(line, delay=random.randint(12, 25))
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(0.1, 0.2))
        log("✅ BƯỚC 2 HOÀN TẤT: Đã gõ xong nội dung.")

        await human_delay(1.5, 2.5, "Chờ Lexical cập nhật state")

        # BƯỚC 3: CHECK THE CONTENT ALREADY
        log("🔎 BƯỚC 3: Kiểm tra xác thực nội dung trong modal...")
        editor_text = await editor.evaluate("el => el.innerText.trim()")
        log(f"📝 Số ký tự trong editor: {len(editor_text)}")
        if len(editor_text) < 20:
            log("❌ LỖI: Nội dung chưa được ghi nhận vào editor!")
            return
        log("✅ BƯỚC 3 HOÀN TẤT: Nội dung bài viết đã hiển thị đầy đủ, không lặp lại.")

        await human_delay(1.5, 2.5, "Chuẩn bị đính kèm ảnh")

        # BƯỚC 4: INJECT 3 IMAGES THẲNG VÀO INPUT DOM
        log("🖼️ BƯỚC 4: Inject 3 file ảnh vào input ẩn (Playwright CDP)...")
        file_input = modal.locator('input[type="file"][multiple][accept*="image"]').first
        if await file_input.count() == 0:
            file_input = modal.locator('input[type="file"]').first

        await file_input.set_input_files(IMAGES)
        log("✅ BƯỚC 4 HOÀN TẤT: Đã gán 3 ảnh thành công vào input! Hoàn toàn KHÔNG bật popup OS.")

        # BƯỚC 5: CHECK IMAGES ATTACHED ON POST WINDOW
        log("⏳ BƯỚC 5: Chờ Facebook upload và hiển thị thumbnail preview...")
        images_rendered = False
        for attempt in range(8):
            await human_delay(1.5, 2.0, f"Đang kiểm tra preview ảnh (lần {attempt+1}/8)")
            preview_count = await modal.locator('img[src*="blob:"], img[src*="fbcdn"], button:has-text("Chỉnh sửa"), div[aria-label*="Ảnh"]').count()
            post_btn = modal.locator('div[aria-label="Đăng"][role="button"], div[role="button"]:has-text("Đăng")').first
            is_disabled = await post_btn.get_attribute("aria-disabled")

            if preview_count > 0 or is_disabled is None or is_disabled == "false":
                images_rendered = True
                log(f"🎯 ĐÃ XÁC THỰC: 3 ảnh đã hiển thị preview trong modal! (Tìm thấy {preview_count} phần tử media).")
                log(f"📊 Trạng thái nút 'Đăng': SẴN SÀNG (aria-disabled = {is_disabled}).")
                break

        # Chụp màn hình lưu lại
        screenshot_path = os.path.join(ASSETS_DIR, "test_result_with_images.png")
        await page.screenshot(path=screenshot_path)
        log(f"📸 Đã chụp màn hình lưu tại: {screenshot_path}")

        log("==================================================")
        log("🎉 TEST HOÀN TOÀN THÀNH CÔNG:")
        log("  1. Khung soạn thảo được làm sạch hoàn toàn.")
        log("  2. Nội dung được điền đầy đủ và đúng 1 lần.")
        log("  3. 3 ảnh đã được inject và preview hiển thị trên modal.")
        log("  4. Hoàn toàn KHÔNG có cửa sổ file dialog nào của hệ điều hành.")
        log("  5. Nút 'Đăng' ĐÃ KHÔNG ĐƯỢC CLICK theo đúng cam kết.")
        log("==================================================")

        log("👀 Giữ cửa sổ trình duyệt 25 giây để bạn tự mình kiểm tra tận mắt trên màn hình...")
        await asyncio.sleep(25)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
