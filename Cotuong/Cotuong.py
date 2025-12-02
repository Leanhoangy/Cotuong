import pygame
from board import Board
import sys
from ai import ai_move, random_move
import random
import csv
import os
import threading

pygame.init()
pygame.font.init()
file_path = "highscore.csv"
DEBUG = False
last_attacker = None  # (r, c, piece)
last_checked_king = None  # (r, c)
check_overlay_end = 0
check_overlay_player = None
CHECK_OVERLAY_DEFAULT_MS = 1200
MESSAGE_OVERLAY_DEFAULT_MS = 1200
message_overlay_text = None
message_overlay_end = 0
# AI background task state
ai_thinking = False
ai_move_result = None
ai_thread = None
# Per-move thinking time (seconds) per player — change as desired
THINK_TIME_PER_MOVE = {"red": 60, "black": 60}
# Timestamp (ms) when current player's turn started
turn_start_time = pygame.time.get_ticks()
# Pause / resign controls
paused = False
pause_button_rect = None
resign_button_rect = None
paused_remaining_ms = None

def supports_vietnamese(font_name):
    try:
        font_path = pygame.font.match_font(font_name)
        if not font_path:
            return False

        font = pygame.font.Font(font_path, 32)
        test_text = "Chọn chế độ chơi"
        rendered = font.render(test_text, True, (0, 0, 0))
        # Nếu render thành công → chấp nhận
        return True
    except:
        return False


def find_best_vietnamese_font():
    preferred_fonts = [
        "segoeui", "tahoma", "calibri", "verdana",
        "arialunicode", "arialuni", "arial unicode ms",
        "micross"
    ]

    for f in preferred_fonts:
        if supports_vietnamese(f):
            return pygame.font.match_font(f)

    for f in pygame.font.get_fonts():
        if supports_vietnamese(f):
            return pygame.font.match_font(f)

    return None


VIET_FONT_PATH = find_best_vietnamese_font()


FONT_TITLE = pygame.font.Font(VIET_FONT_PATH, 50)
FONT_BUTTON = pygame.font.Font(VIET_FONT_PATH, 36)
FONT_TIME = pygame.font.Font(VIET_FONT_PATH, 12)
FONT_BXH = pygame.font.Font(VIET_FONT_PATH, 22)


# Kiểm tra nếu chưa có file thì tạo (với điểm riêng biệt cho PvP và Vs Máy)
if not os.path.exists(file_path):
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Tên","DiemPvP","Thắng","Thua","DiemMay","VsMáy"])
        writer.writeheader()
#nhập tên người chơi
def input_player_name(player_num):
    """Hiển thị màn hình nhập tên và trả về tên."""
    name = ""
    font = FONT_BUTTON
    input_rect = pygame.Rect(width//2 - 150, height//2 - 30, 300, 60)
    active = True

    while active:
        screen.fill((200, 180, 150))

        # Con trỏ nhấp nháy
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""

        # Hiển thị text
        display_name = name + cursor
        txt_surface = FONT_BUTTON.render(f"Tên người chơi {player_num}: {display_name}", True, (0,0,0))
        screen.blit(txt_surface, (input_rect.x+5, input_rect.y+15))

        # Vẽ khung input
        pygame.draw.rect(screen, (0,0,0), input_rect, 2)
        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if name.strip() != "":
                        active = False
                        return name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                else:
                    # Chỉ chấp nhận chữ cái, số, khoảng trắng
                    if event.unicode.isalpha() or event.unicode.isspace() or event.unicode.isdigit():
                        name += event.unicode

                # Giới hạn ký tự trong ô input
                while font.size(name)[0] > input_rect.width - 10:
                    name = name[:-1]

#lưu kết quả
def save_result(name, win, vs_machine=False, num_moves=0):
    """Cập nhật kết quả trận đấu vào highscore.csv với hệ điểm động riêng biệt.
    Quy ước điểm:
      - Điểm khởi tạo: 1200 (cho mỗi chế độ)
      - Thắng: cộng điểm dựa trên số nước đi (càng ít nước càng nhiều điểm)
        Công thức: bonus = max(100, 500 - num_moves * 5)
      - Thua: -50 điểm
    File lưu: Tên, DiemPvP, Thắng, Thua, DiemMay, VsMáy.
    """
    file_path = "highscore.csv"
    data = {}
    # Đọc dữ liệu hiện có
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ten = row.get("Tên", "").strip()
                if not ten:
                    continue
                diem_pvp = int(row.get("DiemPvP", 0)) if row.get("DiemPvP", "") != "" else 0
                thang = int(row.get("Thắng", 0)) if row.get("Thắng", "") != "" else 0
                thua = int(row.get("Thua", 0)) if row.get("Thua", "") != "" else 0
                diem_may = int(row.get("DiemMay", 0)) if row.get("DiemMay", "") != "" else 0
                vsmay = int(row.get("VsMáy", 0)) if row.get("VsMáy", "") != "" else 0
                data[ten] = {"DiemPvP": diem_pvp, "Thắng": thang, "Thua": thua, "DiemMay": diem_may, "VsMáy": vsmay}
    except FileNotFoundError:
        pass
    except Exception as e:
        print("Lỗi đọc highscore:", e)

    # Khởi tạo nếu chưa có (điểm mặc định 1200 cho mỗi chế độ)
    if name not in data:
        data[name] = {"DiemPvP": 1200, "Thắng": 0, "Thua": 0, "DiemMay": 1200, "VsMáy": 0}

    # Tính điểm thưởng khi thắng dựa trên số nước đi
    if win:
        bonus = max(100, 500 - num_moves * 5)
    else:
        bonus = -50

    # Cập nhật theo loại trận (điểm riêng biệt)
    if vs_machine:
        if win:
            data[name]["VsMáy"] += 1
        data[name]["DiemMay"] += bonus
    else:  # PvP
        if win:
            data[name]["Thắng"] += 1
        else:
            data[name]["Thua"] += 1
        data[name]["DiemPvP"] += bonus

    # Ghi ngược lại file
    try:
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["Tên", "DiemPvP", "Thắng", "Thua", "DiemMay", "VsMáy"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ten, v in data.items():
                writer.writerow({
                    "Tên": ten,
                    "DiemPvP": v["DiemPvP"],
                    "Thắng": v["Thắng"],
                    "Thua": v["Thua"],
                    "DiemMay": v["DiemMay"],
                    "VsMáy": v["VsMáy"]
                })
    except Exception as e:
        print("Lỗi ghi highscore:", e)


def leaderboard():
    """Hiển thị bảng xếp hạng với hai phần riêng biệt:
      1. PvP: Tên | DiemPvP | Thắng | Thua
      2. Vs Máy: Tên | DiemMay | VsMáy
    """
    file_path = "highscore.csv"
    entries = []
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    entries.append({
                        "Tên": row.get("Tên", ""),
                        "DiemPvP": int(row.get("DiemPvP", 0)),
                        "Thắng": int(row.get("Thắng", 0)),
                        "Thua": int(row.get("Thua", 0)),
                        "DiemMay": int(row.get("DiemMay", 0)),
                        "VsMáy": int(row.get("VsMáy", 0))
                    })
                except ValueError:
                    pass
    except FileNotFoundError:
        entries = []

    # PvP: hiển thị tất cả người chơi có ít nhất 1 trận PvP (Thắng > 0 hoặc Thua > 0)
    pvp_entries = [e for e in entries if e["Thắng"] > 0 or e["Thua"] > 0]
    pvp_sorted = sorted(pvp_entries, key=lambda x: (-x["DiemPvP"], -x["Thắng"], x["Thua"], x["Tên"]))
    
    # Vs Máy: hiển thị tất cả người chơi từng chơi vs máy
    vsm_entries = [e for e in entries if e["VsMáy"] > 0 or (e["DiemMay"] != 1200)]
    vsm_sorted = sorted(vsm_entries, key=lambda x: (-x["DiemMay"], -x["VsMáy"], x["Tên"]))

    back_rect = pygame.Rect(20, 20, 120, 40)
    # Monospace font (simple alignment); fallback to FONT_BXH if not found
    font_rows = None
    for cand in ["Consolas", "Courier New", "Lucida Console"]:
        try:
            font_rows = pygame.font.SysFont(cand, 20)
            break
        except Exception:
            continue
    if font_rows is None:
        font_rows = FONT_BXH
    running_lb = True
    while running_lb:
        screen.fill((220, 210, 200))
        title = FONT_BUTTON.render("Bảng xếp hạng", True, (0,0,0))
        screen.blit(title, (width//2 - title.get_width()//2, 20))

        # Fixed positions to avoid overlap
        # PvP block (left) and Vs Máy block (fine-tuned further right)
        pvp_x = 30
        sep_x = width//2 + 40   # separator moved a bit more to the right
        vm_x = sep_x + 50       # Vs Máy block starts further from separator for clearer gap
        # If exceeding window, clamp
        if vm_x > width - 200:
            vm_x = width - 200
            sep_x = vm_x - 30
        pygame.draw.line(screen, (0,0,0), (sep_x, 70), (sep_x, height-40), 1)

        # PvP section
        pvp_title = FONT_BXH.render("Người vs Người", True, (0,0,0))
        screen.blit(pvp_title, (pvp_x, 90))
        hdr_pvp = "#  Tên   Điểm   Thắng  Thua"
        screen.blit(font_rows.render(hdr_pvp, True, (0,0,0)), (pvp_x, 120))
        for i, row in enumerate(pvp_sorted[:15], start=1):
            name = row['Tên'][:7]
            line = f"{i:<2} {name:<5} {row['DiemPvP']:<8} {row['Thắng']:<4} {row['Thua']}"
            screen.blit(font_rows.render(line, True, (0,0,0)), (pvp_x, 120 + i*24))

        # Vs Máy section
        vm_title = FONT_BXH.render("Chơi với Máy", True, (0,0,0))
        screen.blit(vm_title, (vm_x, 90))
        hdr_vm = "#  Tên     Điểm"
        screen.blit(font_rows.render(hdr_vm, True, (0,0,0)), (vm_x, 120))
        for i, row in enumerate(vsm_sorted[:15], start=1):
            name = row['Tên'][:7]
            line = f"{i:<2} {name:<7} {row['DiemMay']}"
            screen.blit(font_rows.render(line, True, (0,0,0)), (vm_x, 120 + i*24))

        draw_button(back_rect, "Quay lại", (180,200,220))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_rect.collidepoint(event.pos):
                    running_lb = False
        pygame.display.flip()
        clock.tick(60)

def check_game_over(player):
    """Kiểm tra player có thua vì bị chiếu bí hay không."""
    # nếu tướng chết thì obviously game over
    if find_king(board, player) is None:
        return True

    # nếu bị chiếu và không còn nước hợp lệ → chiếu bí
    if is_checked(player, board) and not has_any_legal_move(player):
        return True

    return False


def reset_game():
    global board, current_player, selected
    board = Board()             # tạo lại bàn cờ từ đầu
    current_player = "red"      # đỏ đi trước
    selected = None             # bỏ chọn
    global move_history
    move_history = []
    set_turn_start()



def show_winner(winner):
    """Hiển thị overlay thắng với hai nút: Chơi lại và Menu."""
    global current_player, selected, game_mode

    win_screen = pygame.display.get_surface()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    
    # Font hiển thị tên người thắng
    font = pygame.font.SysFont("arial", 40, bold=True)
    winner_name = player_red_name if winner == "red" else player_black_name
    text_surface = FONT_BUTTON.render(f"{winner_name} THẮNG!", True, (255, 255, 0))
    text_rect = text_surface.get_rect(center=(width//2, height//2 - 50))

    # Nút "Chơi lại" và "Menu"
    btn_play_again_rect = pygame.Rect(width//2 - 160, height//2 + 80, 150, 60)
    btn_menu_rect = pygame.Rect(width//2 + 10, height//2 + 80, 150, 60)

    # Trạng thái xác nhận chơi lại (PvP cần 2 người đồng ý)
    confirm_red = False
    confirm_black = False
    confirm_message = ""

    waiting = True
    while waiting:
        draw_board()
        win_screen.blit(overlay, (0,0))
        win_screen.blit(text_surface, text_rect)

        # Vẽ nút với hiệu ứng hover
        mouse_pos = pygame.mouse.get_pos()
        play_again_color = (80, 180, 80) if btn_play_again_rect.collidepoint(mouse_pos) else (50, 150, 50)
        menu_color = (80, 180, 80) if btn_menu_rect.collidepoint(mouse_pos) else (50, 150, 50)

        pygame.draw.rect(win_screen, play_again_color, btn_play_again_rect, border_radius=8)
        pygame.draw.rect(win_screen, menu_color, btn_menu_rect, border_radius=8)

        btn_play_again_txt = FONT_BUTTON.render("Chơi lại", True, (255, 255, 255))
        btn_menu_txt = FONT_BUTTON.render("Menu", True, (255, 255, 255))

        win_screen.blit(btn_play_again_txt, btn_play_again_txt.get_rect(center=btn_play_again_rect.center))
        win_screen.blit(btn_menu_txt, btn_menu_txt.get_rect(center=btn_menu_rect.center))

        # Hiển thị trạng thái xác nhận (nếu đang chờ)
        if confirm_message:
            confirm_txt = FONT_TIME.render(confirm_message, True, (255, 255, 255))
            win_screen.blit(confirm_txt, confirm_txt.get_rect(center=(width//2, height//2 + 160)))

        # Xử lý sự kiện
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_play_again_rect.collidepoint(event.pos):
                    # PvP: cần 2 người đồng ý
                    if game_mode == "pvp":
                        if not confirm_red:
                            confirm_red = True
                            confirm_message = f"{player_red_name} đã đồng ý. Chờ {player_black_name}..."
                        elif not confirm_black:
                            confirm_black = True
                            confirm_message = "Cả hai đã đồng ý!"
                            # Cả hai đồng ý rồi -> reset game
                            reset_game()
                            waiting = False
                    else:
                        # Vs Máy: chỉ cần 1 click
                        reset_game()
                        waiting = False
                elif btn_menu_rect.collidepoint(event.pos):
                    menu()
                    setup_game()  # Nhập tên lại sau khi chọn mode mới
                    waiting = False

        pygame.display.update()
        clock.tick(60)



def show_message(text, duration=1.2):
    # Non-blocking: schedule a transient message overlay to be drawn
    global message_overlay_text, message_overlay_end
    message_overlay_text = text
    message_overlay_end = pygame.time.get_ticks() + int(duration * 1000)
    if DEBUG:
        print(f"show_message: scheduled message '{text}' until {message_overlay_end}")
    return

def show_check_screen(player, duration_ms=CHECK_OVERLAY_DEFAULT_MS):
    """Non-blocking: schedule a temporary overlay indicating `player` is in check.

    Set a global expiration timestamp; the overlay is drawn each frame by
    `draw_board()` until it expires. This avoids blocking the main loop.
    """
    global check_overlay_end, check_overlay_player
    now = pygame.time.get_ticks()
    # If the same player's check overlay is already active, do not reschedule (avoids flicker)
    if check_overlay_player == player and check_overlay_end and now < check_overlay_end:
        if DEBUG:
            print(f"show_check_screen: already scheduled for {player} until {check_overlay_end}, skipping")
        return
    check_overlay_player = player
    check_overlay_end = now + int(duration_ms)
    if DEBUG:
        print(f"show_check_screen: scheduled check overlay for {player} until {check_overlay_end}")


# ----- CONFIG -----
cell = 60
margin = 40
TOP_BAR_HEIGHT = 28
TOP_BAR_PADDING = 8
top_margin = margin + TOP_BAR_HEIGHT + TOP_BAR_PADDING
cols = 9
rows = 10
clock = pygame.time.Clock()
width = margin * 2 + cell * (cols - 1)
height = margin * 2 + cell * (rows - 1) + TOP_BAR_HEIGHT + TOP_BAR_PADDING

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Cotuong Board")

running = True
selected = None
valid_moves = []
# ---- Thêm biến quản lý lượt ----
current_player = "red"
move_history = []  # list of ((r1,c1),(r2,c2), piece, player)



# ===== QUÂN ĐEN (simplified) =====
# 车 马 象 士 将 炮 卒
# ===== QUÂN ĐỎ (traditional) =====
# 車 馬 相 仕 帥 炮 兵

board = Board()


piece_font = pygame.font.SysFont("Microsoft YaHei", 32)
red_pieces = {"帥","仕","相","車","馬","炮","兵"}

black_pieces = {"将","士","象","车","马","砲","卒"}

# ----- Hàm xác định màu quân -----
def piece_color(piece):
    if piece in red_pieces:
        return "red"
    elif piece in black_pieces:
        return "black"
    return None

def draw_piece(row, col, text, color):
    x = margin + col * cell
    y = top_margin + row * cell
    center = (x, y)

    # Quân cờ
    pygame.draw.circle(screen, (240, 220, 180), center, 25)
    pygame.draw.circle(screen, (0, 0, 0), center, 25, 2)

    img = piece_font.render(text, True, color)
    rect = img.get_rect(center=center)
    screen.blit(img, rect)


def draw_all_pieces():
    for r in range(10):
        for c in range(9):
            p = board.get(r, c)

            if p != "":
                # Tô màu theo ký tự
                if p in red_pieces:
                    color = (255, 0, 0) 
                    
                elif p in black_pieces:
                    color = (0, 0, 0)
                else:
                    color = (0, 0, 255)

                
                draw_piece(r, c, p, color)


def draw_selected():
    if selected is None:
        return
    r, c = selected
    x = margin + c * cell
    y = top_margin + r * cell
    pygame.draw.circle(screen, (255, 255, 0, 80), (x, y), 30)  # vàng nhạt, alpha 80




def draw_board():
    global check_overlay_end, check_overlay_player, message_overlay_end, message_overlay_text
    global ai_thinking
    screen.fill((240, 200, 150))

    # --- KẺ ĐƯỜNG NGANG ---
    for r in range(rows):
        y = top_margin + r * cell
        pygame.draw.line(screen, (0,0,0), (margin, y), (margin + cell * (cols - 1), y), 2)

    # --- KẺ ĐƯỜNG DỌC ---
    for c in range(cols):
        x = margin + c * cell

        pygame.draw.line(screen, (0,0,0), (x, top_margin), (x, top_margin + cell * 4), 2)
        pygame.draw.line(screen, (0,0,0), (x, top_margin + cell * 5), (x, top_margin + cell * 9), 2)

    # --- CUNG TƯỚNG ---
    c1 = margin + 3 * cell
    c2 = margin + 5 * cell

    # trên
    pygame.draw.line(screen, (0,0,0), (c1, top_margin), (c2, top_margin + 2 * cell), 2)
    pygame.draw.line(screen, (0,0,0), (c2, top_margin), (c1, top_margin + 2 * cell), 2)

    # dưới
    pygame.draw.line(screen, (0,0,0), (c1, top_margin + 7 * cell), (c2, top_margin + 9 * cell), 2)
    pygame.draw.line(screen, (0,0,0), (c2, top_margin + 7 * cell), (c1, top_margin + 9 * cell), 2)

    # --- CHỮ TRÊN SÔNG ---
    font = pygame.font.SysFont("msgothic", 36)
    text1 = font.render("楚河", True, (0,0,0))
    text2 = font.render("漢界", True, (0,0,0))

    screen.blit(text1, (margin + cell * 1.3, top_margin + cell * 4.3))
    screen.blit(text2, (margin + cell * 5.5, top_margin + cell * 4.3))

        # Kiểm tra alternation: nếu 3 nước cuối cùng (toàn bộ history) cùng dùng 1 cặp
        # và chúng theo mẫu alternation (A->B, B->A, A->B), thì nếu nước hiện tại tiếp tục (B->A)
        # tức sẽ thành 4 alternation liên tiếp, ta chặn nước này.
        # Lấy 3 nước cuối cùng (toàn cục)
    
    draw_selected()
    draw_all_pieces()
    # Nếu bật DEBUG và có attacker/king thì hiển thị highlight đỏ
    if DEBUG and last_attacker and last_checked_king:
        ar, ac, ap = last_attacker
        kr, kc = last_checked_king
        ax = margin + ac * cell
        ay = top_margin + ar * cell
        kx = margin + kc * cell
        ky = top_margin + kr * cell
        # vòng đỏ quanh attacker và king
        pygame.draw.circle(screen, (200, 0, 0), (ax, ay), 28, 4)
        pygame.draw.circle(screen, (200, 0, 0), (kx, ky), 28, 4)
    # Nếu có overlay check đang active thì vẽ nó (non-blocking)
    now = pygame.time.get_ticks()
    if check_overlay_end and now < check_overlay_end:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        font = FONT_BUTTON
        player_name = player_red_name if check_overlay_player == "red" else player_black_name
        txt = font.render(f"{player_name} BỊ CHIẾU!", True, (255, 0, 0))
        screen.blit(txt, txt.get_rect(center=(width//2, height//2)))
    elif check_overlay_end and now >= check_overlay_end:
        # expired
        check_overlay_end = 0
        check_overlay_player = None
    # If there is a scheduled transient message, draw it as a non-blocking overlay
    if message_overlay_end and now < message_overlay_end and message_overlay_text:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        font = FONT_BUTTON
        txt = font.render(message_overlay_text, True, (255, 255, 0))
        screen.blit(txt, txt.get_rect(center=(width//2, int(height*0.55))))
    elif message_overlay_end and now >= message_overlay_end:
        # expired
        message_overlay_end = 0
        message_overlay_text = None
    # Nếu AI đang tính toán, hiển thị overlay nhỏ báo 'Máy đang suy nghĩ...'
    if ai_thinking:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        font = pygame.font.SysFont("Arial", 32, bold=True)
        thinking_txt = font.render("Máy đang suy nghĩ...", True, (255, 255, 0))
        screen.blit(thinking_txt, thinking_txt.get_rect(center=(width//2, int(height*0.55))))
    # ---- Highlight đường đi hợp lệ ----
    for (rr, cc) in valid_moves:
        x = margin + cc * cell
        y = top_margin + rr * cell
        pygame.draw.circle(screen, (0, 255, 0), (x, y), 10)  # chấm xanh

    # Draw per-move countdown in a top status bar (outside the board)
    try:
        now = pygame.time.get_ticks()
        remaining_ms = max(0, int(THINK_TIME_PER_MOVE.get(current_player, 15) * 1000) - (now - turn_start_time))
        remaining_s = remaining_ms // 1000
        bar_h = 28
        bar = pygame.Surface((width, bar_h), pygame.SRCALPHA)
        bar.fill((255, 255, 255, 220))
        screen.blit(bar, (0, 0))
        # Draw pause and resign buttons on the top bar (right side)
        btn_w = 110
        btn_h = 20
        gap = 8
        # rightmost: Pause/Resume
        pause_label = "Tiếp tục" if paused else "Tạm dừng"
        # vertically center buttons in the bar
        btn_y = (bar_h - btn_h) // 2
        pause_rect = pygame.Rect(width - margin - btn_w, btn_y, btn_w, btn_h)
        resign_rect = pygame.Rect(width - margin - btn_w - gap - btn_w, btn_y, btn_w, btn_h)
        pygame.draw.rect(screen, (220,220,220), resign_rect, border_radius=6)
        pygame.draw.rect(screen, (220,220,220), pause_rect, border_radius=6)
        pr_txt = FONT_TIME.render("Đầu hàng", True, (0,0,0))
        ps_txt = FONT_TIME.render(pause_label, True, (0,0,0))
        screen.blit(pr_txt, pr_txt.get_rect(center=resign_rect.center))
        screen.blit(ps_txt, ps_txt.get_rect(center=pause_rect.center))
        # expose rects for event handling
        global pause_button_rect, resign_button_rect
        pause_button_rect = pause_rect
        resign_button_rect = resign_rect

        # Reserve right area for buttons so the timer text won't overlap
        reserved_right = margin + (btn_w * 2) + gap + 12
        # center timer in the area between left margin and (width - reserved_right)
        player_display = player_red_name if current_player == "red" else player_black_name
        # If paused, display paused label and freeze remaining time display
        if paused:
            rem = paused_remaining_ms if paused_remaining_ms is not None else remaining_s * 1000
            disp_txt = f"Lượt: {player_display} - Tạm dừng (còn {max(0, rem//1000)}s)"
        else:
            disp_txt = f"Lượt: {player_display} - {remaining_s}s"
        txt = FONT_TIME.render(disp_txt, True, (0, 0, 0))
        available_left = margin
        available_right = width - reserved_right
        center_x = available_left + max(0, (available_right - available_left) // 2)
        screen.blit(txt, (center_x - txt.get_width()//2, (bar_h - txt.get_height())//2))
    except Exception:
        pass

    # If paused, draw a centered paused overlay over the board area
    if paused:
        overlay_h = height - TOP_BAR_HEIGHT - TOP_BAR_PADDING
        overlay = pygame.Surface((width, overlay_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, TOP_BAR_HEIGHT))
        pause_txt = FONT_BUTTON.render("Đã tạm dừng", True, (255, 255, 255))
        screen.blit(pause_txt, pause_txt.get_rect(center=(width//2, TOP_BAR_HEIGHT + overlay_h//2)))



def get_cell_from_mouse(pos):
    mx, my = pos
    col = round((mx - margin) / cell)
    row = round((my - top_margin) / cell)
    if 0 <= row < rows and 0 <= col < cols:
        return (row, col)
    return None

def try_move(selected, target):
    global current_player

    r1, c1 = selected
    r2, c2 = target

    moving_piece = board.get(r1, c1)
    target_piece = board.get(r2, c2)

    # DEBUG: in thông tin lịch sử khi bật DEBUG
    if DEBUG:
        print(f"try_move: kiểm tra nước {(r1,c1)} -> {(r2,c2)} cho người chơi {current_player}")
        print(" lịch sử gần nhất (8):", move_history[-8:])

    # Kiểm tra lặp nước liên tiếp: không cho phép cùng một nước (từ->đến) của cùng người chơi lặp 4 lần liên tiếp
    consec = 0
    for mv in reversed(move_history):
        if mv[0] == (r1, c1) and mv[1] == (r2, c2) and mv[3] == current_player:
            consec += 1
        else:
            break
    # nếu đã lặp 3 lần trước đó, lần này là lần thứ 4 -> cấm
    if consec >= 3:
        show_message("Không được lặp lại nước này quá 3 lần liên tiếp")
        return selected, False

    # Per-player repetition rule:
    # If the current player already made the same unordered pair move in their
    # last 3 own moves, block this move (would be the 4th for that player).
    if len(move_history) >= 3:
        pair = frozenset(((r1, c1), (r2, c2)))
        player_moves = [mv for mv in move_history if mv[3] == current_player]
        recent_player_moves = player_moves[-3:]
        if len(recent_player_moves) == 3 and all(frozenset((m[0], m[1])) == pair for m in recent_player_moves):
            if DEBUG:
                print(f"try_move: blocked by per-player 4th repetition on pair {pair}")
            show_message("Lặp lại 3 lần!")
            return selected, False

    if (r1, c1) == (r2, c2):
        print("[!] Không thể đứng yên.")
        return selected, False

    if piece_color(moving_piece) == piece_color(target_piece) and target_piece != "":
        print("[!] Không thể ăn quân cùng màu.")
        return selected, False

    if not is_valid_move(moving_piece, r1, c1, r2, c2, board):
        print(f"[!] Sai luật di chuyển: {moving_piece}")
        return selected, False

    # Thử move tạm
    captured_piece = target_piece
    board.set(r2, c2, moving_piece)
    board.set(r1, c1, "")

    # Ăn tướng → thắng
    if captured_piece in ["帥", "将"]:
    # CHỈNH SỬA ĐÚNG
    # Ăn帥 → tướng đỏ chết → black thắng
    # Ăn将 → tướng đen chết → red thắng
        winner = "black" if captured_piece == "帥" else "red"

        move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))
        num_moves = len(move_history)

        if game_mode == "pvp":
            if winner == "red":
                save_result(player_red_name, True, vs_machine=False, num_moves=num_moves)
                save_result(player_black_name, False, vs_machine=False, num_moves=num_moves)
            else:
                save_result(player_black_name, True, vs_machine=False, num_moves=num_moves)
                save_result(player_red_name, False, vs_machine=False, num_moves=num_moves)
        else:
            if winner == "red":
                save_result(player_red_name, True, vs_machine=True, num_moves=num_moves)
            else:
                save_result(player_red_name, False, vs_machine=True, num_moves=num_moves)

        show_winner(winner)
        return selected, True


    opponent = "black" if current_player == "red" else "red"

    # Move gây chiếu chính mình → không hợp lệ
    if is_checked(current_player, board):
        board.set(r1, c1, moving_piece)
        board.set(r2, c2, captured_piece)
        show_message(f"{current_player.upper()} BỊ CHIẾU!")
        return selected, False

    # Chiếu đối phương → overlay
    if is_checked(opponent, board):
        show_check_screen(opponent)

    # Chiếu bí → thắng
    if not has_any_legal_move(opponent):
        # ghi lịch sử nước đi trước khi xử lý kết thúc
        move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))
        num_moves = len(move_history)
        # record result
        if game_mode == "pvp":
            # current_player won, other lost
            if current_player == "red":
                save_result(player_red_name, True, vs_machine=False, num_moves=num_moves)
                save_result(player_black_name, False, vs_machine=False, num_moves=num_moves)
            else:
                save_result(player_black_name, True, vs_machine=False, num_moves=num_moves)
                save_result(player_red_name, False, vs_machine=False, num_moves=num_moves)
        else:
            # vs machine
            if current_player == "red":
                save_result(player_red_name, True, vs_machine=True, num_moves=num_moves)
            else:
                save_result(player_red_name, False, vs_machine=True, num_moves=num_moves)
        show_winner(current_player)
        return selected, True

    # Ghi lịch sử nước đi (nếu tới đây tức là nước hợp lệ và không gây self-check)
    move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))

    return selected, True


def is_valid_move(piece, r1, c1, r2, c2, board):
    # Delegate to Board.is_valid_move to keep rules consistent.
    try:
        return board.is_valid_move(r1, c1, r2, c2)
    except Exception:
        return False

def get_valid_moves(r, c):
    valid_moves = []
    piece = board.get(r, c)
    if piece == "":
        return valid_moves

    for r2 in range(rows):
        for c2 in range(cols):
            if (r2, c2) == (r, c):
                continue
            if piece_color(board.get(r2, c2)) == piece_color(piece):
                continue
            if not is_valid_move(piece, r, c, r2, c2, board):
                continue

            # Kiểm tra chiếu tướng sau move
            temp_board = board.copy()
            temp_board.set(r2, c2, piece)
            temp_board.set(r, c, "")
            if is_checked(current_player, temp_board):
                continue

            valid_moves.append((r2, c2))

    return valid_moves


def set_turn_start():
    global turn_start_time
    turn_start_time = pygame.time.get_ticks()


def get_all_legal_moves(player):
    moves = []
    for r in range(rows):
        for c in range(cols):
            p = board.get(r, c)
            if p == "" or piece_color(p) != player:
                continue
            for (r2, c2) in get_valid_moves(r, c):
                moves.append(((r, c), (r2, c2)))
    return moves


def handle_timeout():
    """Handle timeout for current_player: auto-play a fallback move or declare loss."""
    global current_player, ai_thinking, ai_move_result
    player = current_player
    moves = get_all_legal_moves(player)
    if not moves:
        opponent = "black" if player == "red" else "red"
        show_winner(opponent)
        return

    # If AI's turn (and not PvP), try to use ai_move_result, else quick random fallback
    if player == "black" and game_mode != "pvp":
        if ai_move_result:
            start, end = ai_move_result
            ai_move_result = None
            _, moved = try_move(start, end)
            if moved:
                current_player = "red"
                set_turn_start()
                return
        # fallback: quick random move
        mv = random_move(board, "black", history=list(move_history))
        if mv:
            start, end = mv
            _, moved = try_move(start, end)
            if moved:
                current_player = "red"
                set_turn_start()
                ai_thinking = False
                return

    # Human or PvP: pick a random legal move
    start, end = random.choice(moves)
    _, moved = try_move(start, end)
    if moved:
        current_player = "black" if player == "red" else "red"
        set_turn_start()
        return


def find_king(board, player):
    king_char = "帥" if player == "red" else "将"
    for r in range(rows):
        for c in range(cols):
            if board.get(r, c) == king_char:
                return (r, c)
    # Nếu không tìm thấy tướng thì trả về None (không ném lỗi)
    return None

def is_checked(player, board):
    global last_attacker, last_checked_king
    king_pos = find_king(board, player)
    if king_pos is None:
        last_attacker = None
        last_checked_king = None
        return False
    kr, kc = king_pos
    opponent = "black" if player == "red" else "red"
    opponent_king = "将" if player == "red" else "帥"

    # 1. Kiểm tra chiếu từ quân đối phương
    for r in range(rows):
        for c in range(cols):
            p = board.get(r, c)
            if p != "" and piece_color(p) == opponent:
                try:
                    attack = is_valid_move(p, r, c, kr, kc, board)
                except Exception as e:
                    attack = False
                    if DEBUG:
                        print(f"is_checked: error checking move {p} from {(r,c)} to king {(kr,kc)}: {e}")
                if attack:
                    if DEBUG:
                        print(f"is_checked: king at {(kr,kc)} attacked by {p} at {(r,c)}")
                    last_attacker = (r, c, p)
                    last_checked_king = (kr, kc)
                    return True

    # 2. Kiểm tra Flying General
    for step in [-1, 1]:
        r = kr + step
        while 0 <= r < rows:
            p = board.get(r, kc)
            if p != "":
                if p == opponent_king:
                    if DEBUG:
                        print(f"is_checked: flying general attack at {(r,kc)}")
                    last_attacker = (r, kc, p)
                    last_checked_king = (kr, kc)
                    return True
                break
            r += step

    # nếu không có attacker, xóa highlight
    last_attacker = None
    last_checked_king = None
    return False


def find_attackers(player, board):
    """Return list of (r,c,piece) of opponent pieces that attack player's king."""
    king_pos = find_king(board, player)
    if king_pos is None:
        return []
    kr, kc = king_pos
    opponent = "black" if player == "red" else "red"
    attackers = []
    for r in range(rows):
        for c in range(cols):
            p = board.get(r, c)
            if p != "" and piece_color(p) == opponent:
                try:
                    if is_valid_move(p, r, c, kr, kc, board):
                        attackers.append((r, c, p))
                except Exception as e:
                    if DEBUG:
                        print(f"find_attackers: error checking {p} {(r,c)} -> king {(kr,kc)}: {e}")
    return attackers


def has_any_legal_move(player):
    """Kiểm tra xem player còn nước đi hợp lệ hay không."""
    for r1 in range(rows):
        for c1 in range(cols):
            p = board.get(r1, c1)
            if p == "" or piece_color(p) != player:
                continue

            # thử tất cả ô trên bàn
            for r2 in range(rows):
                for c2 in range(cols):
                    if (r1, c1) == (r2, c2):
                        continue
                    if piece_color(board.get(r2, c2)) == player:
                        continue
                    if not is_valid_move(p, r1, c1, r2, c2, board):
                        continue

                    # thử đi tạm
                    temp = board.copy()
                    temp.set(r2, c2, p)
                    temp.set(r1, c1, "")
                    still_checked = is_checked(player, temp)
                    if not still_checked:
                        return True

    return False


# ==========================
# MAIN LOOP
# ==========================
game_mode = None  # sẽ lưu PvP / Easy / Medium / Hard

def draw_button(rect, text, color):
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, (0,0,0), rect, 2)
    txt = FONT_BUTTON.render(text, True, (0,0,0))
    txt_rect = txt.get_rect(center=rect.center)
    screen.blit(txt, txt_rect)

def setup_game():
    """Thiết lập game sau khi chọn mode: nhập tên và reset bàn cờ."""
    global player_red_name, player_black_name
    player_red_name = input_player_name(1)
    if game_mode == "pvp":
        player_black_name = input_player_name(2)
    else:
        player_black_name = "Máy"
    reset_game()

def menu():
    global game_mode
    menu_running = True
    buttons = [
        (pygame.Rect(width//2-100, 150, 200, 50), "PvP", "pvp"),
        (pygame.Rect(width//2-100, 230, 200, 50), "Easy", "de"),
        (pygame.Rect(width//2-100, 310, 200, 50), "Medium", "trung"),
        (pygame.Rect(width//2-100, 390, 200, 50), "Hard", "kho"),
        (pygame.Rect(width//2-100, 470, 200, 50), "BXH", "leaderboard"),
    ]

    while menu_running:
        screen.fill((200, 180, 150))
        title = FONT_TITLE.render("Chọn chế độ chơi", True, (0,0,0))
        screen.blit(title, (width//2 - title.get_width()//2, 50))

        for rect, text, _ in buttons:
            draw_button(rect, text, (180, 200, 220))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for rect, text, mode in buttons:
                    if rect.collidepoint(mx, my):
                        if mode == "leaderboard":
                            leaderboard()
                            break
                        else:
                            game_mode = mode
                            menu_running = False

        pygame.display.flip()
        clock.tick(60)

# Gọi menu trước khi vào main loop
menu()
print("Chế độ chơi:", game_mode)

# Thiết lập game: nhập tên và khởi tạo
setup_game()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            # Bấm D để bật/tắt debug (vẽ vòng đỏ quanh attacker/king)
            if event.key == pygame.K_d:
                DEBUG = not DEBUG
                print(f"DEBUG set to {DEBUG}")
            # Bấm R để in ra move_history gần nhất (debug)
            if event.key == pygame.K_r:
                print("--- move_history (last 20) ---")
                for i, mv in enumerate(move_history[-20:], start=max(0, len(move_history)-20)):
                    print(i, mv)
            # Bấm H để liệt kê tất cả quân tấn công vào tướng của current_player
            if event.key == pygame.K_h:
                atk = find_attackers(current_player, board)
                if atk:
                    print(f"Attackers on {current_player} king:")
                    for (ar, ac, ap) in atk:
                        print(f" - {ap} at {(ar,ac)}")
                    # highlight first attacker
                    last = atk[0]
                    last_attacker = (last[0], last[1], last[2])
                    last_checked_king = find_king(board, current_player)
                else:
                    print(f"No attackers on {current_player} king")
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            # Top-bar button handling (pause/resign)
            try:
                if pause_button_rect and pause_button_rect.collidepoint((mx, my)):
                    # toggle pause: when pausing store remaining_ms; when resuming restore timer
                    now = pygame.time.get_ticks()
                    allowed_ms = int(THINK_TIME_PER_MOVE.get(current_player, 15) * 1000)
                    if not paused:
                        # entering pause: calculate remaining time
                        rem = max(0, allowed_ms - (now - turn_start_time))
                        paused_remaining_ms = rem
                        paused = True
                    else:
                        # leaving pause: restore turn_start_time so remaining time is preserved
                        if paused_remaining_ms is None:
                            set_turn_start()
                        else:
                            turn_start_time = pygame.time.get_ticks() - (allowed_ms - paused_remaining_ms)
                            paused_remaining_ms = None
                        paused = False
                    continue
                if resign_button_rect and resign_button_rect.collidepoint((mx, my)):
                    num_moves = len(move_history)
                    # Người chơi (red) đầu hàng => máy (black) thắng
                    if game_mode == "pvp":
                        # PvP: current_player đầu hàng
                        opponent = "black" if current_player == "red" else "red"
                        if current_player == "red":
                            save_result(player_red_name, False, vs_machine=False, num_moves=num_moves)
                            save_result(player_black_name, True, vs_machine=False, num_moves=num_moves)
                        else:
                            save_result(player_black_name, False, vs_machine=False, num_moves=num_moves)
                            save_result(player_red_name, True, vs_machine=False, num_moves=num_moves)
                        show_winner(opponent)
                    else:
                        # Vs machine: red (người chơi) đầu hàng => black (máy) thắng
                        save_result(player_red_name, False, vs_machine=True, num_moves=num_moves)
                        show_winner("black")
                    continue
            except Exception:
                # If buttons not yet initialized, ignore
                pass

            # If paused, ignore board clicks
            if paused:
                continue

            if current_player == "red" or game_mode == "pvp":
                clicked = get_cell_from_mouse(event.pos)
                if clicked:
                    r, c = clicked
                    if selected is None:
                        p = board.get(r, c)
                        if p != "" and piece_color(p) == current_player:
                            selected = (r, c)
                            valid_moves = get_valid_moves(r, c)
                    else:
                        _, moved = try_move(selected, (r, c))
                        if moved:
                            selected = None
                            valid_moves = []
                            current_player = "black" if current_player == "red" else "red"
                            set_turn_start()
                        else:
                            # đổi chọn nếu click vào quân cùng màu
                            if piece_color(board.get(r, c)) == current_player:
                                selected = (r, c)
                                valid_moves = get_valid_moves(r, c)

    # --- AI đi nếu cần ---
    # Check per-move timeout (skip when paused)
    if not paused:
        now = pygame.time.get_ticks()
        allowed_ms = int(THINK_TIME_PER_MOVE.get(current_player, 15) * 1000)
        if now - turn_start_time >= allowed_ms:
            if DEBUG:
                print(f"Turn timeout for {current_player}, auto-playing fallback move")
            handle_timeout()

    if not paused and game_mode != "pvp" and current_player == "black":
        # Start background AI thread if not already running
        if not ai_thinking and ai_move_result is None:
            # copy board to let AI compute without racing on main board
            def _run_ai(bcopy, mode, history):
                global ai_move_result, ai_thinking
                try:
                    mv = ai_move(bcopy, "black", level=mode, history=history)
                    ai_move_result = mv
                except Exception as e:
                    ai_move_result = None
                    if DEBUG:
                        print("Lỗi luồng AI:", e)
                finally:
                    ai_thinking = False

            ai_thinking = True
            ai_move_result = None
            ai_thread = threading.Thread(target=_run_ai, args=(board.copy(), game_mode, list(move_history)), daemon=True)
            ai_thread.start()

        # If AI finished computing, apply the move once
        if not ai_thinking and ai_move_result:
            start, end = ai_move_result
            ai_move_result = None
            if start and end:
                _, moved = try_move(start, end)
                if moved:
                    current_player = "red"
                    selected = None
                    valid_moves = []
                    set_turn_start()

    draw_board()
    pygame.display.flip()
    clock.tick(60)


pygame.quit()
sys.exit()

