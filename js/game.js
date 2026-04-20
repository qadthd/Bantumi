/**
 * game.js — Игровая логика Бантуми (Kalah)
 * Автор: Хусейнов Амин (backend)
 * Review: Зубков В.
 *
 * Структура доски (14 ячеек):
 *   Индексы 0–5   — лунки Игрока 1
 *   Индекс  6     — Калах Игрока 1
 *   Индексы 7–12  — лунки Игрока 2
 *   Индекс  13    — Калах Игрока 2
 *
 * Визуальное расположение:
 *   [12][11][10][9][8][7]
 * [13]                    [6]
 *   [0] [1] [2][3][4][5]
 */

class BantumiGame {
  constructor(stonesPerPit = 4) {
    this.stonesPerPit = stonesPerPit;
    this.reset();
  }

  reset() {
    this.board = new Array(14).fill(this.stonesPerPit);
    this.board[6] = 0;
    this.board[13] = 0;
    this.currentPlayer = 1;
    this.gameOver = false;
    this.winner = null;
    this.lastLandedPit = null;
    this.capturedFrom = null;
    this.history = [];
  }

  // Индексы лунок (без Калаха) для заданного игрока
  getPits(player) {
    return player === 1 ? [0, 1, 2, 3, 4, 5] : [7, 8, 9, 10, 11, 12];
  }

  // Индекс Калаха игрока
  getKalah(player) {
    return player === 1 ? 6 : 13;
  }

  // Принадлежит ли лунка (без Калаха) игроку
  ownsPit(player, pit) {
    return player === 1 ? (pit >= 0 && pit <= 5) : (pit >= 7 && pit <= 12);
  }

  // Противоположная лунка: 0↔12, 1↔11, ..., 5↔7
  opposite(pit) {
    return 12 - pit;
  }

  // Выполнить ход
  makeMove(pitIndex) {
    if (this.gameOver) {
      return { valid: false, reason: 'Игра окончена' };
    }
    if (!this.ownsPit(this.currentPlayer, pitIndex)) {
      return { valid: false, reason: 'Это не ваша лунка' };
    }
    if (this.board[pitIndex] === 0) {
      return { valid: false, reason: 'Лунка пуста' };
    }

    // Сохраняем состояние для истории
    this.history.push({
      board: [...this.board],
      player: this.currentPlayer,
    });

    const opponentKalah = this.getKalah(this.currentPlayer === 1 ? 2 : 1);
    const myKalah = this.getKalah(this.currentPlayer);

    let stones = this.board[pitIndex];
    this.board[pitIndex] = 0;
    let current = pitIndex;
    this.capturedFrom = null;

    // Раскладываем камни по одному против часовой стрелки
    while (stones > 0) {
      current = (current + 1) % 14;
      if (current === opponentKalah) continue; // Пропускаем Калах противника
      this.board[current]++;
      stones--;
    }

    this.lastLandedPit = current;
    let bonusTurn = false;
    let captured = false;

    // Бонусный ход: последний камень упал в свой Калах
    if (current === myKalah) {
      bonusTurn = true;
    }
    // Захват: последний камень в пустую лунку своей стороны (и напротив есть камни)
    else if (this.ownsPit(this.currentPlayer, current) && this.board[current] === 1) {
      const opp = this.opposite(current);
      if (this.board[opp] > 0) {
        this.board[myKalah] += this.board[opp] + 1;
        this.capturedFrom = opp;
        this.board[opp] = 0;
        this.board[current] = 0;
        captured = true;
      }
    }

    // Проверка конца игры: у одного игрока кончились камни
    const p1Empty = this.getPits(1).every(i => this.board[i] === 0);
    const p2Empty = this.getPits(2).every(i => this.board[i] === 0);

    if (p1Empty || p2Empty) {
      // Оставшиеся камни каждый игрок забирает в свой Калах
      this.getPits(1).forEach(i => { this.board[6] += this.board[i]; this.board[i] = 0; });
      this.getPits(2).forEach(i => { this.board[13] += this.board[i]; this.board[i] = 0; });
      this.gameOver = true;
      if (this.board[6] > this.board[13])       this.winner = 1;
      else if (this.board[13] > this.board[6])  this.winner = 2;
      else                                       this.winner = 0; // Ничья
    } else if (!bonusTurn) {
      this.currentPlayer = this.currentPlayer === 1 ? 2 : 1;
    }

    return {
      valid: true,
      bonusTurn,
      captured,
      capturedFrom: this.capturedFrom,
      landedPit: current,
      gameOver: this.gameOver,
      winner: this.winner,
    };
  }

  // Список доступных ходов для игрока
  getAvailableMoves(player) {
    return this.getPits(player).filter(i => this.board[i] > 0);
  }

  // Глубокое копирование состояния (используется функцией Undo)
  clone() {
    const copy = new BantumiGame(this.stonesPerPit);
    copy.board = [...this.board];
    copy.currentPlayer = this.currentPlayer;
    copy.gameOver = this.gameOver;
    copy.winner = this.winner;
    return copy;
  }
}
