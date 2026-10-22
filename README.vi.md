<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">Checklist overlay cho <b>Black Myth: Wukong</b>, tự tick theo file save.<br>
<b>Tiếng Việt</b> · <a href="README.md">English</a> · <a href="CHANGELOG.md">Changelog</a></p>

---

## Tính năng

- **Overlay luôn nổi trên game, không bao giờ cướp quyền điều khiển của game.** Mặc định chuột đi xuyên qua app xuống game (🔒); nhấn phím **`** (dấu huyền, cạnh số 1) để dùng app (🖱), nhấn lần nữa để khoá lại. Game cần để chế độ *Borderless / Windowed*.
- **Theo tiến trình game.** 6 chương xếp theo thứ tự miếu Thổ Địa, gồm boss, tinh phách, vật phẩm, phép, nhiệm vụ, khu ẩn, điểm thiền và mẹo.
- **Tick hoàn toàn theo file save, không tick tay.** App đọc save của game và tự đánh dấu:
  - boss/quái đã gặp trong Du Ký, vật phẩm, trang bị, tinh phách, phép, điểm thiền;
  - miếu Thổ Địa đã mở (⛩ cạnh tên khu).
  - App chỉ đọc lại khi file save thay đổi, nên gần như không tốn CPU.
  - Dòng mờ có dấu `·` là hướng dẫn mà save không ghi lại (cốt truyện, nhiệm vụ, vật phẩm đã dùng hết…), không tính vào tiến độ.
- **Tự tìm file save** trên máy (Steam, Epic, bản cài riêng). Bạn cũng có thể chọn bằng tay trong ⚙.
- **Song ngữ Việt / Anh:** đổi trong ⚙ → Ngôn ngữ.
- **Chế độ gọn (F10):** chỉ hiện 3 bước tiếp theo kèm mẹo, chiếm rất ít chỗ.
- **Icon ở khay hệ thống** (cạnh đồng hồ) cho biết app đang chạy. Bấm trái để ẩn/hiện app; bấm phải để mở menu: ẩn/hiện, khoá chuột, bản đồ, thoát.
- **Minimap (F11):** bản đồ quanh nhân vật nằm ngay trên checklist, có mũi tên hướng nhìn, cập nhật theo thời gian thực.
  - Hiện rương, Lạc Già Hương Đằng, Tam Đông Trùng, boss, đầu mục, tinh phách, điểm thiền, miếu, NPC…
  - Điểm đã xong tự ẩn theo save: miếu đã mở, boss/đầu mục đã hạ, tinh phách và vật phẩm có tên riêng đã có, rương đã mở. Điểm rương, vật phẩm và NPC cũng tự xoá khi bạn đứng gần mà không còn gì ở đó.
  - Lăn chuột trên map để phóng to / thu nhỏ; rê chuột lên một điểm để xem tên.
  - **Chỉ đường theo lối đi:** bấm một dòng hoặc tên khu trong checklist (khi đã mở khoá chuột bằng phím `). Đường nét đứt đi theo thung lũng và lối vẽ trên bản đồ, không cắt thẳng qua núi, kèm quãng đường đi thật và hướng rẽ cho đoạn kế tiếp (ví dụ "→ bên phải"). Đi lệch thì đường tự tính lại. Dòng không có điểm riêng sẽ chỉ tới miếu của khu. Bấm vào map để bỏ chỉ đường.
  - App chỉ **đọc** bộ nhớ game để lấy vị trí, không chèn DLL, không ghi gì.
- **Toàn bản đồ (F12):** mở bản đồ lớn của cả khu hiện tại nổi trên game, có mọi điểm chưa xong và vị trí của bạn theo thời gian thực.
  - Lăn chuột để phóng to / thu nhỏ, kéo để di chuyển, rê chuột lên điểm để xem tên.
  - Bấm vào một điểm để được chỉ đường tới đó; checklist tự cuộn tới dòng của điểm đó và nháy sáng.
  - Bấm F12 lần nữa hoặc ✕ để đóng.
- **Nhiệm vụ chính nổi bật:** các bước cốt truyện có mũi tên ➤ vàng, chữ đậm, để không lạc mạch chính.

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
| `` ` `` (phím dấu huyền, cạnh số 1) | Khoá / mở khoá chuột (🔒 chuột xuyên xuống game, 🖱 bấm được vào app) |
| `F9` | Ẩn / hiện overlay |
| `F10` | Chuyển giữa chế độ gọn và đầy đủ |
| `F11` | Ẩn / hiện minimap |
| `F12` | Mở / đóng toàn bản đồ |
| `Ctrl+Alt+B` | Mở app (từ shortcut Start Menu) |
| Lăn chuột | Cuộn danh sách |
| Kéo thanh tiêu đề | Di chuyển cửa sổ |

## Sửa checklist

Dữ liệu nằm ở `data/checklist.vi.md` và `data/checklist.en.md`, mỗi dòng có dạng:

```
- [Boss] Cổ Hộ Viện — boss đầu, thưởng Định Thân Pháp @card:102004
```

Mã `@loại:id` ở cuối dòng là ID trong game, dùng để tự tick. Các loại: `card` (Du Ký), `item`, `equip`, `soul` (tinh phách), `meditation`, `shrine` (gắn trên tiêu đề khu). Dòng không có mã sẽ hiện dạng hướng dẫn. Hai file phải giữ cùng thứ tự dòng. Bản exe đọc thư mục `data/` cạnh file exe nếu có, nên bạn sửa được checklist mà không cần build lại.

## Kiểm tra

Chạy `python smoke_test.py` để kiểm tra checklist, asset, giải mã save, tìm đường, tra vị trí trên map và chạy thử app vài giây. Bài kiểm tra dùng thư mục tạm nên không đụng tới tiến độ của bạn.

## Ghi chú

- App chỉ **đọc** file save, không bao giờ ghi vào.
- Tên tiếng Việt theo bản Việt hoá của cộng đồng. Thông tin tham khảo từ game8, PowerPyx, bmwukong.info, BWIKI và 3DM.
- Ảnh bản đồ, icon và dữ liệu điểm của minimap lấy từ [jaskang/wukong-minimap](https://github.com/jaskang/wukong-minimap) (Apache-2.0), xem `assets/maps/NOTICE.txt`.
- Đây là dự án cá nhân của người hâm mộ, không liên quan Game Science.
