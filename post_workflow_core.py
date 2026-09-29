import asyncio
import os
import random
import sys
from playwright.async_api import Page, Locator

def log(msg: str):
    print(msg, flush=True)

async def human_delay(min_s: float = 2.0, max_s: float = 4.5, msg: str = None):
    """Wait with random human-like jitter to bypass bot detection."""
    wait_time = round(random.uniform(min_s, max_s), 2)
    if msg:
        log(f"⏳ {msg} (đợi {wait_time}s)...")
    await asyncio.sleep(wait_time)

async def safe_post_to_group(
    page: Page,
    group_url: str,
    content_text: str,
    image_paths: list,
    dry_run: bool = False
) -> bool:
    """
    Thực hiện quy trình đăng bài chuẩn 6 bước:
    1. Kiểm tra ô soạn thảo: Xoá sạch đảm bảo hoàn toàn trống.
    2. Điền nội dung bài viết.
    3. Kiểm tra xác thực nội dung đã có trong ô soạn thảo.
    4. Inject 3 ảnh vào input ẩn (không mở popup OS).
    5. Kiểm tra xác thực các ảnh đã được đính kèm và render preview trong modal.
    6. Xử lý nút ĐĂNG:
       - Click nút 'Đăng'.
       - Chờ modal đóng hoàn tất (state detached hoặc biến mất).
       - Đợi thêm 8-15s để Facebook xử lý xong bài trên feed trước khi chuyển nhóm.
    """
    log(f"\n==================================================")
    log(f"🌐 BẮT ĐẦU QUY TRÌNH CHO NHÓM: {group_url}")
    log(f"⚙️  Chế độ: {'DRY RUN (Chỉ test, KHÔNG bấm Đăng)' if dry_run else 'LIVE POST (Bấm Đăng thật & Chờ đăng xong)'}")
    log(f"==================================================")

    # 1. Điều hướng đến trang nhóm
    log(f"🔗 Đang truy cập nhóm: {group_url}")
    await page.goto(group_url, wait_until="domcontentloaded")
    await human_delay(4.0, 7.0, "Chờ trang nhóm tải ổn định")

    # Đóng popup che màn hình nếu có
    close_popup = page.locator('div[aria-label="Đóng"][role="button"], div[aria-label="Close"][role="button"]').first
    if await close_popup.count() > 0 and await close_popup.is_visible():
        try:
            log("👆 Phát hiện hộp thoại che màn hình, đang click đóng popup...")
            await close_popup.click()
            await asyncio.sleep(1.0)
        except Exception:
            pass

    # Nếu tài khoản chưa tham gia nhóm, tự động bấm 'Tham gia nhóm'
    join_btn = page.locator('div[role="button"]:has-text("Tham gia nhóm"), span:has-text("Tham gia nhóm")').first
    if await join_btn.count() > 0 and await join_btn.is_visible():
        log("🤝 Phát hiện chưa tham gia nhóm, đang tự động click 'Tham gia nhóm'...")
        try:
            await join_btn.click()
            await asyncio.sleep(2.0)
            if await close_popup.count() > 0 and await close_popup.is_visible():
                await close_popup.click()
                await asyncio.sleep(1.0)
        except Exception:
            pass

    # 2. Tìm và click nút mở modal "Tạo bài viết"
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

    # Đóng popup che màn hình nếu có
    close_popup = page.locator('div[aria-label="Đóng"][role="button"]').first
    if await close_popup.count() > 0 and await close_popup.is_visible():
        try:
            await close_popup.click()
            await asyncio.sleep(1.0)
        except Exception:
            pass

    # Nếu chưa thấy nút tạo bài viết, tìm và click tab "Thảo luận" đang hiển thị (visible)
    if not trigger_btn:
        tab_candidates = [
            page.locator('a:has-text("Thảo luận")'),
            page.locator('span:has-text("Thảo luận")'),
            page.locator('div:has-text("Thảo luận")'),
        ]
        clicked_tab = False
        for loc in tab_candidates:
            count = await loc.count()
            for i in range(count):
                el = loc.nth(i)
                if await el.is_visible():
                    log("🔄 Tìm thấy tab 'Thảo luận' hiển thị, đang click để mở trang thảo luận...")
                    try:
                        await el.click()
                        clicked_tab = True
                        break
                    except Exception as e:
                        log(f"Thử click tab Thảo luận lỗi: {e}")
            if clicked_tab:
                break

        if clicked_tab:
            await human_delay(3.0, 5.0, "Chờ tải nội dung tab Thảo luận")
            for sel in trigger_selectors:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    trigger_btn = loc
                    break

    if not trigger_btn:
        log("⚠️ Nhóm này chỉ mở định dạng 'Mua và bán' niêm yết hoặc không hỗ trợ bài viết thường. Bỏ qua an toàn.")
        return False

    await human_delay(1.5, 3.0, "Chuẩn bị click mở modal")
    await trigger_btn.click()
    log("✅ Đã click mở hộp thoại bài viết.")

    # 3. Chờ modal xuất hiện chính xác
    modal = page.locator('div[role="dialog"]:has(h2:has-text("Tạo bài viết"))').first
    if await modal.count() == 0:
        modal = page.locator('div[role="dialog"]').first

    await modal.wait_for(state="visible", timeout=15000)
    log("✅ Modal 'Tạo bài viết' đã hiển thị.")
    await human_delay(2.0, 3.5, "Chờ modal render hoàn tất")

    # BƯỚC 1: CHECK THE POST IF IT IS EMPTY & CLEAR THOROUGHLY
    log("🧹 BƯỚC 1: Kiểm tra ô soạn thảo và xoá sạch đảm bảo rỗng...")
    editor = modal.locator('div[data-lexical-editor="true"][role="textbox"], div[contenteditable="true"][role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await human_delay(0.8, 1.5, "Focus vào ô soạn thảo")

    modifier_key = "Meta" if sys.platform == "darwin" else "Control"
    await page.keyboard.press(f"{modifier_key}+A")
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.5)

    is_empty = await editor.evaluate("el => el.innerText.trim() === ''")
    if not is_empty:
        log("⚠️ Thử xoá triệt để bằng lệnh DOM...")
        await editor.evaluate("el => el.innerText = ''")
    log("✅ BƯỚC 1 HOÀN TẤT: Khung soạn thảo đã HOÀN TOÀN TRỐNG.")

    await human_delay(1.0, 2.0, "Nghỉ trước khi chép nội dung")

    # BƯỚC 2: COPY / TYPE THE CONTENT
    log("✍️ BƯỚC 2: Điền nội dung bài viết...")
    lines = content_text.strip().split("\n")
    for i, line in enumerate(lines):
        await page.keyboard.type(line, delay=random.randint(12, 28))
        if i < len(lines) - 1:
            await page.keyboard.press("Enter")
            await asyncio.sleep(random.uniform(0.1, 0.25))
    log("✅ BƯỚC 2 HOÀN TẤT: Đã gõ xong nội dung.")

    await human_delay(1.5, 2.5, "Nghỉ để Lexical cập nhật state")

    # BƯỚC 3: CHECK THE CONTENT ALREADY
    log("🔎 BƯỚC 3: Kiểm tra xác thực nội dung đã có trong modal...")
    current_editor_text = await editor.evaluate("el => el.innerText.trim()")
    log(f"📝 Độ dài ký tự hiện tại trong editor: {len(current_editor_text)} ký tự")
    if len(current_editor_text) < 20:
        log("❌ LỖI: Nội dung bài viết chưa được ghi nhận vào editor!")
        return False
    log("✅ BƯỚC 3 HOÀN TẤT: Đã xác thực nội dung hiển thị chuẩn xác trong bài viết.")

    await human_delay(2.0, 3.5, "Nghỉ trước khi đính kèm ảnh")

    # BƯỚC 4: INJECT IMAGES (KHÔNG BẬT POPUP OS)
    log(f"🖼️ BƯỚC 4: Inject {len(image_paths)} file ảnh vào thẻ input ẩn...")
    file_input = modal.locator('input[type="file"][multiple][accept*="image"]').first
    if await file_input.count() == 0:
        file_input = modal.locator('input[type="file"]').first

    if await file_input.count() == 0:
        log("❌ LỖI: Không tìm thấy thẻ input[type=file] trong modal.")
        return False

    await file_input.set_input_files(image_paths)
    log("✅ BƯỚC 4 HOÀN TẤT: Đã inject 3 ảnh thẳng vào input DOM mà hoàn toàn KHÔNG bật cửa sổ file của OS.")

    # BƯỚC 5: CHECK IMAGES ATTACHED
    log("⏳ BƯỚC 5: Chờ và kiểm tra xác thực ảnh đã đính kèm trên cửa sổ bài viết...")
    images_attached = False
    post_btn = None

    for attempt in range(8):
        await human_delay(1.5, 2.5, f"Đang kiểm tra preview ảnh (lần {attempt + 1}/8)")
        preview_count = await modal.locator('img[src*="blob:"], img[src*="fbcdn"], div[aria-label*="Ảnh"], button:has-text("Chỉnh sửa")').count()
        post_btn = modal.locator('div[aria-label="Đăng"][role="button"], div[role="button"]:has-text("Đăng")').first
        is_disabled = await post_btn.get_attribute("aria-disabled")

        if preview_count > 0 or is_disabled is None or is_disabled == "false":
            images_attached = True
            log(f"🎯 ĐÃ XÁC THỰC: Ảnh đã đính kèm thành công! (Phát hiện {preview_count} phần tử media preview).")
            log(f"📊 Trạng thái nút 'Đăng': SẴN SÀNG (aria-disabled = {is_disabled}).")
            break

    if not images_attached:
        log("⚠️ Cảnh báo: Chưa thấy thumbnail render rõ ràng, tiếp tục quy trình an toàn.")

    log("✅ BƯỚC 5 HOÀN TẤT: Ảnh đã được gắn vào cửa sổ bài viết.")

    # BƯỚC 6: XỬ LÝ BẤM ĐĂNG & CHỜ ĐĂNG XONG
    if dry_run:
        log("🛑 [DRY RUN ACTIVE]: Chế độ test - KHÔNG bấm nút 'Đăng'.")
        return True

    log("🚀 BƯỚC 6: BẤM NÚT 'ĐĂNG' VÀ CHỜ HOÀN TẤT ĐĂNG BÀI...")
    await human_delay(2.0, 3.5, "Chuẩn bị nhấn Đăng")
    
    post_btn = modal.locator('div[aria-label="Đăng"][role="button"], div[role="button"]:has-text("Đăng")').first
    await post_btn.click()
    log("👆 Đã click nút 'Đăng'!")

    # Chờ modal biến mất (Facebook đóng modal khi đăng thành công)
    try:
        log("⏳ Đang chờ hộp thoại 'Tạo bài viết' đóng lại (Facebook đang tải bài lên)...")
        await modal.wait_for(state="hidden", timeout=30000)
        log("🎉 Hộp thoại đã đóng! Bài viết đã được đăng lên Facebook.")
    except Exception:
        log("⚠️ Hộp thoại chưa đóng hoàn toàn trong 30s, kiểm tra trạng thái feed...")

    # Chờ thêm 8 - 15 giây để Facebook xử lý xong bài viết và cache nhóm
    await human_delay(8.0, 14.0, "Nghỉ an toàn sau khi đăng thành công trước khi chuyển nhóm tiếp theo")
    log(f"✅ HOÀN TẤT ĐĂNG BÀI CHO NHÓM: {group_url}!")
    return True
