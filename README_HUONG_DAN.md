# Hướng Dẫn Tự Động Đăng Bài Facebook Bằng GitHub Actions (Cron Job)

Toàn bộ hệ thống tự động hoá đã được thiết lập hoàn chỉnh trong thư mục `/Users/macos/Downloads/bia`.

---

## 🌟 Quy Trình Kiểm Tra 5 Bước Chuẩn Xác (Đã Tích Hợp Sẵn)
Mỗi lần đăng vào một nhóm, script sẽ thực hiện tuần tự:
1. **Check Empty**: Focus vào ô soạn thảo, chọn tất cả và xoá sạch. Xác thực ô soạn thảo **100% trống**.
2. **Copy / Type Content**: Nhập nội dung bài viết từ `content.txt` với tốc độ gõ ngẫu nhiên (delay tự nhiên giữa các ký tự).
3. **Verify Content**: Kiểm tra lại DOM của modal, đảm bảo nội dung đã xuất hiện đầy đủ và đúng độ dài.
4. **Inject Images**: Gán trực tiếp 3 file ảnh vào thẻ `input[type="file"]` qua DOM. **Tuyệt đối không bật cửa sổ File Picker của hệ điều hành.**
5. **Verify Attached**: Chờ và kiểm tra các thumbnail preview ảnh trong cửa sổ modal, đồng thời xác thực nút **"Đăng"** đã chuyển sang trạng thái sẵn sàng.
6. **Post / Dry Run**: Nếu chế độ `DRY_RUN=True` thì dừng lại an toàn không bấm Đăng; nếu `DRY_RUN=False` thì bấm Đăng và đợi xác nhận. Giãn cách ngẫu nhiên 30–60s giữa các nhóm.

---

## 🚀 Các Bước Đưa Lên GitHub (Chạy Miễn Phí 100% Trên Cloud)

### Bước 1: Lấy Cookies Facebook (Làm 1 lần duy nhất)
1. Cài extension [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) trên Chrome.
2. Mở tab Facebook bạn đang đăng nhập -> bấm biểu tượng Cookie-Editor -> chọn **Export** -> chọn **Export as JSON**.
3. Toàn bộ chuỗi JSON cookie sẽ được copy vào Clipboard của bạn.

### Bước 2: Tạo Repository GitHub Private
1. Tạo một repository mới trên GitHub (đặt ở chế độ **Private** để bảo mật cookies và hình ảnh).
2. Đẩy toàn bộ thư mục `/Users/macos/Downloads/bia` lên repo:
   ```bash
   cd /Users/macos/Downloads/bia
   git init
   git add .
   git commit -m "feat: setup facebook auto poster cron"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo-name>.git
   git push -u origin main
   ```

### Bước 3: Thêm Secret trên GitHub
1. Vào repository trên GitHub -> vào tab **Settings** -> **Secrets and variables** -> **Actions**.
2. Bấm **New repository secret**:
   - **Name**: `FB_COOKIES_JSON`
   - **Secret**: Paste toàn bộ chuỗi JSON cookies bạn vừa copy ở Bước 1.
3. Bấm **Add secret**.

### Bước 4: Chạy thử hoặc để Cron tự chạy
- **Chạy thử thủ công**: Vào tab **Actions** trên GitHub -> chọn **Facebook Auto Poster Cron** -> bấm **Run workflow**. Bạn có thể chọn bật `dry_run = true` để chạy test thử, hoặc `dry_run = false` để đăng thật.
- **Tự động theo lịch**: GitHub Actions sẽ tự động chạy theo lịch cron được cấu hình (ví dụ mỗi ngày 2 lần vào khung giờ bạn muốn).

---

## 📁 Cấu Trúc Các File Trong Thư Mục
- `post_workflow_core.py`: Lõi xử lý 5 bước kiểm tra DOM và inject file.
- `github_cron_poster.py`: Script điều phối chạy theo lô nhóm (mặc định 5 nhóm mỗi lượt), tự động lưu lịch sử `posted_history.json` để không bao giờ bị đăng trùng nhóm.
- `.github/workflows/facebook_post_cron.yml`: File cấu hình cron job tự động cho GitHub Actions.
- `content.txt`: Nội dung bài viết thanh lý đồ bi-a.
- 3 file ảnh `.jpg`: Ảnh sản phẩm đính kèm.
- `facebook_joined_groups.json`: Danh sách 654 nhóm Facebook đã trích xuất.
