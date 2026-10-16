<p align="center"><img src="assets/icon.png" width="96" alt="BMW Guide"></p>

<h1 align="center">BMW Guide</h1>

<p align="center">Checklist overlay cho <b>Black Myth: Wukong</b>, tự tick theo file save.<br>
<b>Tiếng Việt</b> · <a href="README.en.md">English</a></p>

---

## Tính năng

- **Overlay luôn nổi trên game.** Cửa sổ trong suốt, bo góc, kéo thả được. Game cần để chế độ *Borderless / Windowed*.
- **Theo tiến trình game.** 6 chương xếp theo thứ tự miếu Thổ Địa, gồm boss, tinh phách, vật phẩm, phép, nhiệm vụ, khu ẩn, điểm thiền và mẹo.
- **Tự tick từ file save.** App đọc save của game (đã giải mã) và tự đánh dấu boss đã gặp trong Du Ký, vật phẩm, trang bị, tinh phách, phép và điểm thiền.
  - App chỉ đọc lại khi file save thay đổi, nên gần như không tốn CPU.
  - Mục tự tick có dấu ◆ màu xanh. Bạn vẫn tick hoặc bỏ tick tay được, và app nhớ lựa chọn của bạn.
- **Tự tìm file save** trên máy (Steam, Epic, bản cài riêng). Bạn cũng có thể chọn bằng tay trong ⚙.
- **Song ngữ Việt / Anh:** đổi trong ⚙ → Ngôn ngữ.
- **Chế độ gọn (F10):** chỉ hiện 3 bước tiếp theo kèm mẹo, chiếm rất ít chỗ.

## Cài đặt

1. Cài [Python 3.10+](https://www.python.org/downloads/) (nhớ chọn *Add to PATH*). App không cần thư viện ngoài.
2. Tải repo này về: **Code → Download ZIP**, rồi giải nén.
3. Chạy file tạo shortcut. Lệnh này tạo shortcut **BMW Guide** trên Desktop và Start Menu, với phím tắt **Ctrl+Alt+B**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
   ```
4. Mở game và chuyển sang **Borderless / Windowed**. Sau đó mở BMW Guide.

## Phím tắt

| Phím | Tác dụng |
|---|---|
| `F9` | Ẩn / hiện overlay |
| `F10` | Chuyển giữa chế độ gọn và đầy đủ |
| `Ctrl+Alt+B` | Mở app (từ shortcut Start Menu) |
| Lăn chuột | Cuộn danh sách |
| Kéo thanh tiêu đề | Di chuyển cửa sổ |

## Sửa checklist

Dữ liệu nằm ở `data/checklist.vi.md` và `data/checklist.en.md`, mỗi dòng có dạng:

```
- [Boss] Cổ Hộ Viện — boss đầu, thưởng Định Thân Pháp @card:102004
```

Mã `@loại:id` ở cuối dòng là ID trong game, dùng để tự tick. Các loại: `card` (Du Ký), `item`, `equip`, `soul` (tinh phách), `meditation`. Hai file phải giữ cùng thứ tự dòng.

## Ghi chú

- App chỉ **đọc** file save, không bao giờ ghi vào.
- Tên tiếng Việt theo bản Việt hoá của cộng đồng. Thông tin tham khảo từ game8, PowerPyx, bmwukong.info, BWIKI và 3DM.
- Đây là dự án cá nhân của người hâm mộ, không liên quan Game Science.
