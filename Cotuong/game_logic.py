"""
Logic thuần túy của game Cờ Tướng — không dùng pygame, không dùng biến toàn cục.
Tất cả hàm nhận board/player làm tham số.
"""

from ai import piece_color

ROWS, COLS = 10, 9


def find_king(board, player):
    king_char = "帥" if player == "red" else "将"
    for r in range(ROWS):
        for c in range(COLS):
            if board.get(r, c) == king_char:
                return (r, c)
    return None


def is_checked(board, player):
    """Trả về (bool, attacker_tuple|None, king_pos|None) — không sửa biến toàn cục."""
    king_pos = find_king(board, player)
    if king_pos is None:
        return False, None, None
    kr, kc = king_pos
    opp = "black" if player == "red" else "red"
    opp_king = "将" if player == "red" else "帥"

    for r in range(ROWS):
        for c in range(COLS):
            p = board.get(r, c)
            if p and piece_color(p) == opp:
                try:
                    if board.is_valid_move(r, c, kr, kc):
                        return True, (r, c, p), king_pos
                except Exception:
                    pass

    # Flying General
    for step in [-1, 1]:
        r = kr + step
        while 0 <= r < ROWS:
            p = board.get(r, kc)
            if p:
                if p == opp_king:
                    return True, (r, kc, p), king_pos
                break
            r += step

    return False, None, None


def find_attackers(board, player):
    """Danh sách (r, c, piece) đang tấn công tướng của player."""
    king_pos = find_king(board, player)
    if king_pos is None:
        return []
    kr, kc = king_pos
    opp = "black" if player == "red" else "red"
    result = []
    for r in range(ROWS):
        for c in range(COLS):
            p = board.get(r, c)
            if p and piece_color(p) == opp:
                try:
                    if board.is_valid_move(r, c, kr, kc):
                        result.append((r, c, p))
                except Exception:
                    pass
    return result


def has_any_legal_move(board, player):
    for r1 in range(ROWS):
        for c1 in range(COLS):
            p = board.get(r1, c1)
            if not p or piece_color(p) != player:
                continue
            for r2 in range(ROWS):
                for c2 in range(COLS):
                    if (r1, c1) == (r2, c2):
                        continue
                    if piece_color(board.get(r2, c2)) == player:
                        continue
                    if not board.is_valid_move(r1, c1, r2, c2):
                        continue
                    temp = board.copy()
                    temp.set(r2, c2, p)
                    temp.set(r1, c1, "")
                    checked, _, _ = is_checked(temp, player)
                    if not checked:
                        return True
    return False


def check_game_over(board, player):
    if find_king(board, player) is None:
        return True
    checked, _, _ = is_checked(board, player)
    return checked and not has_any_legal_move(board, player)


def get_all_legal_moves(board, player):
    moves = []
    for r in range(ROWS):
        for c in range(COLS):
            p = board.get(r, c)
            if not p or piece_color(p) != player:
                continue
            for r2 in range(ROWS):
                for c2 in range(COLS):
                    if (r, c) == (r2, c2):
                        continue
                    if piece_color(board.get(r2, c2)) == player:
                        continue
                    if not board.is_valid_move(r, c, r2, c2):
                        continue
                    temp = board.copy()
                    temp.set(r2, c2, p)
                    temp.set(r, c, "")
                    checked, _, _ = is_checked(temp, player)
                    if not checked:
                        moves.append(((r, c), (r2, c2)))
    return moves
