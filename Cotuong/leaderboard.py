"""
Quản lý bảng xếp hạng: đọc/ghi CSV và hiển thị màn hình BXH.
"""

import csv
import os
import sys
import pygame

from ui import (screen, clock, FONT_BUTTON, FONT_BXH, FONT_TIME,
                WIDTH, HEIGHT, draw_button)

FILE_PATH = "highscore.csv"

# Tạo file nếu chưa có
if not os.path.exists(FILE_PATH):
    with open(FILE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Tên", "DiemPvP", "Thắng", "Thua", "DiemMay", "VsMáy"])
        writer.writeheader()


# =================== ĐỌC / GHI ===================

def save_result(name: str, win: bool, vs_machine: bool = False, num_moves: int = 0):
    """Cập nhật kết quả trận đấu vào highscore.csv."""
    data = {}
    try:
        with open(FILE_PATH, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ten = row.get("Tên", "").strip()
                if not ten:
                    continue
                data[ten] = {
                    "DiemPvP": int(row.get("DiemPvP") or 0),
                    "Thắng":   int(row.get("Thắng")   or 0),
                    "Thua":    int(row.get("Thua")     or 0),
                    "DiemMay": int(row.get("DiemMay")  or 0),
                    "VsMáy":   int(row.get("VsMáy")    or 0),
                }
    except FileNotFoundError:
        pass
    except Exception as e:
        print("Lỗi đọc highscore:", e)

    if name not in data:
        data[name] = {"DiemPvP": 1200, "Thắng": 0, "Thua": 0, "DiemMay": 1200, "VsMáy": 0}

    bonus = max(100, 500 - num_moves * 5) if win else -50

    if vs_machine:
        if win:
            data[name]["VsMáy"] += 1
        data[name]["DiemMay"] += bonus
    else:
        if win:
            data[name]["Thắng"] += 1
        else:
            data[name]["Thua"] += 1
        data[name]["DiemPvP"] += bonus

    try:
        with open(FILE_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Tên", "DiemPvP", "Thắng", "Thua", "DiemMay", "VsMáy"])
            writer.writeheader()
            for ten, v in data.items():
                writer.writerow({"Tên": ten, **v})
    except Exception as e:
        print("Lỗi ghi highscore:", e)


# =================== MÀN HÌNH NHẬP TÊN ===================

def input_player_name(player_num: int) -> str:
    name = ""
    input_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 30, 300, 60)

    while True:
        screen.fill((200, 180, 150))
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        txt = FONT_BUTTON.render(
            f"Tên người chơi {player_num}: {name + cursor}", True, (0, 0, 0))
        screen.blit(txt, (input_rect.x + 5, input_rect.y + 15))
        pygame.draw.rect(screen, (0, 0, 0), input_rect, 2)
        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if name.strip():
                        return name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode.isalpha() or event.unicode.isspace() or event.unicode.isdigit():
                    name += event.unicode
                while FONT_BUTTON.size(name)[0] > input_rect.width - 10:
                    name = name[:-1]


# =================== MÀN HÌNH BXH ===================

def leaderboard():
    entries = []
    try:
        with open(FILE_PATH, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    entries.append({
                        "Tên":     row.get("Tên", ""),
                        "DiemPvP": int(row.get("DiemPvP", 0)),
                        "Thắng":   int(row.get("Thắng",   0)),
                        "Thua":    int(row.get("Thua",     0)),
                        "DiemMay": int(row.get("DiemMay",  0)),
                        "VsMáy":   int(row.get("VsMáy",    0)),
                    })
                except ValueError:
                    pass
    except FileNotFoundError:
        pass

    pvp_sorted = sorted(
        [e for e in entries if e["Thắng"] > 0 or e["Thua"] > 0],
        key=lambda x: (-x["DiemPvP"], -x["Thắng"], x["Thua"]))
    vsm_sorted = sorted(
        [e for e in entries if e["VsMáy"] > 0 or e["DiemMay"] != 1200],
        key=lambda x: (-x["DiemMay"], -x["VsMáy"]))

    back_rect = pygame.Rect(20, 20, 120, 40)
    font_rows = None
    for cand in ["Consolas", "Courier New", "Lucida Console"]:
        try:
            font_rows = pygame.font.SysFont(cand, 20)
            break
        except Exception:
            continue
    if font_rows is None:
        font_rows = FONT_BXH

    running = True
    while running:
        screen.fill((220, 210, 200))
        title = FONT_BUTTON.render("Bảng xếp hạng", True, (0, 0, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

        pvp_x = 30
        sep_x = WIDTH // 2 + 40
        vm_x  = min(sep_x + 50, WIDTH - 200)
        sep_x = min(sep_x, vm_x - 30)
        pygame.draw.line(screen, (0, 0, 0), (sep_x, 70), (sep_x, HEIGHT - 40), 1)

        screen.blit(FONT_BXH.render("Người vs Người", True, (0, 0, 0)), (pvp_x, 90))
        screen.blit(font_rows.render("#  Tên   Điểm   Thắng  Thua", True, (0, 0, 0)), (pvp_x, 120))
        for i, row in enumerate(pvp_sorted[:15], 1):
            line = f"{i:<2} {row['Tên'][:7]:<5} {row['DiemPvP']:<8} {row['Thắng']:<4} {row['Thua']}"
            screen.blit(font_rows.render(line, True, (0, 0, 0)), (pvp_x, 120 + i * 24))

        screen.blit(FONT_BXH.render("Chơi với Máy", True, (0, 0, 0)), (vm_x, 90))
        screen.blit(font_rows.render("#  Tên     Điểm", True, (0, 0, 0)), (vm_x, 120))
        for i, row in enumerate(vsm_sorted[:15], 1):
            line = f"{i:<2} {row['Tên'][:7]:<7} {row['DiemMay']}"
            screen.blit(font_rows.render(line, True, (0, 0, 0)), (vm_x, 120 + i * 24))

        draw_button(back_rect, "Quay lại", (180, 200, 220))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_rect.collidepoint(event.pos):
                    running = False
        pygame.display.flip()
        clock.tick(60)
