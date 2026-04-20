"""
main.py — Графический интерфейс игры Бантуми
Автор: Старостин Максим (frontend, Python/Tkinter)

Требования:
    pip install requests
    Java-бэкенд должен быть запущен на http://localhost:8080
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests

# ── Настройки подключения к бэкенду ──────────────────────────────────────────
BASE_URL = "http://localhost:8080/api/v1/game"

# ── Цветовая палитра (деревянная тема) ───────────────────────────────────────
BG          = "#1a0f02"
BOARD_BG    = "#5d3a1a"
BOARD_EDGE  = "#c8874a"
PIT_FILL    = "#3b2208"
PIT_HOVER   = "#5a3510"
PIT_ACTIVE  = "#7a4820"
KALAH_FILL  = "#2a1805"
TEXT_LIGHT  = "#f5e6c8"
TEXT_DIM    = "#906040"
P1_COLOR    = "#e74c3c"
P2_COLOR    = "#3498db"
GOLD        = "#f0c040"


class BantumiApp:
    """Главное окно приложения."""

    # Размеры доски
    CW, CH   = 740, 300   # ширина и высота Canvas
    PIT_R    = 32          # радиус лунки
    KALAH_W  = 55          # полуширина Калаха
    KALAH_H  = 105         # полувысота Калаха
    ROW_Y1   = 95          # центр верхнего ряда (П2)
    ROW_Y2   = 205         # центр нижнего ряда (П1)
    MID_Y    = 150         # вертикальный центр доски
    KALAH1_X = 680         # центр Калаха П1 (справа)
    KALAH2_X = 60          # центр Калаха П2 (слева)

    # Центры лунок: П1 слева-направо (индексы 0-5), П2 справа-налево (индексы 12-7)
    PIT_XS = [150, 245, 340, 400+35, 495, 590]

    def __init__(self):
        self.state       = None    # последнее состояние от бэкенда
        self.stones_var  = tk.IntVar(value=4)
        self.pit_items   = {}      # canvas_item_id → pit_index

        self._build_window()
        self._fetch_state()

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Бантуми (Kalah)")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Заголовок
        tk.Label(self.root, text="БАНТУМИ", bg=BG, fg=BOARD_EDGE,
                 font=("Arial", 26, "bold")).pack(pady=(16, 2))
        tk.Label(self.root, text="Классическая игра Kalah · 2 игрока",
                 bg=BG, fg=TEXT_DIM, font=("Arial", 10)).pack()

        # Панель настроек
        cfg = tk.Frame(self.root, bg=BG)
        cfg.pack(pady=8)
        tk.Label(cfg, text="Камней в лунке:", bg=BG, fg=TEXT_DIM,
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=4)
        for v in (3, 4, 5, 6):
            tk.Radiobutton(cfg, text=str(v), variable=self.stones_var, value=v,
                           bg=BG, fg=TEXT_LIGHT, selectcolor=BOARD_BG,
                           activebackground=BG, command=self._new_game
                           ).pack(side=tk.LEFT, padx=3)

        # Статусная строка
        self.status_var = tk.StringVar(value="Ход: Игрок 1")
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var,
                                   bg=BG, fg=P1_COLOR,
                                   font=("Arial", 13, "bold"))
        self.status_lbl.pack(pady=4)

        # Canvas с игровой доской
        self.canvas = tk.Canvas(self.root, width=self.CW, height=self.CH,
                                bg=BG, highlightthickness=0)
        self.canvas.pack(padx=20)

        # Привязка hover-эффекта
        self.canvas.bind("<Motion>",    self._on_hover)
        self.canvas.bind("<Leave>",     self._on_leave)

        # Панель счёта
        score_frame = tk.Frame(self.root, bg=BG)
        score_frame.pack(pady=8)
        tk.Label(score_frame, text="Игрок 1:", bg=BG, fg=TEXT_DIM,
                 font=("Arial", 11)).grid(row=0, column=0, padx=10)
        self.score1_var = tk.StringVar(value="0")
        tk.Label(score_frame, textvariable=self.score1_var, bg=BG, fg=P1_COLOR,
                 font=("Arial", 18, "bold")).grid(row=0, column=1, padx=5)
        tk.Label(score_frame, text="Игрок 2:", bg=BG, fg=TEXT_DIM,
                 font=("Arial", 11)).grid(row=0, column=2, padx=10)
        self.score2_var = tk.StringVar(value="0")
        tk.Label(score_frame, textvariable=self.score2_var, bg=BG, fg=P2_COLOR,
                 font=("Arial", 18, "bold")).grid(row=0, column=3, padx=5)

        # Кнопки управления
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=6)
        self._btn(btn_frame, "Новая игра",    self._new_game).pack(side=tk.LEFT, padx=6)
        self.undo_btn = self._btn(btn_frame, "Отменить ход", self._undo)
        self.undo_btn.pack(side=tk.LEFT, padx=6)

        # Журнал ходов
        log_frame = tk.Frame(self.root, bg=BG)
        log_frame.pack(pady=(4, 16), padx=20, fill=tk.X)
        tk.Label(log_frame, text="ЖУРНАЛ ХОДОВ", bg=BG, fg=TEXT_DIM,
                 font=("Arial", 8)).pack(anchor=tk.W)
        self.log_box = tk.Listbox(log_frame, height=5, bg="#110900", fg=TEXT_DIM,
                                  font=("Courier", 9), selectbackground=BOARD_BG,
                                  borderwidth=0, highlightthickness=1,
                                  highlightcolor=BOARD_BG)
        self.log_box.pack(fill=tk.X)

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=BOARD_BG, fg=TEXT_LIGHT,
                         activebackground=PIT_ACTIVE,
                         font=("Arial", 10, "bold"),
                         relief=tk.FLAT, padx=14, pady=6, cursor="hand2")

    # ── Отрисовка доски ───────────────────────────────────────────────────────

    def _draw_board(self):
        """Полная перерисовка игрового поля по текущему state."""
        self.canvas.delete("all")
        self.pit_items.clear()
        if not self.state:
            return

        board  = self.state["board"]
        player = self.state["currentPlayer"]
        landed = self.state.get("lastLandedPit")

        # Фон доски
        self.canvas.create_rectangle(10, 10, self.CW - 10, self.CH - 10,
                                     fill=BOARD_BG, outline=BOARD_EDGE,
                                     width=3)

        # ── Кalах Игрока 2 (слева) ──
        self._draw_kalah(self.KALAH2_X, self.MID_Y, board[13], 2)

        # ── Кalах Игрока 1 (справа) ──
        self._draw_kalah(self.KALAH1_X, self.MID_Y, board[6], 1)

        # ── Лунки Игрока 2 (верхний ряд, индексы 12→7, отображаются слева направо) ──
        for col, pit_idx in enumerate([12, 11, 10, 9, 8, 7]):
            cx = self.PIT_XS[col]
            cy = self.ROW_Y1
            clickable = (player == 2 and board[pit_idx] > 0
                         and not self.state["gameOver"])
            self._draw_pit(cx, cy, board[pit_idx], pit_idx,
                           clickable, pit_idx == landed)

        # ── Лунки Игрока 1 (нижний ряд, индексы 0→5) ──
        for col, pit_idx in enumerate([0, 1, 2, 3, 4, 5]):
            cx = self.PIT_XS[col]
            cy = self.ROW_Y2
            clickable = (player == 1 and board[pit_idx] > 0
                         and not self.state["gameOver"])
            self._draw_pit(cx, cy, board[pit_idx], pit_idx,
                           clickable, pit_idx == landed)

        # Метки строк
        self.canvas.create_text(self.KALAH2_X, self.ROW_Y1,
                                 text="П2", fill=P2_COLOR,
                                 font=("Arial", 8, "bold"))
        self.canvas.create_text(self.KALAH2_X, self.ROW_Y2,
                                 text="П1", fill=P1_COLOR,
                                 font=("Arial", 8, "bold"))

    def _draw_pit(self, cx, cy, count, pit_idx, clickable, highlighted):
        """Нарисовать одну лунку."""
        r = self.PIT_R
        fill = PIT_ACTIVE if clickable else PIT_FILL
        if highlighted:
            fill = "#8a5828"

        item = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill=fill, outline=BOARD_EDGE, width=1)
        # Число камней
        color = TEXT_LIGHT if count > 0 else TEXT_DIM
        self.canvas.create_text(cx, cy - 8, text=str(count),
                                 fill=color, font=("Arial", 14, "bold"))
        # Маленькие точки (до 6 камней)
        if 0 < count <= 6:
            for i in range(count):
                dx = (i % 3 - 1) * 9
                dy = 10 + (i // 3) * 8
                self.canvas.create_oval(cx + dx - 3, cy + dy - 3,
                                        cx + dx + 3, cy + dy + 3,
                                        fill="#d4b87a", outline="")

        if clickable:
            self.pit_items[item] = pit_idx
            self.canvas.tag_bind(item, "<Button-1>",
                                 lambda e, p=pit_idx: self._on_pit_click(p))
            self.canvas.tag_bind(item, "<Enter>",
                                 lambda e, i=item: self.canvas.itemconfig(i, fill=PIT_HOVER))
            self.canvas.tag_bind(item, "<Leave>",
                                 lambda e, i=item, f=fill: self.canvas.itemconfig(i, fill=f))

    def _draw_kalah(self, cx, cy, count, player):
        """Нарисовать Калах (хранилище)."""
        w, h = self.KALAH_W, self.KALAH_H
        color = P1_COLOR if player == 1 else P2_COLOR
        self.canvas.create_oval(cx - w, cy - h, cx + w, cy + h,
                                 fill=KALAH_FILL, outline=BOARD_EDGE, width=2)
        label = "Игрок 1" if player == 1 else "Игрок 2"
        self.canvas.create_text(cx, cy - 30, text=label,
                                 fill=TEXT_DIM, font=("Arial", 8))
        self.canvas.create_text(cx, cy + 5, text=str(count),
                                 fill=color, font=("Arial", 22, "bold"))

        # Индикатор активного хода
        if self.state and self.state["currentPlayer"] == player and not self.state["gameOver"]:
            self.canvas.create_oval(cx - 5, cy + 45, cx + 5, cy + 55,
                                    fill=color, outline="")

    
    # ── Обновление UI ───────────────────────────────────────────────────────── 

    def _update_ui(self, log_text=None):
        """Перерисовать всё после изменения state."""
        self._draw_board()
        board  = self.state["board"]
        player = self.state["currentPlayer"]

        self.score1_var.set(str(board[6]))
        self.score2_var.set(str(board[13]))

        if self.state["gameOver"]:
            w = self.state.get("winner")
            if w == 0:
                msg = "Ничья!"
            else:
                msg = f"Игрок {w} победил!"
            self.status_var.set(msg)
            self.status_lbl.configure(fg=GOLD)
            self._show_result(w, board)
        else:
            self.status_var.set(f"Ход: Игрок {player}")
            self.status_lbl.configure(fg=P1_COLOR if player == 1 else P2_COLOR)

        # Кнопка Undo
        self.undo_btn.configure(state=tk.NORMAL if self.state["moveCount"] > 0
                                                    and not self.state["gameOver"]
                                else tk.DISABLED)

        if log_text:
            self.log_box.insert(0, log_text)

    def _show_result(self, winner, board):
        """Показать диалог с результатом."""
        if winner == 0:
            msg = "Ничья! Оба игрока набрали поровну."
        else:
            msg = f"Игрок {winner} победил!"
        detail = f"Счёт:  Игрок 1 — {board[6]},  Игрок 2 — {board[13]}"
        ans = messagebox.askquestion("Игра окончена",
                                     f"{msg}\n{detail}\n\nСыграть ещё раз?",
                                     icon="info")
        if ans == "yes":
            self._new_game()

    # ── Hover ─────────────────────────────────────────────────────────────────

    def _on_hover(self, event):
        pass  # hover реализован через tag_bind на каждой лунке

    def _on_leave(self, event):
        pass

    # ── Обработчики событий ───────────────────────────────────────────────────

    def _on_pit_click(self, pit_idx):
        """Клик по лунке → POST /move/{pit}."""
        try:
            resp = requests.post(f"{BASE_URL}/move/{pit_idx}", timeout=3)
            data = resp.json()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось связаться с бэкендом:\n{e}")
            return

        if not data.get("valid", True):
            return  # невалидный ход — игнорируем

        self.state = data["state"]

        # Формируем запись для журнала
        pit_num = pit_idx + 1 if pit_idx <= 5 else pit_idx - 6
        move_no = self.state["moveCount"]
        # Определяем кто только что ходил
        if data.get("bonusTurn"):
            who = self.state["currentPlayer"]
        else:
            who = 2 if self.state["currentPlayer"] == 1 else 1
        log = f"#{move_no}  Игрок {who}: лунка {pit_num}"
        if data.get("bonusTurn"):  log += " — бонусный ход!"
        if data.get("captured"):   log += " — захват!"

        self._update_ui(log_text=log)

    def _new_game(self):
        """Начать новую партию."""
        stones = self.stones_var.get()
        try:
            resp = requests.post(f"{BASE_URL}/new", params={"stones": stones}, timeout=3)
            self.state = resp.json()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось связаться с бэкендом:\n{e}")
            return
        self.log_box.delete(0, tk.END)
        self._update_ui()

    def _undo(self):
        """Отменить последний ход."""
        try:
            resp = requests.post(f"{BASE_URL}/undo", timeout=3)
            self.state = resp.json()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось связаться с бэкендом:\n{e}")
            return
        if self.log_box.size() > 0:
            self.log_box.delete(0)
        self._update_ui()

    def _fetch_state(self):
        """Получить начальное состояние при запуске."""
        try:
            resp = requests.get(f"{BASE_URL}/state", timeout=3)
            self.state = resp.json()
            self._update_ui()
        except Exception:
            messagebox.showerror(
                "Бэкенд недоступен",
                "Запустите Java-сервер перед запуском клиента:\n\n"
                "cd backend\nmvn spring-boot:run"
            )

    def run(self):
        self.root.mainloop()


# ── Точка входа ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = BantumiApp()
    app.run()
