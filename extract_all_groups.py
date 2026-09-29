import asyncio
import csv
import json
import os
import re
from playwright.async_api import async_playwright

ASSETS_DIR = "/Users/macos/Downloads/bia"
COOKIES_FILE = os.path.join(ASSETS_DIR, "fb_cookies.json")
OUTPUT_JSON = os.path.join(ASSETS_DIR, "facebook_joined_groups.json")
OUTPUT_CSV = os.path.join(ASSETS_DIR, "facebook_joined_groups.csv")
JOINS_URL = "https://www.facebook.com/groups/joins/?nav_source=tab"

def log(msg):
    print(msg, flush=True)

async def main():
    log("==================================================")
    log("🚀 BẮT ĐẦU TRÍCH XUẤT TOÀN BỘ NHÓM FACEBOOK ĐÃ THAM GIA")
    log("==================================================")

    # Đọc cookies
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        cookies_raw = json.load(f)

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

    async with async_playwright() as p:
        log("🌐 Mở trình duyệt...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        await context.add_cookies(formatted_cookies)
        page = await context.new_page()

        log(f"🔗 Điều hướng đến: {JOINS_URL}")
        await page.goto(JOINS_URL, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        log("📜 Đang cuộn trang xuống tận đáy để nạp hết 100% danh sách nhóm...")
        prev_count = 0
        unchanged_count = 0

        # JavaScript thu thập nhóm liên tục trong quá trình cuộn
        extracted_groups = {}

        while True:
            # Thu thập nhóm đang có trên DOM
            current_batch = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href*="/groups/"]'));
                const results = [];
                for (const a of links) {
                    const href = a.href;
                    // Bỏ qua các link điều hướng hệ thống của Facebook
                    if (
                        href.includes('/groups/feed/') || 
                        href.includes('/groups/discover/') || 
                        href.includes('/groups/joins/') || 
                        href.includes('/groups/create/') ||
                        href.includes('/search/')
                    ) continue;

                    // Chuẩn hoá URL nhóm
                    const match = href.match(/https:\\/\\/www\\.facebook\\.com\\/groups\\/([^\\/?#]+)/);
                    if (match) {
                        const groupIdOrVanity = match[1];
                        const cleanUrl = `https://www.facebook.com/groups/${groupIdOrVanity}/`;
                        
                        // Lấy tên nhóm từ text hoặc aria-label
                        let name = a.innerText.trim();
                        if (!name) name = a.getAttribute('aria-label') || '';
                        
                        // Nếu thẻ a chỉ là ảnh, tìm thẻ text gần nhất
                        if (!name || name.length < 2) {
                            const parentContainer = a.closest('div[role="listitem"]') || a.parentElement?.parentElement;
                            if (parentContainer) {
                                const textSpans = Array.from(parentContainer.querySelectorAll('span')).map(s => s.innerText.trim()).filter(Boolean);
                                if (textSpans.length > 0) name = textSpans[0];
                            }
                        }

                        if (cleanUrl && name && name !== 'Xem nhóm' && !name.includes('Đã tham gia')) {
                            results.push({ name: name.split('\\n')[0], url: cleanUrl, id: groupIdOrVanity });
                        }
                    }
                }
                return results;
            }""")

            for g in current_batch:
                if g["url"] not in extracted_groups or len(extracted_groups[g["url"]]["name"]) < len(g["name"]):
                    extracted_groups[g["url"]] = g

            current_count = len(extracted_groups)

            # Cuộn xuống
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.8)

            log(f"  ⏳ Đã nạp được: {current_count} nhóm...")

            if current_count == prev_count:
                unchanged_count += 1
                # Thử cuộn thêm một chút hoặc ấn phím PageDown
                await page.keyboard.press("PageDown")
                await asyncio.sleep(2)
                # Nếu không có nhóm mới sau 5 lần kiểm tra thì đã đến tận đáy trang
                if unchanged_count >= 5:
                    log("🏁 Đã chạm đáy trang! Không còn nhóm nào để tải thêm.")
                    break
            else:
                unchanged_count = 0
                prev_count = current_count

        final_groups = list(extracted_groups.values())
        log(f"\n🎉 TỔNG CỘNG ĐÃ TRÍCH XUẤT ĐƯỢC: {len(final_groups)} NHÓM!")

        # 1. Lưu ra JSON
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(final_groups, f, ensure_ascii=False, indent=2)
        log(f"💾 Đã lưu JSON: {OUTPUT_JSON}")

        # 2. Lưu ra CSV
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "url", "id"])
            writer.writeheader()
            writer.writerows(final_groups)
        log(f"💾 Đã lưu CSV: {OUTPUT_CSV}")

        # Copy ra thư mục Downloads để bạn dễ xem
        user_dl_json = "/Users/macos/Downloads/facebook_joined_groups.json"
        user_dl_csv = "/Users/macos/Downloads/facebook_joined_groups.csv"
        with open(user_dl_json, "w", encoding="utf-8") as f:
            json.dump(final_groups, f, ensure_ascii=False, indent=2)
        with open(user_dl_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "url", "id"])
            writer.writeheader()
            writer.writerows(final_groups)

        log("✅ Đã cập nhật cả vào thư mục /Users/macos/Downloads!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
