# game.py
import random
from adafruit_ticks import ticks_ms, ticks_diff
from pieces import PIECES

GRID_W = 10
GRID_H = 20
_SCORE_TABLE = (0, 100, 300, 500, 800)  #points for 0-4 line clears

class Game:

    def __init__(self):
        self.grid = bytearray(GRID_W * GRID_H)  # 0=empty, 1-7=piece color index
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.dirty = True  # tells renderer a full redraw is needed
        self.lines_cleared = False
        self._piece = 0    # current piece index (0-6)
        self._rot   = 0    # current rotation (0-3)
        self._px    = 3    # anchor col
        self._py    = 0    # anchor row
        self.next_piece = 0  # exposed so renderer can draw the preview
        
        self._das_timer  = 0
        self._das_delay  = 200   # ms before repeat starts
        self._das_speed  = 50    # ms between repeats once held
        self._das_dir    = 0     # -1 left, 1 right, 0 none

        self._gravity_ms = 800
        self._last_tick  = ticks_ms()
        
    

        # reusable 4-cell buffer to avoids allocating a list every frame
        self._cell_buf = [(0, 0), (0, 0), (0, 0), (0, 0)]

        # Previous button states for edge detection
        self._prev = {'left': False, 'right': False,
                      'rotate': False, 'down': False, 'drop': False}

   

    def reset(self):
        for i in range(GRID_W * GRID_H):
            self.grid[i] = 0
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over  = False
        self._gravity_ms = 800
        self.next_piece = random.randint(0, 6)
        for k in self._prev:         
            self._prev[k] = True
        self._spawn()
        self.dirty = True

    def update(self, buttons):
        #Call once per main loop frame 
        if self.over:
            return

        #edge detection help
        def pressed(key):
            return buttons[key] and not self._prev[key]

        
        now = ticks_ms()
        if buttons['left'] and not buttons['right']:
            if self._das_dir != -1:
                self._das_dir   = -1
                self._das_timer = now
                if not self._collides(self._py, self._px - 1, self._rot):
                    self._px -= 1
                    self.dirty = True
            else:
                delay = self._das_delay if ticks_diff(now, self._das_timer) < self._das_delay else self._das_speed
                if ticks_diff(now, self._das_timer) >= delay:
                    self._das_timer = now
                    if not self._collides(self._py, self._px - 1, self._rot):
                        self._px -= 1
                        self.dirty = True

        elif buttons['right'] and not buttons['left']:
            if self._das_dir != 1:
                self._das_dir   = 1
                self._das_timer = now
                if not self._collides(self._py, self._px + 1, self._rot):
                    self._px += 1
                    self.dirty = True
            else:
                delay = self._das_delay if ticks_diff(now, self._das_timer) < self._das_delay else self._das_speed
                if ticks_diff(now, self._das_timer) >= delay:
                    self._das_timer = now
                    if not self._collides(self._py, self._px + 1, self._rot):
                        self._px += 1
                        self.dirty = True

        else:
            self._das_dir = 0

        #rotation
        if pressed('rotate'):
            new_rot = (self._rot + 1) % 4
            #wall kick
            for nudge in (0, 1, -1):
                if not self._collides(self._py, self._px + nudge, new_rot):
                    self._rot = new_rot
                    self._px += nudge
                    self.dirty = True
                    break

        #soft dorp
        if pressed('down'):
            if not self._collides(self._py + 1, self._px, self._rot):
                self._py += 1
                self.score += 1
                self.dirty = True

        #hard drop
        if pressed('drop'):
            while not self._collides(self._py + 1, self._px, self._rot):
                self._py += 1
                self.score += 2
            self._lock()
            self._last_tick = ticks_ms()
            self._update_prev(buttons)
            return

        #gravity
        now = ticks_ms()
        if ticks_diff(now, self._last_tick) >= self._gravity_ms:
            self._last_tick = now
            if not self._collides(self._py + 1, self._px, self._rot):
                self._py += 1
                self.dirty = True
            else:
                self._lock()

        self._update_prev(buttons)

    def current_cells(self):
        #Returns the 4 (row, col) positions of the active piece. Uses internal buffer.
        self._fill_cells(self._py, self._px, self._rot)
        return self._cell_buf

    def ghost_row(self):
        #Row where the current piece would land (for ghost piece rendering).
        gy = self._py
        while not self._collides(gy + 1, self._px, self._rot):
            gy += 1
        return gy

  

    def _fill_cells(self, row, col, rot):
        offsets = PIECES[self._piece][rot]
        for i in range(4):
            self._cell_buf[i] = (row + offsets[i][0], col + offsets[i][1])

    def _collides(self, row, col, rot):
        offsets = PIECES[self._piece][rot]
        for dr, dc in offsets:
            r, c = row + dr, col + dc
            if r < 0 or r >= GRID_H or c < 0 or c >= GRID_W:
                return True
            if self.grid[r * GRID_W + c]:
                return True
        return False

    def _lock(self):
        color = self._piece + 1  # 1-7
        self._fill_cells(self._py, self._px, self._rot)
        for r, c in self._cell_buf:
            if 0 <= r < GRID_H and 0 <= c < GRID_W:
                self.grid[r * GRID_W + c] = color
        self._clear_lines()
        self._spawn()
        self.dirty = True

    def _clear_lines(self):
        cleared = 0
        r = GRID_H - 1
        while r >= 0:
            full = True
            for c in range(GRID_W):
                if not self.grid[r * GRID_W + c]:
                    full = False
                    break
            if full:
                # shift all rows above down by one
                for rr in range(r, 0, -1):
                    for c in range(GRID_W):
                        self.grid[rr * GRID_W + c] = self.grid[(rr - 1) * GRID_W + c]
                for c in range(GRID_W):
                    self.grid[c] = 0
                cleared += 1
            else:
                r -= 1

        if cleared:
            self.lines_cleared = True
            self.lines += cleared
            self.score += _SCORE_TABLE[min(cleared, 4)] * self.level
            self.level  = self.lines // 10 + 1
            self._gravity_ms = max(100, 800 - (self.level - 1) * 70)

    def _spawn(self):
        self._piece = self.next_piece
        self.next_piece = random.randint(0, 6)
        self._rot = 0
        self._px  = 3
        self._py  = 0
        if self._collides(self._py, self._px, self._rot):
            self.over = True

    def _update_prev(self, buttons):
        for k in self._prev:
            self._prev[k] = buttons[k]
