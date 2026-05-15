import random
import os
import numpy as np

# =================== HÀM HỖ TRỢ ===================

# 14 loại quân — thứ tự khớp với ml_train.py
_PIECES = ["帥","将","仕","士","相","象","車","车","馬","马","炮","砲","兵","卒"]
_PIECE_TO_CH = {p: i for i, p in enumerate(_PIECES)}

_cnn_model = None
_cnn_loaded = False
_eval_cache: dict = {}   # transposition table: board_key → score

def _load_cnn():
    global _cnn_model, _cnn_loaded
    if _cnn_loaded:
        return _cnn_model
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pt")
    if os.path.exists(model_path):
        try:
            import torch
            import torch.nn as nn

            class ChessCNN(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.conv = nn.Sequential(
                        nn.Conv2d(14, 32, kernel_size=3, padding=1),
                        nn.BatchNorm2d(32), nn.ReLU(),
                        nn.Conv2d(32, 64, kernel_size=3, padding=1),
                        nn.BatchNorm2d(64), nn.ReLU(),
                        nn.Conv2d(64, 64, kernel_size=3, padding=1),
                        nn.BatchNorm2d(64), nn.ReLU(),
                    )
                    self.fc = nn.Sequential(
                        nn.Flatten(),
                        nn.Linear(64 * 10 * 9, 128), nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(128, 1),
                    )
                def forward(self, x):
                    return self.fc(self.conv(x)).squeeze(1)

            checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
            net = ChessCNN()
            net.load_state_dict(checkpoint["model_state"])
            net.eval()
            _cnn_model = net
        except Exception:
            pass
    _cnn_loaded = True
    return _cnn_model

def board_to_features(board):
    """Vector 90 số — dùng cho fallback (giữ tương thích)."""
    t = np.zeros((1, 14, 10, 9), dtype=np.float32)
    for r in range(10):
        for c in range(9):
            p = board.get(r, c)
            if p and p in _PIECE_TO_CH:
                t[0, _PIECE_TO_CH[p], r, c] = 1.0
    return t

def piece_color(piece):
    red_pieces = {"帥","仕","相","車","馬","炮","兵"}
    black_pieces = {"将","士","象","车","马","砲","卒"}
    if piece in red_pieces:
        return "red"
    elif piece in black_pieces:
        return "black"
    return None

def opponent(player):
    return "black" if player=="red" else "red"

def _board_key(board):
    return tuple(board.get(r, c) for r in range(10) for c in range(9))

def evaluate_board(board):
    key = _board_key(board)
    if key in _eval_cache:
        return _eval_cache[key]

    model = _load_cnn()
    if model is not None:
        import torch
        with torch.no_grad():
            t = torch.tensor(board_to_features(board))
            score = float(model(t).item())
    else:
        # Fallback khi chưa train CNN
        piece_values = {
            "帥":1000,"将":1000,
            "仕":20,"士":20,
            "相":20,"象":20,
            "車":90,"车":90,
            "馬":45,"马":45,
            "炮":50,"砲":50,
            "兵":10,"卒":10
        }
        score = 0
        for r in range(10):
            for c in range(9):
                p = board.get(r, c)
                if piece_color(p) == "red":
                    score += piece_values.get(p, 0)
                elif piece_color(p) == "black":
                    score -= piece_values.get(p, 0)

    if len(_eval_cache) < 200_000:
        _eval_cache[key] = score
    return score

def get_valid_moves(board, r, c, history=None):
    """Danh sách nước đi hợp lệ từ (r,c)"""
    moves = []
    piece = board.get(r,c)
    if piece == "":
        return moves
    for r2 in range(10):
        for c2 in range(9):
            if (r2, c2) == (r, c): continue
            target_piece = board.get(r2, c2)
            if piece_color(piece) == piece_color(target_piece) and target_piece != "":
                continue
            if board.is_valid_move(r, c, r2, c2):
                # Simulate move and ensure it doesn't leave player's king in check
                temp = board.copy()
                temp.set(r2, c2, piece)
                temp.set(r, c, "")
                # Check repetition history: do not allow moves repeated 4 times consecutively by same player
                if history:
                    consec = 0
                    for mv in reversed(history):
                        if mv[0] == (r, c) and mv[1] == (r2, c2) and mv[3] == piece_color(piece):
                            consec += 1
                        else:
                            break
                    if consec >= 3:
                        # there were already 3 consecutive identical moves, skip this move
                        continue

                # Per-player repetition rule: if this player's last 3 moves all used
                # the same unordered pair, skip this candidate (would be the 4th).
                if history:
                    pair = frozenset(((r, c), (r2, c2)))
                    player_moves = [mv for mv in history if mv[3] == piece_color(piece)]
                    recent_player_moves = player_moves[-3:]
                    if len(recent_player_moves) == 3 and all(frozenset((m[0], m[1])) == pair for m in recent_player_moves):
                        continue
                # find king position for the moving piece's color
                king_char = "帥" if piece_color(piece) == "red" else "将"
                king_pos = None
                for rr in range(10):
                    for cc in range(9):
                        if temp.get(rr, cc) == king_char:
                            king_pos = (rr, cc)
                            break
                    if king_pos:
                        break
                # If king missing (shouldn't happen), skip this move
                if king_pos is None:
                    continue
                kr, kc = king_pos
                # Check if any opponent piece attacks the king on temp board
                opponent_color = opponent(piece_color(piece))
                attacked = False
                for rr in range(10):
                    for cc in range(9):
                        p2 = temp.get(rr, cc)
                        if p2 != "" and piece_color(p2) == opponent_color:
                            try:
                                if temp.is_valid_move(rr, cc, kr, kc):
                                    attacked = True
                                    break
                            except Exception:
                                pass
                    if attacked:
                        break
                if not attacked:
                    moves.append((r2, c2))
    return moves
def ai_move(board, player, level="de", history=None):
    """
    Trả về nước đi của AI: ((r1,c1),(r2,c2))
    level = "de" | "trung" | "kho"
    """
    if level == "de":
        return random_move(board, player, history=history)
    elif level == "trung":
        _, move = minimax(board, depth=1, maximizing_player=(player=="red"), player=player, history=history)
        return move
    elif level == "kho":
        _, move = minimax(board, depth=3, maximizing_player=(player=="red"), player=player, history=history)
        return move
    return None
def random_move(board, player, history=None):
    """AI mức dễ: chọn nước đi hợp lệ ngẫu nhiên"""
    moves = []
    for r in range(10):
        for c in range(9):
            piece = board.get(r, c)
            if piece_color(piece) == player:
                for r2, c2 in get_valid_moves(board, r, c, history=history):
                    moves.append(((r, c), (r2, c2)))
    if moves:
        return random.choice(moves)
    return None
def minimax(board, depth, maximizing_player, player, alpha=-float("inf"), beta=float("inf"), history=None):
    # Khi hết độ sâu: trả về điểm của bàn cờ
    if depth == 0:
        return evaluate_board(board), None

    best_move = None

    if maximizing_player:
        # Lượt của RED (muốn điểm cao)
        max_eval = -float("inf")

        for r in range(10):
            for c in range(9):
                piece = board.get(r, c)
                if piece_color(piece) == player:
                    for r2, c2 in get_valid_moves(board, r, c, history=history):
                        temp = board.copy()
                        temp.set(r2, c2, piece)
                        temp.set(r, c, "")
                        # extend history for recursive evaluation
                        new_history = list(history) + [((r, c), (r2, c2), piece, player)] if history else [((r, c), (r2, c2), piece, player)]

                        score, _ = minimax(temp, depth-1, False, opponent(player), alpha, beta, history=new_history)

                        if score > max_eval:
                            max_eval = score
                            best_move = ((r, c), (r2, c2))

                        alpha = max(alpha, score)
                        if beta <= alpha:
                            return max_eval, best_move   # alpha-beta cắt nhanh

        return max_eval, best_move

    else:
        # Lượt của BLACK (muốn điểm thấp)
        min_eval = float("inf")

        for r in range(10):
            for c in range(9):
                piece = board.get(r, c)
                if piece_color(piece) == player:
                    for r2, c2 in get_valid_moves(board, r, c, history=history):
                        temp = board.copy()
                        temp.set(r2, c2, piece)
                        temp.set(r, c, "")
                        new_history = list(history) + [((r, c), (r2, c2), piece, player)] if history else [((r, c), (r2, c2), piece, player)]

                        score, _ = minimax(temp, depth-1, True, opponent(player), alpha, beta, history=new_history)

                        if score < min_eval:
                            min_eval = score
                            best_move = ((r, c), (r2, c2))

                        beta = min(beta, score)
                        if beta <= alpha:
                            return min_eval, best_move   # alpha-beta cắt nhanh

        return min_eval, best_move

