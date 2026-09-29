import asyncio
import os
import sys
from playwright.async_api import async_playwright
from post_workflow_core import safe_post_to_group, log

ASSETS_DIR = "/Users/macos/Downloads/bia"
CONTENT_FILE = os.path.join(ASSETS_DIR, "content.txt")
TEST_GROUP_URL = "https://www.facebook.com/groups/165470812211350"
IMAGES = [
    os.path.join(ASSETS_DIR, "796449862_122235768704578759_888180158004585452_n.jpg"),
    os.path.join(ASSETS_DIR, "796533170_122235768728578759_2591879549114888193_n.jpg"),
    os.path.join(ASSETS_DIR, "809646104_122235768716578759_208930171129126713_n.jpg"),
]

async def main():
    log("==================================================")
    log("🧪 CHẠY TEST THỰC TẾ: TỰ ĐỘNG ĐIỀN VÀ INJECT ẢNH")
    log("⚠️  CHẾ ĐỘ: DRY RUN (KHÔNG BẤM NÚT ĐĂNG)")
    log("==================================================")

    # Đọc nội dung
    with open(CONTENT_FILE, "r", encoding="utf-8") as f:
        content_text = f.read().strip()

    user_data_dir = os.path.join(ASSETS_DIR, ".fb_session")
    os.makedirs(user_data_dir, exist_ok=True)

    # Nạp cookies nếu có
    cookies_file = os.path.join(ASSETS_DIR, "fb_cookies.json")
    cookies = []
    if os.path.exists(cookies_file):
        import json
        with open(cookies_file, "r") as f:
            cookies = json.load(f)
            log("🍪 Đã tìm thấy và nạp cookies từ fb_cookies.json.")

    async with async_playwright() as p:
        log("🌐 Mở trình duyệt Chrome giao diện trực quan...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 850},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        if cookies:
            await context.add_cookies(cookies)

        page = context.pages[0] if context.pages else await context.new_page()

        # Kiểm tra đăng nhập
        await page.goto(TEST_GROUP_URL, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        if "login" in page.url or await page.locator('input[name="email"]').count() > 0:
            log("👉 Cửa sổ trình duyệt đang mở: Xin vui lòng đăng nhập tài khoản Facebook của bạn vào cửa sổ đó (chỉ cần làm 1 lần này)!")
            while "login" in page.url or await page.locator('input[name="email"]').count() > 0:
                await asyncio.sleep(2)
            log("🎉 Đăng nhập thành công! Phiên đã được lưu tự động.")
            await page.goto(TEST_GROUP_URL, wait_until="domcontentloaded")
            await asyncio.sleep(4)

        # Chạy quy trình 5 bước an toàn
        success = await safe_post_to_group(
            page=page,
            group_url=TEST_GROUP_URL,
            content_text=content_text,
            image_paths=IMAGES,
            dry_run=True  # TUYỆT ĐỐI KHÔNG BẤM ĐĂNG
        )

        # Chụp ảnh màn hình lưu lại
        screenshot_path = os.path.join(ASSETS_DIR, "test_live_result.png")
        await page.screenshot(path=screenshot_path)
        log(f"\n📸 Đã chụp ảnh màn hình lưu tại: {screenshot_path}")

        log("\n==================================================")
        log("👀 Trình duyệt sẽ được GIỮ MỞ TRONG 30 GIÂY để bạn tận mắt kiểm tra nội dung và 3 ảnh trong modal!")
        log("==================================================")
        await asyncio.sleep(30)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
