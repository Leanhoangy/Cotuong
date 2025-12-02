import pygame
class Board:
    def __init__(self):
        # Bàn cờ 10x9
        self.grid = [
            ["车","马","象","士","将","士","象","马","车"],
            ["", "", "", "", "", "", "", "", ""],
            ["", "砲", "", "", "", "", "", "砲", ""],
            ["卒", "", "卒", "", "卒", "", "卒", "", "卒"],
            ["", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", "", ""],
            ["兵", "", "兵", "", "兵", "", "兵", "", "兵"],
            ["", "炮", "", "", "", "", "", "炮", ""],
            ["", "", "", "", "", "", "", "", ""],
            ["車","馬","相","仕","帥","仕","相","馬","車"]
        ]

    def get(self, r, c):
        """Lấy quân tại vị trí (r, c)"""
        return self.grid[r][c]
    
    # Trong file board.py, thêm phương thức này:
    def set(self, r, c, piece):
        """Đặt quân 'piece' vào vị trí (r, c)"""
        self.grid[r][c] = piece

    def move(self, r1, c1, r2, c2):
        """Di chuyển quân từ (r1, c1) sang (r2, c2)"""
        self.grid[r2][c2] = self.grid[r1][c1]
        self.grid[r1][c1] = ""
        
    
    # ===========================
    # KIỂM TRA LUẬT DI CHUYỂN
    # ===========================
    def is_valid_move(self, r1, c1, r2, c2):
        piece = self.get(r1, c1)

        if piece == "":
            return False

        dr = r2 - r1
        dc = c2 - c1

        # ----- XE -----
        if piece in ["車", "车"]:
            if r1 != r2 and c1 != c2:
                return False
            # kiểm tra đường ngang
            if r1 == r2:
                step = 1 if c2 > c1 else -1
                for c in range(c1 + step, c2, step):
                    if self.get(r1, c) != "":
                        return False
            # kiểm tra đường dọc
            if c1 == c2:
                step = 1 if r2 > r1 else -1
                for r in range(r1 + step, r2, step):
                    if self.get(r, c1) != "":
                        return False
            return True

        # ----- MÃ -----
        if piece in ["馬", "马"]:
            if (abs(dr), abs(dc)) not in [(2, 1), (1, 2)]:
                return False
            # chặn chân
            if abs(dr) == 2 and self.get(r1 + dr//2, c1) != "":
                return False
            if abs(dc) == 2 and self.get(r1, c1 + dc//2) != "":
                return False
            return True

        # ----- TƯỢNG -----
        if piece in ["象", "相"]:
            if abs(dr) != 2 or abs(dc) != 2:
                return False
            # chặn giữa
            if self.get(r1 + dr//2, c1 + dc//2) != "":
                return False
            # tượng không qua sông
            if piece == "象" and r2 > 4:
                return False
            if piece == "相" and r2 < 5:
                return False
            return True

        # ----- SĨ -----
        if piece in ["士", "仕"]:
            if abs(dr) != 1 or abs(dc) != 1:
                return False
            if c2 < 3 or c2 > 5:
                return False
            if piece == "士" and not (0 <= r2 <= 2):
                return False
            if piece == "仕" and not (7 <= r2 <= 9):
                return False
            return True

        # ----- TƯỚNG -----
        if piece in ["将", "帥"]:
            # Di chuyển 1 ô theo 4 hướng trong cung
            if abs(dr) + abs(dc) != 1:
                return False
            if c2 < 3 or c2 > 5:
                return False
            if piece == "将" and not (0 <= r2 <= 2):
                return False
            if piece == "帥" and not (7 <= r2 <= 9):
                return False

            # Kiểm tra luật "tướng đối mặt" (Flying General) sau khi TƯỚNG dự định di chuyển đến (r2,c2)
            # Tìm vị trí tướng còn lại
            other_king_pos = None
            for rr in range(10):
                for cc in range(9):
                    if self.get(rr, cc) in ["将", "帥"] and (rr, cc) != (r1, c1):
                        other_king_pos = (rr, cc)
                        break
                if other_king_pos:
                    break
            if other_king_pos and other_king_pos[1] == c2:
                # Kiểm tra có quân cản giữa (r2,c2) và other_king_pos (bỏ qua ô gốc r1,c1 vì sẽ trống sau khi di chuyển)
                blocked = False
                step = 1 if other_king_pos[0] > r2 else -1
                for r in range(r2 + step, other_king_pos[0], step):
                    if (r, c2) == (r1, c1):  # ô xuất phát sẽ trống sau khi di chuyển
                        continue
                    if self.get(r, c2) != "":
                        blocked = True
                        break
                if not blocked:
                    return False  # Không có quân cản -> phạm luật
            return True

        # ----- TỐT -----
        if piece in ["卒", "兵"]:
            # hướng đi
            if piece == "卒" and r2 < r1:
                return False
            if piece == "兵" and r2 > r1:
                return False

            # qua sông đi ngang: chỉ được đi ngang sau khi đã qua sông
            # - Quân Đen ("卒") bắt đầu ở trên (small r) và qua sông khi r >= 5
            # - Quân Đỏ ("兵") bắt đầu ở dưới (large r) và qua sông khi r <= 4
            if (piece == "卒" and r1 >= 5) or (piece == "兵" and r1 <= 4):
                if abs(dc) == 1 and dr == 0:
                    return True

            # đi thẳng
            if dc != 0:
                return False
            if abs(dr) != 1:
                return False
            return True

        # (Khối kiểm tra Flying General cũ bị đặt sai vị trí đã được hợp nhất ở trên)
   
        # ----- PHÁO -----
        if piece in ["炮", "砲"]:
            count = 0
            if r1 == r2:
                step = 1 if c2 > c1 else -1
                for c in range(c1 + step, c2, step):
                    if self.get(r1, c) != "":
                        count += 1
            elif c1 == c2:
                step = 1 if r2 > r1 else -1
                for r in range(r1 + step, r2, step):
                    if self.get(r, c1) != "":
                        count += 1
            else:
                return False

            # di chuyển không ăn
            if self.get(r2, c2) == "":
                return count == 0

            # ăn → phải có đúng 1 quân chắn
            return count == 1

        return False
    def copy(self):
        new_board = Board()
        new_board.grid = [row[:] for row in self.grid]
        return new_board

    def crossed_river(self, piece, r):
        if piece == "卒": return r > 4
        if piece == "兵": return r < 5
        return False