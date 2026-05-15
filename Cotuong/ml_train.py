"""
Sinh dữ liệu + huấn luyện CNN (PyTorch) để thay thế evaluate_board trong Minimax.

Kiến trúc:
    Input  : (14, 10, 9) — 14 kênh loại quân, bàn cờ 10×9
    Conv1  : 32 filters 3×3, ReLU
    Conv2  : 64 filters 3×3, ReLU
    Flatten→ Dense 128 → Dense 1 (score)

Cách chạy:
    cd Cotuong
    python ml_train.py

Output: model.pt  (tự động được load bởi ai.py khi chạy game)
"""

import random
import os
import sys
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import matplotlib
matplotlib.use("Agg")   # không cần GUI
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board
from ai import get_valid_moves, piece_color

# =================== ENCODE BÀN CỜ ===================
# 14 loại quân → mỗi loại 1 kênh nhị phân (0/1)
PIECES = ["帥","将","仕","士","相","象","車","车","馬","马","炮","砲","兵","卒"]
PIECE_TO_CH = {p: i for i, p in enumerate(PIECES)}

def board_to_tensor(board) -> np.ndarray:
    """Trả về array (14, 10, 9) — mỗi kênh là binary map của 1 loại quân."""
    t = np.zeros((14, 10, 9), dtype=np.float32)
    for r in range(10):
        for c in range(9):
            p = board.get(r, c)
            if p and p in PIECE_TO_CH:
                t[PIECE_TO_CH[p], r, c] = 1.0
    return t

# =================== PIECE-SQUARE TABLES (nhãn huấn luyện) ===================
_PST_CHARIOT = [
    [14,14,12,18,16,18,12,14,14],
    [16,20,18,24,26,24,18,20,16],
    [12,12,12,18,18,18,12,12,12],
    [12,18,16,22,22,22,16,18,12],
    [12,14,12,18,18,18,12,14,12],
    [12,16,14,20,20,20,14,16,12],
    [ 6,10, 8,15,15,15, 8,10, 6],
    [ 4, 8, 6,14,12,14, 6, 8, 4],
    [ 8, 4, 8,16, 8,16, 8, 4, 8],
    [-2,10, 6,14,12,14, 6,10,-2],
]
_PST_HORSE = [
    [ 4, 8,16,12, 4,12,16, 8, 4],
    [ 4,10,28,16, 8,16,28,10, 4],
    [12,14,16,20,18,20,16,14,12],
    [ 8,24,18,24,20,24,18,24, 8],
    [ 6,16,14,18,16,18,14,16, 6],
    [ 4,12,16,14,12,14,16,12, 4],
    [ 4, 8,12,11, 8,11,12, 8, 4],
    [ 4, 8, 4, 4, 8, 4, 4, 8, 4],
    [-10,-2, 4, 4,-2, 4, 4,-2,-10],
    [ 0,-4, 0, 0,-4, 0, 0,-4, 0],
]
_PST_CANNON = [
    [ 6, 4, 0,-10,-12,-10, 0, 4, 6],
    [ 2, 2, 0, -4,-14, -4, 0, 2, 2],
    [ 2, 6, 4,  0,-10,  0, 4, 6, 2],
    [ 0, 0, 0,  2,  6,  2, 0, 0, 0],
    [ 0, 0, 0,  2,  6,  2, 0, 0, 0],
    [ 4, 0, 4,  2,  6,  2, 4, 0, 4],
    [ 0, 0, 0,  2,  4,  2, 0, 0, 0],
    [ 4, 0, 8,  0,  2,  0, 8, 0, 4],
    [ 0, 2, 4,  6,  6,  6, 4, 2, 0],
    [ 0, 0, 2,  6,  6,  6, 2, 0, 0],
]
_PST_SOLDIER = [
    [ 0, 3, 6, 9,12, 9, 6, 3, 0],
    [18,36,56,80,120,80,56,36,18],
    [14,26,42,60,80,60,42,26,14],
    [10,20,30,34,40,34,30,20,10],
    [ 2, 4, 8,16,32,16, 8, 4, 2],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0],
]
_PST_GENERAL = [
    [0]*9, [0]*9, [0]*9, [0]*9, [0]*9, [0]*9, [0]*9,
    [0,0,0,1,2,1,0,0,0],
    [0,0,0,2,4,2,0,0,0],
    [0,0,0,1,2,1,0,0,0],
]

_RED_PST  = {"車":_PST_CHARIOT,"馬":_PST_HORSE,"炮":_PST_CANNON,"兵":_PST_SOLDIER,"帥":_PST_GENERAL}
_BLACK_PST = {"车":_PST_CHARIOT,"马":_PST_HORSE,"砲":_PST_CANNON,"卒":_PST_SOLDIER,"将":_PST_GENERAL}

PIECE_VALUES = {
    "帥":1000,"将":1000,"仕":20,"士":20,"相":20,"象":20,
    "車":90,"车":90,"馬":45,"马":45,"炮":50,"砲":50,"兵":10,"卒":10,
}

def pst_evaluate(board) -> float:
    score = 0.0
    for r in range(10):
        for c in range(9):
            p = board.get(r, c)
            if not p:
                continue
            val = PIECE_VALUES.get(p, 0)
            if piece_color(p) == "red":
                bonus = _RED_PST.get(p, [[0]*9]*10)[r][c] if p in _RED_PST else 0
                score += val + bonus
            else:
                bonus = _BLACK_PST.get(p, [[0]*9]*10)[9 - r][c] if p in _BLACK_PST else 0
                score -= val + bonus
    return score

# =================== SINH DỮ LIỆU ===================
def generate_position(n_moves: int) -> Board:
    board = Board()
    player = "red"
    for _ in range(n_moves):
        moves = []
        for r in range(10):
            for c in range(9):
                if piece_color(board.get(r, c)) == player:
                    for r2, c2 in get_valid_moves(board, r, c):
                        moves.append(((r, c), (r2, c2)))
        if not moves:
            break
        (r1, c1), (r2, c2) = random.choice(moves)
        piece = board.get(r1, c1)
        board.set(r2, c2, piece)
        board.set(r1, c1, "")
        player = "black" if player == "red" else "red"
    return board

def generate_dataset(n_samples: int = 6000):
    X, y = [], []
    print(f"Đang sinh {n_samples} thế cờ ...")
    for i in range(n_samples):
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{n_samples} mẫu hoàn thành")
        board = generate_position(random.randint(0, 50))
        X.append(board_to_tensor(board))
        y.append(pst_evaluate(board))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

# =================== KIẾN TRÚC CNN ===================
class ChessCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(14, 32, kernel_size=3, padding=1),  # (32,10,9)
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),  # (64,10,9)
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),  # (64,10,9)
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 10 * 9, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
        )

    def forward(self, x):
        return self.fc(self.conv(x)).squeeze(1)


def train(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        loss = criterion(model(X_batch), y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(y_batch)
    return total_loss / len(loader.dataset)


def r2_score(y_true, y_pred):
    ss_res = ((y_true - y_pred) ** 2).sum()
    ss_tot = ((y_true - y_true.mean()) ** 2).sum()
    return 1 - ss_res / ss_tot


# =================== MAIN ===================
if __name__ == "__main__":
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    X, y = generate_dataset(n_samples=6000)
    print(f"\nDataset: {len(X)} mẫu | Input shape: {X[0].shape}")
    print(f"Score  : min={y.min():.1f}  max={y.max():.1f}  mean={y.mean():.1f}")

    # Train/test split thủ công
    idx = np.random.permutation(len(X))
    split = int(0.8 * len(X))
    tr, te = idx[:split], idx[split:]

    X_train = torch.tensor(X[tr])
    y_train = torch.tensor(y[tr])
    X_test  = torch.tensor(X[te])
    y_test  = torch.tensor(y[te])

    train_ds = TensorDataset(X_train, y_train)
    loader   = DataLoader(train_ds, batch_size=64, shuffle=True)

    model     = ChessCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)
    criterion = nn.MSELoss()

    print(f"\nHuấn luyện CNN — {sum(p.numel() for p in model.parameters()):,} tham số")
    best_r2, best_state = -999, None
    history = {"epoch": [], "loss": [], "r2_train": [], "r2_test": []}

    for epoch in range(60):
        loss = train(model, loader, optimizer, criterion, device)
        scheduler.step()
        model.eval()
        with torch.no_grad():
            pred_tr = model(X_train.to(device)).cpu()
            pred_te = model(X_test.to(device)).cpu()
        r2_tr = r2_score(y_train, pred_tr).item()
        r2_te = r2_score(y_test,  pred_te).item()

        history["epoch"].append(epoch + 1)
        history["loss"].append(loss)
        history["r2_train"].append(r2_tr)
        history["r2_test"].append(r2_te)

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d} | loss={loss:.2f} | R² train={r2_tr:.4f} | R² test={r2_te:.4f}")
        if r2_te > best_r2:
            best_r2 = r2_te
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    model.eval()

    # ---- Lưu model ----
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pt")
    torch.save({"model_state": best_state, "arch": "ChessCNN"}, model_path)
    print(f"\nBest R² test : {best_r2:.4f}")
    print(f"Model lưu   : {model_path}")

    # ---- Vẽ training curve ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(history["epoch"], history["loss"], color="steelblue", linewidth=2)
    ax1.set_title("Training Loss (MSE)")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.grid(True, alpha=0.3)

    ax2.plot(history["epoch"], history["r2_train"], label="Train", color="steelblue", linewidth=2)
    ax2.plot(history["epoch"], history["r2_test"],  label="Test",  color="tomato",    linewidth=2)
    ax2.axhline(y=best_r2, color="gray", linestyle="--", alpha=0.6,
                label=f"Best R² test = {best_r2:.4f}")
    ax2.set_title("R² Score theo Epoch")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("R²")
    ax2.set_ylim(0, 1.05)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.suptitle("CNN Training Curve — Cờ Tướng AI", fontsize=13, fontweight="bold")
    plt.tight_layout()

    chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_curve.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"Biểu đồ lưu : {chart_path}")
    print("Chạy lại game — AI sẽ dùng CNN mới!")
