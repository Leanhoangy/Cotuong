"""
Khởi tạo pygame, hằng số màn hình, font chữ, và các hàm vẽ cơ bản.
Import module này sẽ tự động init pygame và tạo cửa sổ game.
"""

import pygame
import sys

pygame.init()
pygame.font.init()

# =================== HẰNG SỐ MÀN HÌNH ===================
CELL            = 60
MARGIN          = 40
TOP_BAR_HEIGHT  = 28
TOP_BAR_PADDING = 8
TOP_MARGIN      = MARGIN + TOP_BAR_HEIGHT + TOP_BAR_PADDING
COLS            = 9
ROWS            = 10
WIDTH           = MARGIN * 2 + CELL * (COLS - 1)
HEIGHT          = MARGIN * 2 + CELL * (ROWS - 1) + TOP_BAR_HEIGHT + TOP_BAR_PADDING

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cờ Tướng")
clock  = pygame.time.Clock()

piece_font   = pygame.font.SysFont("Microsoft YaHei", 32)
red_pieces   = {"帥", "仕", "相", "車", "馬", "炮", "兵"}
black_pieces = {"将", "士", "象", "车", "马", "砲", "卒"}

# =================== FONT TIẾNG VIỆT ===================

def supports_vietnamese(font_name):
    try:
        path = pygame.font.match_font(font_name)
        if not path:
            return False
        font = pygame.font.Font(path, 32)
        font.render("Chọn chế độ chơi", True, (0, 0, 0))
        return True
    except Exception:
        return False


def find_best_vietnamese_font():
    preferred = ["segoeui", "tahoma", "calibri", "verdana",
                 "arialunicode", "arialuni", "arial unicode ms", "micross"]
    for f in preferred:
        if supports_vietnamese(f):
            return pygame.font.match_font(f)
    for f in pygame.font.get_fonts():
        if supports_vietnamese(f):
            return pygame.font.match_font(f)
    return None


VIET_FONT_PATH = find_best_vietnamese_font()
FONT_TITLE  = pygame.font.Font(VIET_FONT_PATH, 50)
FONT_BUTTON = pygame.font.Font(VIET_FONT_PATH, 36)
FONT_TIME   = pygame.font.Font(VIET_FONT_PATH, 12)
FONT_BXH    = pygame.font.Font(VIET_FONT_PATH, 22)

# =================== HÀM VẼ CƠ BẢN ===================

def draw_piece(row, col, text, color):
    x = MARGIN + col * CELL
    y = TOP_MARGIN + row * CELL
    pygame.draw.circle(screen, (240, 220, 180), (x, y), 25)
    pygame.draw.circle(screen, (0, 0, 0),       (x, y), 25, 2)
    img  = piece_font.render(text, True, color)
    rect = img.get_rect(center=(x, y))
    screen.blit(img, rect)


def draw_all_pieces(board):
    for r in range(ROWS):
        for c in range(COLS):
            p = board.get(r, c)
            if not p:
                continue
            color = (255, 0, 0) if p in red_pieces else (0, 0, 0)
            draw_piece(r, c, p, color)


def draw_selected(selected):
    if selected is None:
        return
    r, c = selected
    x = MARGIN  + c * CELL
    y = TOP_MARGIN + r * CELL
    pygame.draw.circle(screen, (255, 255, 0, 80), (x, y), 30)


def draw_button(rect, text, color):
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 2)
    txt      = FONT_BUTTON.render(text, True, (0, 0, 0))
    txt_rect = txt.get_rect(center=rect.center)
    screen.blit(txt, txt_rect)
