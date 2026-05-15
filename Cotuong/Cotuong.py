import sys
import random
import threading

import pygame

from board import Board
from ai import ai_move, random_move
from ui import (screen, clock,
                CELL, MARGIN, TOP_MARGIN, TOP_BAR_HEIGHT, TOP_BAR_PADDING,
                COLS, ROWS, WIDTH, HEIGHT,
                FONT_TITLE, FONT_BUTTON, FONT_TIME,
                red_pieces, black_pieces,
                draw_all_pieces, draw_selected, draw_button)
from leaderboard import save_result, leaderboard, input_player_name
import game_logic

# =================== TRẠNG THÁI GAME ===================
DEBUG               = False
board               = Board()
current_player      = "red"
selected            = None
valid_moves         = []
move_history        = []
game_mode           = None
player_red_name     = ""
player_black_name   = ""

last_attacker       = None
last_checked_king   = None

check_overlay_end    = 0
check_overlay_player = None
CHECK_OVERLAY_MS     = 1200

message_overlay_text = None
message_overlay_end  = 0

ai_thinking     = False
ai_move_result  = None
ai_thread       = None

THINK_TIME      = {"red": 60, "black": 60}
turn_start_time = pygame.time.get_ticks()

paused              = False
pause_button_rect   = None
resign_button_rect  = None
paused_remaining_ms = None

# =================== HÀM HỖ TRỢ ===================

def piece_color(piece):
    if piece in red_pieces:   return "red"
    if piece in black_pieces: return "black"
    return None


def is_valid_move(piece, r1, c1, r2, c2, brd):
    try:
        return brd.is_valid_move(r1, c1, r2, c2)
    except Exception:
        return False


def is_checked(player, brd):
    """Wrapper cập nhật last_attacker / last_checked_king."""
    global last_attacker, last_checked_king
    checked, attacker, king_pos = game_logic.is_checked(brd, player)
    last_attacker    = attacker
    last_checked_king = king_pos
    return checked


def get_valid_moves(r, c):
    moves = []
    piece = board.get(r, c)
    if not piece:
        return moves
    for r2 in range(ROWS):
        for c2 in range(COLS):
            if (r2, c2) == (r, c):
                continue
            if piece_color(board.get(r2, c2)) == piece_color(piece):
                continue
            if not is_valid_move(piece, r, c, r2, c2, board):
                continue
            temp = board.copy()
            temp.set(r2, c2, piece)
            temp.set(r, c, "")
            if not is_checked(current_player, temp):
                moves.append((r2, c2))
    return moves


def set_turn_start():
    global turn_start_time
    turn_start_time = pygame.time.get_ticks()


def reset_game():
    global board, current_player, selected, move_history
    board          = Board()
    current_player = "red"
    selected       = None
    move_history   = []
    set_turn_start()


# =================== OVERLAY / THÔNG BÁO ===================

def show_message(text, duration=1.2):
    global message_overlay_text, message_overlay_end
    message_overlay_text = text
    message_overlay_end  = pygame.time.get_ticks() + int(duration * 1000)


def show_check_screen(player, duration_ms=CHECK_OVERLAY_MS):
    global check_overlay_end, check_overlay_player
    now = pygame.time.get_ticks()
    if check_overlay_player == player and check_overlay_end and now < check_overlay_end:
        return
    check_overlay_player = player
    check_overlay_end    = now + int(duration_ms)


# =================== VẼ BÀN CỜ ===================

def draw_board():
    global check_overlay_end, check_overlay_player
    global message_overlay_end, message_overlay_text
    global pause_button_rect, resign_button_rect

    screen.fill((240, 200, 150))

    # Đường ngang
    for r in range(ROWS):
        y = TOP_MARGIN + r * CELL
        pygame.draw.line(screen, (0, 0, 0),
                         (MARGIN, y), (MARGIN + CELL * (COLS - 1), y), 2)
    # Đường dọc (bỏ khoảng sông giữa hàng 4-5)
    for c in range(COLS):
        x = MARGIN + c * CELL
        pygame.draw.line(screen, (0, 0, 0), (x, TOP_MARGIN), (x, TOP_MARGIN + CELL * 4), 2)
        pygame.draw.line(screen, (0, 0, 0), (x, TOP_MARGIN + CELL * 5), (x, TOP_MARGIN + CELL * 9), 2)

    # Cung tướng
    c1 = MARGIN + 3 * CELL
    c2 = MARGIN + 5 * CELL
    pygame.draw.line(screen, (0, 0, 0), (c1, TOP_MARGIN),            (c2, TOP_MARGIN + 2 * CELL), 2)
    pygame.draw.line(screen, (0, 0, 0), (c2, TOP_MARGIN),            (c1, TOP_MARGIN + 2 * CELL), 2)
    pygame.draw.line(screen, (0, 0, 0), (c1, TOP_MARGIN + 7 * CELL), (c2, TOP_MARGIN + 9 * CELL), 2)
    pygame.draw.line(screen, (0, 0, 0), (c2, TOP_MARGIN + 7 * CELL), (c1, TOP_MARGIN + 9 * CELL), 2)

    # Chữ sông
    font_river = pygame.font.SysFont("msgothic", 36)
    screen.blit(font_river.render("楚河", True, (0, 0, 0)),
                (MARGIN + CELL * 1.3, TOP_MARGIN + CELL * 4.3))
    screen.blit(font_river.render("漢界", True, (0, 0, 0)),
                (MARGIN + CELL * 5.5, TOP_MARGIN + CELL * 4.3))

    draw_selected(selected)
    draw_all_pieces(board)

    # Debug highlight
    if DEBUG and last_attacker and last_checked_king:
        ar, ac, _ = last_attacker
        kr, kc    = last_checked_king
        pygame.draw.circle(screen, (200, 0, 0),
                           (MARGIN + ac * CELL, TOP_MARGIN + ar * CELL), 28, 4)
        pygame.draw.circle(screen, (200, 0, 0),
                           (MARGIN + kc * CELL, TOP_MARGIN + kr * CELL), 28, 4)

    now = pygame.time.get_ticks()

    # Check overlay
    if check_overlay_end and now < check_overlay_end:
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        screen.blit(ov, (0, 0))
        name = player_red_name if check_overlay_player == "red" else player_black_name
        txt  = FONT_BUTTON.render(f"{name} BỊ CHIẾU!", True, (255, 0, 0))
        screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    elif check_overlay_end and now >= check_overlay_end:
        check_overlay_end    = 0
        check_overlay_player = None

    # Message overlay
    if message_overlay_end and now < message_overlay_end and message_overlay_text:
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        screen.blit(ov, (0, 0))
        txt = FONT_BUTTON.render(message_overlay_text, True, (255, 255, 0))
        screen.blit(txt, txt.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.55))))
    elif message_overlay_end and now >= message_overlay_end:
        message_overlay_end  = 0
        message_overlay_text = None

    # AI thinking overlay
    if ai_thinking:
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        screen.blit(ov, (0, 0))
        txt = FONT_BUTTON.render("Máy đang suy nghĩ...", True, (255, 255, 0))
        screen.blit(txt, txt.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.55))))

    # Nước đi hợp lệ (chấm xanh)
    for (rr, cc) in valid_moves:
        pygame.draw.circle(screen, (0, 255, 0),
                           (MARGIN + cc * CELL, TOP_MARGIN + rr * CELL), 10)

    # Thanh trạng thái trên cùng
    bar = pygame.Surface((WIDTH, TOP_BAR_HEIGHT), pygame.SRCALPHA)
    bar.fill((255, 255, 255, 220))
    screen.blit(bar, (0, 0))

    btn_w, btn_h = 110, 20
    btn_y = (TOP_BAR_HEIGHT - btn_h) // 2
    pause_rect  = pygame.Rect(WIDTH - MARGIN - btn_w, btn_y, btn_w, btn_h)
    resign_rect = pygame.Rect(WIDTH - MARGIN - btn_w * 2 - 8, btn_y, btn_w, btn_h)
    pygame.draw.rect(screen, (220, 220, 220), resign_rect, border_radius=6)
    pygame.draw.rect(screen, (220, 220, 220), pause_rect,  border_radius=6)
    screen.blit(FONT_TIME.render("Đầu hàng", True, (0, 0, 0)),
                FONT_TIME.render("Đầu hàng", True, (0, 0, 0)).get_rect(center=resign_rect.center))
    screen.blit(FONT_TIME.render("Tiếp tục" if paused else "Tạm dừng", True, (0, 0, 0)),
                FONT_TIME.render("Tiếp tục" if paused else "Tạm dừng", True, (0, 0, 0))
                .get_rect(center=pause_rect.center))
    pause_button_rect  = pause_rect
    resign_button_rect = resign_rect

    allowed_ms = int(THINK_TIME.get(current_player, 15) * 1000)
    if paused:
        rem = paused_remaining_ms if paused_remaining_ms is not None else 0
        disp = f"Lượt: {player_red_name if current_player == 'red' else player_black_name} - Tạm dừng (còn {max(0, rem // 1000)}s)"
    else:
        remaining_s = max(0, allowed_ms - (now - turn_start_time)) // 1000
        disp = f"Lượt: {player_red_name if current_player == 'red' else player_black_name} - {remaining_s}s"
    txt = FONT_TIME.render(disp, True, (0, 0, 0))
    screen.blit(txt, (MARGIN, (TOP_BAR_HEIGHT - txt.get_height()) // 2))

    # Pause overlay
    if paused:
        ov_h = HEIGHT - TOP_BAR_HEIGHT
        ov   = pygame.Surface((WIDTH, ov_h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        screen.blit(ov, (0, TOP_BAR_HEIGHT))
        txt = FONT_BUTTON.render("Đã tạm dừng", True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=(WIDTH // 2, TOP_BAR_HEIGHT + ov_h // 2)))


# =================== HIỂN THỊ THẮNG ===================

def show_winner(winner):
    global current_player, selected, game_mode

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    winner_name = player_red_name if winner == "red" else player_black_name
    txt         = FONT_BUTTON.render(f"{winner_name} THẮNG!", True, (255, 255, 0))
    txt_rect    = txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))

    btn_replay = pygame.Rect(WIDTH // 2 - 160, HEIGHT // 2 + 80, 150, 60)
    btn_menu   = pygame.Rect(WIDTH // 2 + 10,  HEIGHT // 2 + 80, 150, 60)
    confirm_red = confirm_black = False
    confirm_msg = ""

    while True:
        draw_board()
        screen.blit(overlay, (0, 0))
        screen.blit(txt, txt_rect)

        mp = pygame.mouse.get_pos()
        for rect, label in [(btn_replay, "Chơi lại"), (btn_menu, "Menu")]:
            color = (80, 180, 80) if rect.collidepoint(mp) else (50, 150, 50)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            t = FONT_BUTTON.render(label, True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=rect.center))

        if confirm_msg:
            cm = FONT_TIME.render(confirm_msg, True, (255, 255, 255))
            screen.blit(cm, cm.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 160)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_replay.collidepoint(event.pos):
                    if game_mode == "pvp":
                        if not confirm_red:
                            confirm_red = True
                            confirm_msg = f"{player_red_name} đã đồng ý. Chờ {player_black_name}..."
                        elif not confirm_black:
                            reset_game()
                            return
                    else:
                        reset_game()
                        return
                elif btn_menu.collidepoint(event.pos):
                    menu()
                    setup_game()
                    return

        pygame.display.update()
        clock.tick(60)


# =================== DI CHUYỂN QUÂN ===================

def try_move(sel, target):
    global current_player
    r1, c1 = sel
    r2, c2 = target

    moving_piece  = board.get(r1, c1)
    target_piece  = board.get(r2, c2)

    # Kiểm tra lặp nước
    consec = 0
    for mv in reversed(move_history):
        if mv[0] == (r1, c1) and mv[1] == (r2, c2) and mv[3] == current_player:
            consec += 1
        else:
            break
    if consec >= 3:
        show_message("Không được lặp lại nước này quá 3 lần liên tiếp")
        return sel, False

    if len(move_history) >= 3:
        pair         = frozenset(((r1, c1), (r2, c2)))
        player_moves = [mv for mv in move_history if mv[3] == current_player]
        if len(player_moves) >= 3 and all(
                frozenset((m[0], m[1])) == pair for m in player_moves[-3:]):
            show_message("Lặp lại 3 lần!")
            return sel, False

    if (r1, c1) == (r2, c2):
        return sel, False
    if piece_color(moving_piece) == piece_color(target_piece) and target_piece:
        return sel, False
    if not is_valid_move(moving_piece, r1, c1, r2, c2, board):
        return sel, False

    captured = target_piece
    board.set(r2, c2, moving_piece)
    board.set(r1, c1, "")

    # Ăn tướng → thắng
    if captured in ("帥", "将"):
        winner = "black" if captured == "帥" else "red"
        move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))
        _record_result(winner)
        show_winner(winner)
        return sel, True

    opp = "black" if current_player == "red" else "red"

    # Nước gây chiếu chính mình → không hợp lệ
    if is_checked(current_player, board):
        board.set(r1, c1, moving_piece)
        board.set(r2, c2, captured)
        show_message(f"{current_player.upper()} BỊ CHIẾU!")
        return sel, False

    if is_checked(opp, board):
        show_check_screen(opp)

    if not game_logic.has_any_legal_move(board, opp):
        move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))
        _record_result(current_player)
        show_winner(current_player)
        return sel, True

    move_history.append(((r1, c1), (r2, c2), moving_piece, current_player))
    return sel, True


def _record_result(winner):
    n = len(move_history)
    if game_mode == "pvp":
        save_result(player_red_name,   winner == "red",   vs_machine=False, num_moves=n)
        save_result(player_black_name, winner == "black", vs_machine=False, num_moves=n)
    else:
        save_result(player_red_name, winner == "red", vs_machine=True, num_moves=n)


# =================== TIMEOUT ===================

def handle_timeout():
    global current_player, ai_thinking, ai_move_result
    player = current_player
    moves  = game_logic.get_all_legal_moves(board, player)
    if not moves:
        show_winner("black" if player == "red" else "red")
        return
    if player == "black" and game_mode != "pvp":
        if ai_move_result:
            start, end = ai_move_result
            ai_move_result = None
            _, moved = try_move(start, end)
            if moved:
                current_player = "red"
                set_turn_start()
                return
        mv = random_move(board, "black", history=list(move_history))
        if mv:
            _, moved = try_move(*mv)
            if moved:
                current_player = "red"
                set_turn_start()
                ai_thinking = False
                return
    start, end = random.choice(moves)
    _, moved = try_move(start, end)
    if moved:
        current_player = "black" if player == "red" else "red"
        set_turn_start()


# =================== MENU / SETUP ===================

def menu():
    global game_mode
    buttons = [
        (pygame.Rect(WIDTH // 2 - 100, 150, 200, 50), "PvP",    "pvp"),
        (pygame.Rect(WIDTH // 2 - 100, 230, 200, 50), "Easy",   "de"),
        (pygame.Rect(WIDTH // 2 - 100, 310, 200, 50), "Medium", "trung"),
        (pygame.Rect(WIDTH // 2 - 100, 390, 200, 50), "Hard",   "kho"),
        (pygame.Rect(WIDTH // 2 - 100, 470, 200, 50), "BXH",    "leaderboard"),
    ]
    while True:
        screen.fill((200, 180, 150))
        title = FONT_TITLE.render("Chọn chế độ chơi", True, (0, 0, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        for rect, text, _ in buttons:
            draw_button(rect, text, (180, 200, 220))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for rect, _, mode in buttons:
                    if rect.collidepoint(event.pos):
                        if mode == "leaderboard":
                            leaderboard()
                        else:
                            game_mode = mode
                            return
        pygame.display.flip()
        clock.tick(60)


def setup_game():
    global player_red_name, player_black_name
    player_red_name   = input_player_name(1)
    player_black_name = input_player_name(2) if game_mode == "pvp" else "Máy"
    reset_game()


# =================== MAIN LOOP ===================

menu()
setup_game()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:
                DEBUG = not DEBUG
            if event.key == pygame.K_r:
                print("--- move_history (last 20) ---")
                for i, mv in enumerate(move_history[-20:]):
                    print(i, mv)
            if event.key == pygame.K_h:
                atk = game_logic.find_attackers(board, current_player)
                for item in atk:
                    print(f" - {item[2]} at {item[:2]}")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            try:
                if pause_button_rect and pause_button_rect.collidepoint((mx, my)):
                    now = pygame.time.get_ticks()
                    allowed = int(THINK_TIME.get(current_player, 15) * 1000)
                    if not paused:
                        paused_remaining_ms = max(0, allowed - (now - turn_start_time))
                        paused = True
                    else:
                        if paused_remaining_ms is not None:
                            turn_start_time = now - (allowed - paused_remaining_ms)
                            paused_remaining_ms = None
                        else:
                            set_turn_start()
                        paused = False
                    continue

                if resign_button_rect and resign_button_rect.collidepoint((mx, my)):
                    n   = len(move_history)
                    opp = "black" if current_player == "red" else "red"
                    if game_mode == "pvp":
                        save_result(player_red_name   if current_player == "red"   else player_black_name,
                                    False, vs_machine=False, num_moves=n)
                        save_result(player_black_name if current_player == "red"   else player_red_name,
                                    True,  vs_machine=False, num_moves=n)
                    else:
                        save_result(player_red_name, False, vs_machine=True, num_moves=n)
                    show_winner(opp)
                    continue
            except Exception:
                pass

            if paused:
                continue

            if current_player == "red" or game_mode == "pvp":
                col = round((mx - MARGIN) / CELL)
                row = round((my - TOP_MARGIN) / CELL)
                if 0 <= row < ROWS and 0 <= col < COLS:
                    clicked = (row, col)
                    if selected is None:
                        p = board.get(*clicked)
                        if p and piece_color(p) == current_player:
                            selected    = clicked
                            valid_moves = get_valid_moves(*clicked)
                    else:
                        _, moved = try_move(selected, clicked)
                        if moved:
                            selected       = None
                            valid_moves    = []
                            current_player = "black" if current_player == "red" else "red"
                            set_turn_start()
                        else:
                            p = board.get(*clicked)
                            if p and piece_color(p) == current_player:
                                selected    = clicked
                                valid_moves = get_valid_moves(*clicked)

    if not paused:
        now     = pygame.time.get_ticks()
        allowed = int(THINK_TIME.get(current_player, 15) * 1000)
        if now - turn_start_time >= allowed:
            handle_timeout()

    if not paused and game_mode != "pvp" and current_player == "black":
        if not ai_thinking and ai_move_result is None:
            def _run_ai(bcopy, mode, history):
                global ai_move_result, ai_thinking
                try:
                    ai_move_result = ai_move(bcopy, "black", level=mode, history=history)
                except Exception:
                    ai_move_result = None
                finally:
                    ai_thinking = False

            ai_thinking    = True
            ai_move_result = None
            ai_thread = threading.Thread(
                target=_run_ai,
                args=(board.copy(), game_mode, list(move_history)),
                daemon=True)
            ai_thread.start()

        if not ai_thinking and ai_move_result:
            start, end = ai_move_result
            ai_move_result = None
            if start and end:
                _, moved = try_move(start, end)
                if moved:
                    current_player = "red"
                    selected       = None
                    valid_moves    = []
                    set_turn_start()

    draw_board()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
