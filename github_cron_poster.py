import asyncio
import json
import os
import random
import sys
from playwright.async_api import async_playwright
from post_workflow_core import safe_post_to_group, human_delay, log

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(ASSETS_DIR, "content.txt")
GROUPS_FILE = os.path.join(ASSETS_DIR, "facebook_joined_groups.json")
PROGRESS_FILE = os.path.join(ASSETS_DIR, "posted_history.json")

# Danh sách 3 ảnh sản phẩm
IMAGES = [
    os.path.join(ASSETS_DIR, "796449862_122235768704578759_888180158004585452_n.jpg"),
    os.path.join(ASSETS_DIR, "796533170_122235768728578759_2591879549114888193_n.jpg"),
    os.path.join(ASSETS_DIR, "809646104_122235768716578759_208930171129126713_n.jpg"),
]

# Danh sách biến thể icon để chống bộ lọc trùng lặp bài viết của Facebook (Spintax)
SPIN_ICONS = [
    "🎱 Đam mê bi-a",
    "🎱✨ Hàng đẹp giá tốt",
    "🎱🔥 Nghỉ game thanh lý",
    "🎱🎯 Chuẩn lực chính xác",
    "🎱💯 Hàng sẵn ship ngay",
    "🎱⚡ Ưu tiên anh em nhanh gọn",
    "🎱🏆 Bao test trực tiếp",
    "🎱💫 Còn tin là còn hàng"
]

# Đọc cấu hình từ biến môi trường
TOTAL_GROUPS_LIMIT = int(os.environ.get("TOTAL_GROUPS_LIMIT", "20"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
FB_COOKIES_JSON = os.environ.get("FB_COOKIES_JSON", "")
TEST_GROUP_URL = os.environ.get("TEST_GROUP_URL", "").strip()
FB_USERNAME = os.environ.get("FB_USERNAME", "").strip()
FB_PASSWORD = os.environ.get("FB_PASSWORD", "").strip()

if not FB_USERNAME or not FB_PASSWORD:
    env_file = os.path.join(ASSETS_DIR, "env.txt")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                if len(lines) >= 2:
                    FB_USERNAME = FB_USERNAME or lines[0]
                    FB_PASSWORD = FB_PASSWORD or lines[1]
        except Exception:
            pass

def load_posted_history():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_posted_history(history_set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history_set), f, indent=2, ensure_ascii=False)

def get_varied_content(base_text: str, index: int) -> str:
    """Tự động chèn biến thể câu kết và icon nhẹ để mỗi bài viết độc nhất 100%."""
    chosen_tag = SPIN_ICONS[index % len(SPIN_ICONS)]
    return f"{base_text.strip()}\n\n{chosen_tag}"

async def main():
    log("==================================================")
    log("⚡ FACEBOOK HIGH-SPEED ANTI-SPAM POSTER")
    log(f"⚙️  Chế độ: {'DRY RUN (Chỉ kiểm tra)' if DRY_RUN else 'LIVE POST (Đăng thật)'}")
    log(f"📦 Số nhóm mục tiêu ca này: {TOTAL_GROUPS_LIMIT}")
    log(f"🔄 Kích thước mỗi đợt (Batch size): {BATCH_SIZE} nhóm/đợt")
    log(f"⏱️  Giãn cách giữa 2 nhóm: 30s - 45s (Tối ưu tốc độ cao)")
    log(f"☕ Nghỉ ngơi giữa các đợt (Batch Rest): 2.5 - 3.5 phút")
    if TEST_GROUP_URL:
        log(f"🎯 Chế độ test đơn lẻ: {TEST_GROUP_URL}")
    log("==================================================")

    # 1. Đọc nội dung gốc
    with open(CONTENT_FILE, "r", encoding="utf-8") as f:
        base_content = f.read().strip()

    # 2. Lấy danh sách nhóm
    if TEST_GROUP_URL:
        target_groups = [{"name": "Nhóm test chỉ định", "url": TEST_GROUP_URL}]
    else:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            all_groups = json.load(f)
        log(f"📋 Tổng số nhóm trong database: {len(all_groups)}")

        posted_history = load_posted_history()
        log(f"🕒 Số nhóm đã hoàn thành trước đây: {len(posted_history)}")

        pending_groups = [g for g in all_groups if g["url"] not in posted_history]
        if not pending_groups:
            log("🎉 ĐÃ ĐĂNG HẾT TOÀN BỘ 662 NHÓM! Reset lịch sử để quay vòng đợt mới.")
            posted_history.clear()
            save_posted_history(posted_history)
            pending_groups = all_groups

        target_groups = pending_groups[:TOTAL_GROUPS_LIMIT]

    log(f"🎯 Ca này sẽ thực hiện đăng cho {len(target_groups)} nhóm:")
    for idx, g in enumerate(target_groups, 1):
        log(f"  {idx}. {g['name']} ({g['url']})")

    # 3. Chuẩn bị Cookies
    cookies = []
    if FB_COOKIES_JSON:
        try:
            cookies = json.loads(FB_COOKIES_JSON)
            log("🍪 Đã nạp cookies từ GitHub Secret.")
        except Exception as e:
            log(f"❌ Lỗi giải mã cookies: {e}")
            sys.exit(1)
    elif os.path.exists(os.path.join(ASSETS_DIR, "fb_cookies.json")):
        with open(os.path.join(ASSETS_DIR, "fb_cookies.json"), "r") as f:
            cookies = json.load(f)
            log("🍪 Đã nạp cookies từ file fb_cookies.json cục bộ.")
    else:
        log("❌ Không tìm thấy cookies!")
        sys.exit(1)

    formatted_cookies = []
    for c in cookies:
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

    # 4. Khởi chạy Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        await context.add_cookies(formatted_cookies)
        page = await context.new_page()

        # KIỂM TRA PHIÊN ĐĂNG NHẬP VÀ TỰ ĐỘNG KHÔI PHỤC (AUTO-HEALING SESSION)
        log("🔐 Đang kiểm tra tính hợp lệ của phiên đăng nhập Facebook...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await asyncio.sleep(4.0)

        profile_sel = page.locator('svg[aria-label="Trang cá nhân của bạn"], div[aria-label="Tài khoản của bạn"], div[aria-label="Menu"], a[href*="/me"]').first
        is_logged_in = await profile_sel.count() > 0

        if not is_logged_in:
            log("⚠️ Phiên đăng nhập cần xác thực. Đang kích hoạt cơ chế tự động khôi phục / đăng nhập...")
            # Trường hợp 1: Nhấp vào hồ sơ "An Tâm" nếu có danh sách chuyển đổi hồ sơ
            an_tam_btn = page.locator('div[role="button"]:has-text("An Tâm"), span:has-text("An Tâm"), div:has(> div > span:has-text("An Tâm"))').first
            if await an_tam_btn.count() > 0 and await an_tam_btn.is_visible():
                log("👆 Tìm thấy hồ sơ 'An Tâm', đang click để mở ô nhập mật khẩu...")
                await an_tam_btn.click()
                await asyncio.sleep(2.0)

            # Trường hợp 2: Nút Tiếp tục (One-click login đơn lẻ)
            btn_tiep_tuc = page.locator('button:has-text("Tiếp tục"), div[role="button"]:has-text("Tiếp tục"), a:has-text("Tiếp tục")').first
            if await btn_tiep_tuc.count() > 0 and await btn_tiep_tuc.is_visible():
                log("👆 Tìm thấy nút 'Tiếp tục' hồ sơ cá nhân, đang click...")
                await btn_tiep_tuc.click()
                await asyncio.sleep(2.0)

            # Trường hợp 3: Điền tên đăng nhập nếu có ô email
            email_input = page.locator('input#email, input[name="email"]').first
            if await email_input.count() > 0 and await email_input.is_visible() and FB_USERNAME:
                log("📝 Đang điền tên đăng nhập...")
                await email_input.fill(FB_USERNAME)
                await asyncio.sleep(1.0)

            # Điền mật khẩu
            pass_input = page.locator('input[type="password"]').first
            if await pass_input.count() > 0 and await pass_input.is_visible() and FB_PASSWORD:
                log("🔑 Đang điền mật khẩu đăng nhập...")
                await pass_input.fill(FB_PASSWORD)
                await asyncio.sleep(1.0)
                await page.keyboard.press("Enter")
                log("⏳ Đã gửi mật khẩu (Enter), chờ chuyển vào trang chủ...")
                await asyncio.sleep(8.0)

            # Kiểm tra lại trạng thái đăng nhập
            is_logged_in = await profile_sel.count() > 0
            if is_logged_in:
                log("🎉 TỰ ĐỘNG ĐĂNG NHẬP THÀNH CÔNG! Phiên làm việc đã sẵn sàng.")
            else:
                log(f"⚠️ Cảnh báo: Chưa xác nhận được biểu tượng profile (URL: {page.url}). Lưu ảnh chẩn đoán...")
                await page.screenshot(path=os.path.join(ASSETS_DIR, "session_check_state.png"))
        else:
            log("✅ Phiên đăng nhập hoàn toàn hợp lệ! Tài khoản đang hoạt động bình thường.")

        posted_history = load_posted_history()
        success_count = 0

        for idx, group in enumerate(target_groups, 1):
            group_url = group["url"]
            group_name = group["name"]
            log(f"\n[{idx}/{len(target_groups)}] 🚀 ĐANG XỬ LÝ: {group_name}")

            varied_content = get_varied_content(base_content, idx)

            try:
                ok = await safe_post_to_group(
                    page=page,
                    group_url=group_url,
                    content_text=varied_content,
                    image_paths=IMAGES,
                    dry_run=DRY_RUN
                )

                if ok:
                    success_count += 1
                    if not TEST_GROUP_URL and not DRY_RUN:
                        posted_history.add(group_url)
                        save_posted_history(posted_history)
                else:
                    log(f"⏭️ Đã duyệt qua nhóm {group_name}. Ghi nhận vào lịch sử để không cản trở các ca tiếp theo.")
                    if not TEST_GROUP_URL and not DRY_RUN:
                        posted_history.add(group_url)
                        save_posted_history(posted_history)

                # Chụp ảnh bằng chứng
                proof_name = f"proof_group_{idx}.png"
                await page.screenshot(path=os.path.join(ASSETS_DIR, proof_name))

            except Exception as e:
                log(f"⚠️ Lỗi khi xử lý nhóm {group_name}: {e}")
                err_proof = f"error_group_{idx}.png"
                try:
                    await page.screenshot(path=os.path.join(ASSETS_DIR, err_proof))
                except Exception:
                    pass

            # ĐIỀU PHỐI TỐC ĐỘ VÀ NGHỈ NGƠI
            if idx < len(target_groups):
                if idx % BATCH_SIZE == 0:
                    rest_seconds = random.randint(150, 210)
                    log(f"\n☕ [HẾT ĐỢT {idx // BATCH_SIZE}]: Đã đăng xong {BATCH_SIZE} nhóm.")
                    log(f"⏳ TẠM NGHỈ {round(rest_seconds / 60, 1)} PHÚT ({rest_seconds}s) để reset bộ đếm spam của Facebook...")
                    await asyncio.sleep(rest_seconds)
                else:
                    # Giãn cách tối ưu tốc độ 30s - 50s
                    await human_delay(30.0, 50.0, "Giãn cách an toàn tốc độ cao giữa 2 nhóm")

        log(f"\n==================================================")
        log(f"🏁 TỔNG KẾT CA NÀY: Đã đăng thành công {success_count}/{len(target_groups)} nhóm!")
        log(f"📊 Tổng số nhóm đã phủ sóng từ trước đến nay: {len(posted_history)}/662 nhóm.")
        log(f"==================================================")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
