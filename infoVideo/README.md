# Remotion Manga Studio (HTML5 16:9 & Python WebM Renderer)

Hệ thống template HTML5 thuần (16:9, chuẩn 1920x1080) phong cách Manga/Comic giới thiệu truyện và script Python xuất video định dạng `.webm` (không dùng NodeJS, React hay build tool phức tạp).

---

## 1. Cấu Trúc Các Cảnh (Scenes)
- **Cảnh 1: Giới thiệu kênh & Thông tin truyện**
  - Thông tin kênh: Avatar kênh, Tên kênh, Handle, Huy hiệu xác nhận.
  - Thông tin truyện: Tên truyện, Tên phụ, Tập phát sóng (Chapter/Episode), Huy hiệu manga, Tóm tắt nội dung ngắn, Ảnh bìa truyện 3D.
- **Cảnh 2: Danh sách bình luận nổi bật (Tùy chọn - Có thể bật/tắt)**
  - Hiển thị danh sách bình luận của bạn đọc / khán giả theo phong cách thẻ manga với avatar, tên, số lượt thích.
- **Cảnh 3: Thông tin Donate & Mã QR của chủ kênh**
  - Khung mã QR nổi bật với hiệu ứng quét tia laser.
  - Thông tin ngân hàng: Tên ngân hàng, Chi nhánh, Số tài khoản, Tên chủ tài khoản, Nội dung chuyển khoản.
  - Thông tin ví điện tử (MoMo / ZaloPay).
  - Lời nhắn cảm ơn từ đội ngũ kênh.
- **Cảnh 4: Lưu ý & Thông báo quan trọng (Tùy chọn - Có thể bật/tắt)**
  - 3 khối thông báo: Lịch ra tập mới, Bản quyền & tác quyền, Kêu gọi Like & Subscribe.

---

## 2. Hướng Dẫn Sử Dụng Trên Trình Duyệt (Web Studio)
Bạn có thể mở trực tiếp file `index.html` trên bất kỳ trình duyệt nào (Chrome, Edge, Cốc Cốc, Firefox):
1. **Xem trực tiếp**: Có đầy đủ thanh Timeline, nút Play/Pause, tua đến từng Frame, tua nhanh đến từng Cảnh.
2. **Chỉnh sửa thông số trực tiếp**: Bấm nút **"Chỉnh Sửa Thông Số"** ở góc phải để mở bảng nhập liệu (đổi Tên truyện, Tập, Tóm tắt, Ngân hàng, Bật/Tắt Cảnh 2 và Cảnh 4).
3. **Lưu file cấu hình**: Bấm nút **"Lưu config.json"** để tải về file cấu hình đã chỉnh sửa.
4. **Xuất video WebM ngay trên trình duyệt**: Bấm nút **"Xuất WebM (Trình Duyệt)"** để render trực tiếp không cần cài đặt gì thêm.

---

## 3. Hướng Dẫn Xuất Video Bằng Python (`render.py`)

Script Python `render.py` sử dụng Playwright và FFmpeg (đã có sẵn trên hệ thống của bạn) để render video WebM tỉ lệ chuẩn 16:9 (1920x1080), không có âm thanh.

### Lệnh Cơ Bản:
```powershell
python render.py --config config.json --output video_manga.webm
```

### Các Chế Độ Render:
1. **Chế độ Frame-by-frame (Mặc định - Chuẩn xác từng khung hình kiểu Remotion)**:
   ```powershell
   python render.py --config config.json --output intro.webm --mode frame
   ```
2. **Chế độ Realtime (Render siêu nhanh theo thời gian thực)**:
   ```powershell
   python render.py --config config.json --output intro_fast.webm --mode realtime
   ```
3. **Chế độ Nhập liệu tương tác qua Terminal**:
   ```powershell
   python render.py --interactive --output intro_custom.webm
   ```

### Các Tham Số Tùy Chọn:
- `--config`: Đường dẫn tới file JSON cấu hình (mặc định: `config.json`).
- `--output`: Đường dẫn và tên file `.webm` xuất ra (mặc định: `output.webm`).
- `--mode`: Chọn `frame` (chuẩn từng frame) hoặc `realtime` (nhanh).
- `--fps`: Số khung hình trên giây (mặc định: 30).
- `--bitrate`: Bitrate chất lượng video VP9 (mặc định: `4M`).

---

## 4. Cấu Trúc Thư Mục
```text
Tool html/
├── index.html        # Trang studio 16:9 (HTML5 thuần)
├── style.css         # Phong cách đồ họa Manga, comic frames & speedlines
├── app.js            # Engine timeline toán học & animation điều khiển frame
├── config.json       # File mẫu chứa toàn bộ thông số cấu hình video
├── render.py         # Script Python điều khiển xuất video ra .webm
├── assets/           # Thư mục chứa ảnh bìa, avatar, mã QR
│   ├── qr_code.png   # Ảnh mã QR donate
│   ├── cover.png     # Ảnh bìa truyện
│   ├── avatar.png    # Logo / Avatar kênh
│   ├── user1.png     # Avatar khán giả bình luận 1
│   ├── user2.png     # Avatar khán giả bình luận 2
│   └── user3.png     # Avatar khán giả bình luận 3
└── README.md         # Tài liệu hướng dẫn sử dụng
```
