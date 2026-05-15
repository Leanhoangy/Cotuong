"""
Benchmark: đo win-rate giữa các cấp AI.

Cách chạy:
    cd Cotuong
    python benchmark.py

Các matchup:
    1. Random  vs CNN (khó)
    2. Minimax vs CNN (khó)
    3. CNN     vs CNN (mirror)
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board
from ai import ai_move, piece_color, get_valid_moves
import ai as _ai_module

MAX_MOVES   = 200   # tránh ván vô tận
GAMES_EACH  = 20    # số ván mỗi matchup (10 đỏ trước + 10 đen trước)

# =================== PHÁT HIỆN KẾT THÚC VÁN ===================

def king_alive(board, color):
    king = "帥" if color == "red" else "将"
    for r in range(10):
        for c in range(9):
            if board.get(r, c) == king:
                return True
    return False

def has_any_move(board, player):
    for r in range(10):
        for c in range(9):
            if piece_color(board.get(r, c)) == player:
                if get_valid_moves(board, r, c):
                    return True
    return False

def play_game(red_level: str, black_level: str) -> str:
    """
    Chạy 1 ván không hiển thị.
    Trả về: 'red' | 'black' | 'draw'
    """
    _ai_module._eval_cache.clear()   # reset transposition table mỗi ván
    board   = Board()
    player  = "red"
    history = []

    for _ in range(MAX_MOVES):
        level = red_level if player == "red" else black_level
        move  = ai_move(board, player, level=level, history=history)

        if move is None:
            return "black" if player == "red" else "red"  # hết nước = thua

        (r1, c1), (r2, c2) = move
        piece = board.get(r1, c1)
        board.set(r2, c2, piece)
        board.set(r1, c1, "")
        history.append(((r1, c1), (r2, c2), piece, player))

        # Kiểm tra tướng bị ăn
        opp = "black" if player == "red" else "red"
        if not king_alive(board, opp):
            return player

        player = opp

    return "draw"

# =================== CHẠY MATCHUP ===================

def run_matchup(level_a: str, level_b: str, n_games: int = GAMES_EACH):
    """
    Chạy n_games ván, đổi màu đều.
    Trả về dict: wins_a, wins_b, draws
    """
    wins_a = wins_b = draws = 0
    half = n_games // 2

    for i in range(n_games):
        # Nửa đầu: A đỏ — nửa sau: A đen
        if i < half:
            red_lvl, black_lvl = level_a, level_b
            a_color = "red"
        else:
            red_lvl, black_lvl = level_b, level_a
            a_color = "black"

        winner = play_game(red_lvl, black_lvl)

        if winner == "draw":
            draws += 1
        elif winner == a_color:
            wins_a += 1
        else:
            wins_b += 1

        # Progress
        done = i + 1
        bar  = "█" * (done * 20 // n_games) + "░" * (20 - done * 20 // n_games)
        print(f"\r  [{bar}] {done}/{n_games}", end="", flush=True)

    print()
    return wins_a, wins_b, draws

# =================== MAIN ===================

LEVEL_NAMES = {"de": "Random", "trung": "Minimax-1", "kho": "CNN+Minimax-3"}

def print_result(name_a, name_b, wins_a, wins_b, draws, n):
    wr_a = wins_a / n * 100
    wr_b = wins_b / n * 100
    wr_d = draws  / n * 100
    print(f"  {name_a:<14} {wins_a:>3}W  {wins_b:>3}L  {draws:>3}D   "
          f"Win-rate: {wr_a:5.1f}%  |  {name_b}: {wr_b:.1f}%")

if __name__ == "__main__":
    # de=Random | trung=Minimax depth=1 | kho=Minimax depth=3
    # Tất cả đều dùng CNN trong evaluate_board (ai.py)
    matchups = [
        ("de",    "trung", "Random",        "CNN+Minimax-1"),
        ("de",    "kho",   "Random",        "CNN+Minimax-3"),
        ("trung", "kho",   "CNN+Minimax-1", "CNN+Minimax-3"),
    ]

    print("=" * 60)
    print("  BENCHMARK — Cờ Tướng AI Win-Rate")
    print(f"  {GAMES_EACH} ván mỗi matchup (đổi màu đều)")
    print("=" * 60)

    all_results = []
    for lvl_a, lvl_b, name_a, name_b in matchups:
        print(f"\n{name_a} vs {name_b}")
        wins_a, wins_b, draws = run_matchup(lvl_a, lvl_b, GAMES_EACH)
        all_results.append((name_a, name_b, wins_a, wins_b, draws))
        print_result(name_a, name_b, wins_a, wins_b, draws, GAMES_EACH)

    print("\n" + "=" * 60)
    print("  TÓM TẮT")
    print("=" * 60)
    for name_a, name_b, wins_a, wins_b, draws in all_results:
        wr = wins_a / GAMES_EACH * 100
        print(f"  {name_a} vs {name_b}: {wr:.1f}% win-rate cho {name_a}")
