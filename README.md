<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">Checklist overlay cho <b>Black Myth: Wukong</b>, tự tick theo file save.<br>
<b>Tiếng Việt</b> · <a href="README.en.md">English</a></p>

---

## Tính năng

- **Overlay luôn nổi trên game.** Cửa sổ trong suốt, bo góc, kéo thả được. Game cần để chế độ *Borderless / Windowed*.
- **Theo tiến trình game.** 6 chương xếp theo thứ tự miếu Thổ Địa, gồm boss, tinh phách, vật phẩm, phép, nhiệm vụ, khu ẩn, điểm thiền và mẹo.
- **Tick hoàn toàn theo file save, không tick tay.** App đọc save của game và tự đánh dấu:
  - boss/quái đã gặp trong Du Ký, vật phẩm, trang bị, tinh phách, phép, điểm thiền;
  - miếu Thổ Địa đã mở (⛩ cạnh tên khu).
  - App chỉ đọc lại khi file save thay đổi, nên gần như không tốn CPU.
  - Dòng mờ có dấu `·` là hướng dẫn mà save không ghi lại (cốt truyện, nhiệm vụ, vật phẩm đã dùng hết…), không tính vào tiến độ.
- **Tự tìm file save** trên máy (Steam, Epic, bản cài riêng). Bạn cũng có thể chọn bằng tay trong ⚙.
- **Song ngữ Việt / Anh:** đổi trong ⚙ → Ngôn ngữ.
- **Chế độ gọn (F10):** chỉ hiện 3 bước tiếp theo kèm mẹo, chiếm rất ít chỗ.
- **Minimap (F11):** bản đồ quanh nhân vật nằm ngay trên checklist, có mũi tên hướng nhìn, cập nhật theo thời gian thực.
  - Hiện rương, Lạc Già Hương Đằng, Tam Đông Trùng, boss, đầu mục, tinh phách, điểm thiền, miếu, NPC…
  - Điểm đã xong sẽ tự ẩn: miếu đã mở ẩn ngay theo save. Rương, boss, tinh phách, vật phẩm ẩn khi save ghi nhận bạn vừa mở/hạ/nhặt chúng ở gần đó (tính từ lúc bật app; những thứ lấy trước đó vẫn hiện).
  - Lăn chuột trên map để phóng to / thu nhỏ; rê chuột lên một điểm để xem tên.
  - **Bấm vào một dòng hoặc tên khu trong checklist** để map nhảy tới đó, có vòng đỏ đánh dấu, đường chỉ hướng và khoảng cách (đường thẳng, không phải đường né địa hình). Dòng không có điểm riêng sẽ nhảy tới miếu của khu. Bấm vào map để quay lại theo nhân vật.
  - App chỉ **đọc** bộ nhớ game để lấy vị trí, không chèn DLL, không ghi gì.

## Cài đặt

**Cách nhanh:** tải `BMW_Guide.exe` ở mục [Releases](https://github.com/hieuday88/BMW-Guide/releases) rồi bấm đúp để chạy. Không cần cài gì thêm.

**Chạy từ mã nguồn:**
1. Cài [Python 3.10+](https://www.python.org/downloads/) (nhớ chọn *Add to PATH*). App không cần thư viện ngoài.
2. Tải repo này về: **Code → Download ZIP**, rồi giải nén.
3. Chạy file tạo shortcut. Lệnh này tạo shortcut **BMW Guide** trên Desktop và Start Menu, với phím tắt **Ctrl+Alt+B**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
   ```

Khi chơi, chuyển game sang **Borderless / Windowed**.

## Phím tắt

| Phím | Tác dụng |
|---|---|
| `F9` | Ẩn / hiện overlay |
| `F10` | Chuyển giữa chế độ gọn và đầy đủ |
| `F11` | Ẩn / hiện minimap |
| `Ctrl+Alt+B` | Mở app (từ shortcut Start Menu) |
| Lăn chuột | Cuộn danh sách |
| Kéo thanh tiêu đề | Di chuyển cửa sổ |

## Sửa checklist

Dữ liệu nằm ở `data/checklist.vi.md` và `data/checklist.en.md`, mỗi dòng có dạng:

```
- [Boss] Cổ Hộ Viện — boss đầu, thưởng Định Thân Pháp @card:102004
```

Mã `@loại:id` ở cuối dòng là ID trong game, dùng để tự tick. Các loại: `card` (Du Ký), `item`, `equip`, `soul` (tinh phách), `meditation`, `shrine` (gắn trên tiêu đề khu). Dòng không có mã sẽ hiện dạng hướng dẫn. Hai file phải giữ cùng thứ tự dòng. Bản exe đọc thư mục `data/` cạnh file exe nếu có, nên bạn sửa được checklist mà không cần build lại.

## Ghi chú

- App chỉ **đọc** file save, không bao giờ ghi vào.
- Tên tiếng Việt theo bản Việt hoá của cộng đồng. Thông tin tham khảo từ game8, PowerPyx, bmwukong.info, BWIKI và 3DM.
- Ảnh bản đồ, icon và dữ liệu điểm của minimap lấy từ [jaskang/wukong-minimap](https://github.com/jaskang/wukong-minimap) (Apache-2.0), xem `assets/maps/NOTICE.txt`.
- Đây là dự án cá nhân của người hâm mộ, không liên quan Game Science.
