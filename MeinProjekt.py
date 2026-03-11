"""
Schachprogramm mit grafischer Oberfläche (Tkinter).
Spieler vs. Spieler mit vollständiger Regelumsetzung:
- Alle Figurzüge inkl. Rochade, En Passant, Bauernumwandlung
- Schach-, Schachmatt- und Patterkennung
"""

import tkinter as tk
from tkinter import messagebox
# ── Konstanten ──────────────────────────────────────────────────────────────

BOARD_SIZE = 8
SQUARE_SIZE = 70
WHITE = "white"
BLACK = "black"

# Unicode-Schachfiguren
PIECE_SYMBOLS = {
    ("K", WHITE): "\u2654", ("Q", WHITE): "\u2655", ("R", WHITE): "\u2656",
    ("B", WHITE): "\u2657", ("N", WHITE): "\u2658", ("P", WHITE): "\u2659",
    ("K", BLACK): "\u265A", ("Q", BLACK): "\u265B", ("R", BLACK): "\u265C",
    ("B", BLACK): "\u265D", ("N", BLACK): "\u265E", ("P", BLACK): "\u265F",
}

COLOR_LIGHT = "#F0D9B5"
COLOR_DARK = "#B58863"
COLOR_SELECTED = "#7FC97F"
COLOR_MOVE = "#CDD26A"


# ── Figur-Klasse ────────────────────────────────────────────────────────────

class Piece:
    def __init__(self, kind, color):
        self.kind = kind        # K, Q, R, B, N, P
        self.color = color      # WHITE / BLACK
        self.has_moved = False

    def symbol(self):
        return PIECE_SYMBOLS[(self.kind, self.color)]

    def copy(self):
        p = Piece(self.kind, self.color)
        p.has_moved = self.has_moved
        return p


# ── Brett-Logik ─────────────────────────────────────────────────────────────

class Board:
    def __init__(self):
        self.grid = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.turn = WHITE
        self.en_passant_target = None  # (row, col) des schlagbaren Feldes
        self.move_history = []
        self._setup()

    def _setup(self):
        order = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for col in range(BOARD_SIZE):
            self.grid[0][col] = Piece(order[col], BLACK)
            self.grid[1][col] = Piece("P", BLACK)
            self.grid[6][col] = Piece("P", WHITE)
            self.grid[7][col] = Piece(order[col], WHITE)

    # ── Hilfsmethoden ───────────────────────────────────────────────────────

    def get(self, r, c):
        if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
            return self.grid[r][c]
        return None

    def in_bounds(self, r, c):
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

    def find_king(self, color):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = self.grid[r][c]
                if p and p.kind == "K" and p.color == color:
                    return (r, c)
        return None

    def deep_copy(self):
        b = Board.__new__(Board)
        b.grid = [[p.copy() if p else None for p in row] for row in self.grid]
        b.turn = self.turn
        b.en_passant_target = self.en_passant_target
        b.move_history = list(self.move_history)
        return b

    # ── Zuggenerierung ──────────────────────────────────────────────────────

    def pseudo_legal_moves(self, r, c, skip_castling=False):
        """Gibt alle Zielfelder zurück (ohne Schach-Prüfung)."""
        piece = self.grid[r][c]
        if not piece:
            return []
        moves = []
        color = piece.color
        enemy = BLACK if color == WHITE else WHITE

        if piece.kind == "P":
            direction = -1 if color == WHITE else 1
            start_row = 6 if color == WHITE else 1
            # Ein Feld vorwärts
            nr = r + direction
            if self.in_bounds(nr, c) and not self.grid[nr][c]:
                moves.append((nr, c))
                # Zwei Felder vom Start
                nr2 = r + 2 * direction
                if r == start_row and not self.grid[nr2][c]:
                    moves.append((nr2, c))
            # Schlagen diagonal
            for dc in [-1, 1]:
                nc = c + dc
                nr = r + direction
                if self.in_bounds(nr, nc):
                    target = self.grid[nr][nc]
                    if target and target.color == enemy:
                        moves.append((nr, nc))
                    # En Passant
                    if self.en_passant_target == (nr, nc):
                        moves.append((nr, nc))

        elif piece.kind == "N":
            for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),
                           (1,-2),(1,2),(2,-1),(2,1)]:
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    t = self.grid[nr][nc]
                    if not t or t.color == enemy:
                        moves.append((nr, nc))

        elif piece.kind == "K":
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if self.in_bounds(nr, nc):
                        t = self.grid[nr][nc]
                        if not t or t.color == enemy:
                            moves.append((nr, nc))
            # Rochade
            if not skip_castling and not piece.has_moved and not self.is_square_attacked(r, c, enemy):
                # Königsseite
                rook = self.grid[r][7]
                if (rook and rook.kind == "R" and not rook.has_moved
                        and not self.grid[r][5] and not self.grid[r][6]
                        and not self.is_square_attacked(r, 5, enemy)
                        and not self.is_square_attacked(r, 6, enemy)):
                    moves.append((r, 6))
                # Damenseite
                rook = self.grid[r][0]
                if (rook and rook.kind == "R" and not rook.has_moved
                        and not self.grid[r][1] and not self.grid[r][2]
                        and not self.grid[r][3]
                        and not self.is_square_attacked(r, 2, enemy)
                        and not self.is_square_attacked(r, 3, enemy)):
                    moves.append((r, 2))

        else:
            # Läufer, Turm, Dame – Gleitsätze
            directions = []
            if piece.kind in ("B", "Q"):
                directions += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if piece.kind in ("R", "Q"):
                directions += [(-1,0),(1,0),(0,-1),(0,1)]
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                while self.in_bounds(nr, nc):
                    t = self.grid[nr][nc]
                    if not t:
                        moves.append((nr, nc))
                    elif t.color == enemy:
                        moves.append((nr, nc))
                        break
                    else:
                        break
                    nr += dr
                    nc += dc

        return moves

    def legal_moves(self, r, c):
        """Nur Züge, die den eigenen König nicht im Schach lassen."""
        piece = self.grid[r][c]
        if not piece:
            return []
        result = []
        for mr, mc in self.pseudo_legal_moves(r, c):
            test = self.deep_copy()
            test._raw_move(r, c, mr, mc)
            if not test.is_in_check(piece.color):
                result.append((mr, mc))
        return result

    # ── Schach-Erkennung ────────────────────────────────────────────────────

    def is_square_attacked(self, r, c, by_color):
        """Prüft, ob ein Feld von einer bestimmten Farbe angegriffen wird."""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                p = self.grid[row][col]
                if p and p.color == by_color:
                    if (r, c) in self.pseudo_legal_moves(row, col, skip_castling=True):
                        return True
        return False

    def is_in_check(self, color):
        king_pos = self.find_king(color)
        if not king_pos:
            return False
        enemy = BLACK if color == WHITE else WHITE
        return self.is_square_attacked(king_pos[0], king_pos[1], enemy)

    def has_any_legal_move(self, color):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = self.grid[r][c]
                if p and p.color == color and self.legal_moves(r, c):
                    return True
        return False

    # ── Zug ausführen ───────────────────────────────────────────────────────

    def _raw_move(self, r1, c1, r2, c2):
        """Bewegt eine Figur ohne Regelprüfung (für Simulationen)."""
        piece = self.grid[r1][c1]
        captured = self.grid[r2][c2]

        # En Passant Schlag
        if piece.kind == "P" and (r2, c2) == self.en_passant_target:
            self.grid[r1][c2] = None

        # Rochade – Turm mitbewegen
        if piece.kind == "K" and abs(c2 - c1) == 2:
            if c2 == 6:  # Königsseite
                self.grid[r1][5] = self.grid[r1][7]
                self.grid[r1][7] = None
                if self.grid[r1][5]:
                    self.grid[r1][5].has_moved = True
            elif c2 == 2:  # Damenseite
                self.grid[r1][3] = self.grid[r1][0]
                self.grid[r1][0] = None
                if self.grid[r1][3]:
                    self.grid[r1][3].has_moved = True

        self.grid[r2][c2] = piece
        self.grid[r1][c1] = None
        piece.has_moved = True
        return captured

    def make_move(self, r1, c1, r2, c2, promotion_kind=None):
        """Führt einen legalen Zug aus und wechselt den Spieler."""
        piece = self.grid[r1][c1]
        self._raw_move(r1, c1, r2, c2)

        # En-Passant-Ziel setzen
        if piece.kind == "P" and abs(r2 - r1) == 2:
            self.en_passant_target = ((r1 + r2) // 2, c1)
        else:
            self.en_passant_target = None

        # Bauernumwandlung
        if piece.kind == "P" and (r2 == 0 or r2 == 7):
            kind = promotion_kind if promotion_kind else "Q"
            self.grid[r2][c2] = Piece(kind, piece.color)
            self.grid[r2][c2].has_moved = True

        self.move_history.append((r1, c1, r2, c2))
        self.turn = BLACK if self.turn == WHITE else WHITE


# ── GUI ─────────────────────────────────────────────────────────────────────

class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Schach")
        self.root.resizable(False, False)
        self.board = Board()
        self.selected = None       # (row, col) der gewählten Figur
        self.legal_targets = []    # Legale Zielfelder
        self.pending_promotion = None  # (r1,c1,r2,c2) während Auswahl

        canvas_size = BOARD_SIZE * SQUARE_SIZE
        # Info-Label
        self.info_var = tk.StringVar(value="Weiß ist am Zug")
        self.info_label = tk.Label(root, textvariable=self.info_var,
                                   font=("Arial", 14, "bold"), pady=6)
        self.info_label.pack()

        self.canvas = tk.Canvas(root, width=canvas_size, height=canvas_size)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self.draw_board()

    # ── Zeichnen ────────────────────────────────────────────────────────────

    def draw_board(self):
        self.canvas.delete("all")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x1 = c * SQUARE_SIZE
                y1 = r * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                # Feldfarbe
                if self.selected == (r, c):
                    color = COLOR_SELECTED
                elif (r, c) in self.legal_targets:
                    color = COLOR_MOVE
                elif (r + c) % 2 == 0:
                    color = COLOR_LIGHT
                else:
                    color = COLOR_DARK

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color,
                                             outline="")

                piece = self.board.grid[r][c]
                if piece:
                    self.canvas.create_text(
                        x1 + SQUARE_SIZE // 2, y1 + SQUARE_SIZE // 2,
                        text=piece.symbol(), font=("Arial", 40), anchor="center"
                    )

        # Schach-Anzeige
        if self.board.is_in_check(self.board.turn):
            king_pos = self.board.find_king(self.board.turn)
            if king_pos:
                kr, kc = king_pos
                x1 = kc * SQUARE_SIZE
                y1 = kr * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             outline="red", width=4)

    # ── Klick-Handling ──────────────────────────────────────────────────────

    def on_click(self, event):
        if self.pending_promotion:
            return

        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        if not self.board.in_bounds(row, col):
            return

        # Bereits eine Figur ausgewählt?
        if self.selected:
            sr, sc = self.selected
            if (row, col) in self.legal_targets:
                piece = self.board.grid[sr][sc]
                # Bauernumwandlung nötig?
                if (piece.kind == "P"
                        and (row == 0 or row == 7)):
                    self.pending_promotion = (sr, sc, row, col)
                    self.show_promotion_dialog(piece.color)
                    return
                self.board.make_move(sr, sc, row, col)
                self.selected = None
                self.legal_targets = []
                self.after_move()
                return
            # Andere eigene Figur auswählen
            self.selected = None
            self.legal_targets = []

        clicked = self.board.grid[row][col]
        if clicked and clicked.color == self.board.turn:
            moves = self.board.legal_moves(row, col)
            if moves:
                self.selected = (row, col)
                self.legal_targets = moves

        self.draw_board()

    # ── Bauernumwandlung ────────────────────────────────────────────────────

    def show_promotion_dialog(self, color):
        dialog = tk.Toplevel(self.root)
        dialog.title("Umwandlung")
        dialog.resizable(False, False)
        dialog.grab_set()
        tk.Label(dialog, text="Figur wählen:", font=("Arial", 12)).pack(pady=5)
        frame = tk.Frame(dialog)
        frame.pack(pady=5)
        for kind in ["Q", "R", "B", "N"]:
            sym = PIECE_SYMBOLS[(kind, color)]
            btn = tk.Button(frame, text=sym, font=("Arial", 30), width=2,
                            command=lambda k=kind, d=dialog: self.do_promotion(k, d))
            btn.pack(side="left", padx=4)

    def do_promotion(self, kind, dialog):
        dialog.destroy()
        r1, c1, r2, c2 = self.pending_promotion
        self.board.make_move(r1, c1, r2, c2, promotion_kind=kind)
        self.pending_promotion = None
        self.selected = None
        self.legal_targets = []
        self.after_move()

    # ── Nach einem Zug ──────────────────────────────────────────────────────

    def after_move(self):
        self.draw_board()
        turn = self.board.turn
        name = "Weiß" if turn == WHITE else "Schwarz"

        if not self.board.has_any_legal_move(turn):
            if self.board.is_in_check(turn):
                winner = "Schwarz" if turn == WHITE else "Weiß"
                self.info_var.set(f"Schachmatt! {winner} gewinnt!")
                messagebox.showinfo("Schachmatt",
                                    f"{winner} gewinnt durch Schachmatt!")
            else:
                self.info_var.set("Patt – Unentschieden!")
                messagebox.showinfo("Patt", "Das Spiel endet unentschieden.")
            return

        check_str = " (Schach!)" if self.board.is_in_check(turn) else ""
        self.info_var.set(f"{name} ist am Zug{check_str}")


# ── Start ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    ChessGUI(root)
    root.mainloop()
