# renderer.py
import displayio
import bitmaptools
import terminalio
from adafruit_display_text import label #type: ignore
from pieces import COLORS, PIECES

CELL      = 16          #px per cell
GRID_W    = 10
GRID_H    = 20
SIDEBAR_X = GRID_W * CELL   #sidebar starts here
PREV_CELL = 8               #px per cell in the next piece preview

_GHOST_COLOR = 0x222222     #dark grey for ghost piece
_N_COLORS    = 9            #0-7 for COLORS, 8 for ghost



class Renderer:
    
    

    def __init__(self, display):
        self._display = display
        self._group   = displayio.Group()

        #shared palette for grid and preview
        self._palette = displayio.Palette(_N_COLORS)
        for i, c in enumerate(COLORS):   #index 0-7
            self._palette[i] = c
        self._palette[8] = _GHOST_COLOR
        #grid bitmap where each cell is CELL x CELL pxs
        self._bitmap = displayio.Bitmap(GRID_W * CELL, GRID_H * CELL, _N_COLORS)
        self._group.append(
            displayio.TileGrid(self._bitmap, pixel_shader=self._palette, x=0, y=0)
        )

        #side bar labels
        self._score_lbl = self._make_label("SCORE", SIDEBAR_X + 4,  88, 0xFFFFFF)
        self._score_val = self._make_label("0",     SIDEBAR_X + 4, 100, 0xFFFF00)
        self._level_lbl = self._make_label("LEVEL", SIDEBAR_X + 4, 118, 0xFFFFFF)
        self._level_val = self._make_label("1",     SIDEBAR_X + 4, 130, 0xFFFF00)
        self._lines_lbl = self._make_label("LINES", SIDEBAR_X + 4, 148, 0xFFFFFF)
        self._lines_val = self._make_label("0",     SIDEBAR_X + 4, 160, 0xFFFF00)
        self._next_lbl  = self._make_label("NEXT",  SIDEBAR_X + 4, 178, 0xFFFFFF)

        for lbl in (self._score_lbl, self._score_val,
                    self._level_lbl, self._level_val,
                    self._lines_lbl, self._lines_val,
                    self._next_lbl):
            self._group.append(lbl)

        #next piece preview bitmap,  4x4 cells at PREV_CELL px each
        self._next_bitmap = displayio.Bitmap(4 * PREV_CELL, 4 * PREV_CELL, _N_COLORS)
        self._group.append(
            displayio.TileGrid(self._next_bitmap, pixel_shader=self._palette,
                            x=SIDEBAR_X + 4, y=192)
        )

        #grid lines
        grid_pal = displayio.Palette(2)
        grid_pal[0] = 0x000000
        grid_pal[1] = 0x111111  #very subtle, bump to 0x222222 if too faint
        grid_pal.make_transparent(0)  # so game bitmap shows through

        grid_bmp = displayio.Bitmap(GRID_W * CELL, GRID_H * CELL, 2)

        # horizontal lines
        for row in range(GRID_H):
            for x in range(GRID_W * CELL):
                grid_bmp[x, row * CELL] = 1

        # vertical lines
        for col in range(GRID_W):
            for y in range(GRID_H * CELL):
                grid_bmp[col * CELL, y] = 1

        self._group.append(
            displayio.TileGrid(grid_bmp, pixel_shader=grid_pal, x=0, y=0)
        )

        #divider line between grid and sidebar
        div_pal = displayio.Palette(2)
        div_pal[0] = 0x000000
        div_pal[1] = 0x333333

        div_bmp = displayio.Bitmap(1, GRID_H * CELL, 2)
        for y in range(GRID_H * CELL):
            div_bmp[0, y] = 1

        self._group.append(
            displayio.TileGrid(div_bmp, pixel_shader=div_pal, x=SIDEBAR_X, y=0)
        )

        display.root_group = self._group

        #dirty tracking state
        self._prev_grid        = bytearray(GRID_W * GRID_H)
        self._prev_piece_cells = []
        self._prev_ghost_cells = []
        self._prev_score       = -1
        self._prev_level       = -1
        self._prev_lines       = -1
        self._prev_next        = -1
   

    def draw(self, game):
        if not game.dirty:
            return
        self._draw_grid(game)
        self._draw_piece(game)
        self._draw_sidebar(game)
        game.dirty = False
        
    #switch from menu to game
    def activate(self):
        self._display.root_group = self._group

    #actual grid
    
    def _draw_grid(self, game):
        if game.lines_cleared:
            for i in range(GRID_W * GRID_H):
                self._prev_grid[i] = 0xFF
            game.lines_cleared = False
        
        for i in range(GRID_W * GRID_H):
            val = game.grid[i]
            if val != self._prev_grid[i]:
                row, col = divmod(i, GRID_W)
                self._fill(self._bitmap, col * CELL, row * CELL, CELL, val)
                self._prev_grid[i] = val

    
    #active piece + ghost

    def _draw_piece(self, game):
        piece_cells = list(game.current_cells())   
        ghost_row   = game.ghost_row()

        #ghost cells from piece offsets relative to anchor
        ghost_cells = [
            (ghost_row + (r - game._py), c)
            for r, c in piece_cells
        ]

        color_idx  = game._piece + 1
        active_set = piece_cells   
        ghost_set  = ghost_cells

        #erase previous ghost cells no longer needed
        for r, c in self._prev_ghost_cells:
            if (r, c) not in ghost_set and (r, c) not in active_set:
                self._restore(game, r, c)

        #erase previous piece cells no longer needed
        for r, c in self._prev_piece_cells:
            if (r, c) not in active_set:
                if (r, c) in ghost_set:
                    self._fill(self._bitmap, c * CELL, r * CELL, CELL, 8)
                else:
                    self._restore(game, r, c)

        #draw ghost (skip cells occupied by active piece)
        for r, c in ghost_cells:
            if (r, c) not in active_set and self._in_grid(r, c):
                self._fill(self._bitmap, c * CELL, r * CELL, CELL, 8)

        #draw active piece on top
        for r, c in piece_cells:
            if self._in_grid(r, c):
                self._fill(self._bitmap, c * CELL, r * CELL, CELL, color_idx)

        self._prev_piece_cells = piece_cells
        self._prev_ghost_cells = ghost_cells

    #sidebar

    def _draw_sidebar(self, game):
        if game.score != self._prev_score:
            self._score_val.text = str(game.score)
            self._prev_score = game.score

        if game.level != self._prev_level:
            self._level_val.text = str(game.level)
            self._prev_level = game.level

        if game.lines != self._prev_lines:
            self._lines_val.text = str(game.lines)
            self._prev_lines = game.lines

        if game.next_piece != self._prev_next:
            self._draw_next(game.next_piece)
            self._prev_next = game.next_piece

    def _draw_next(self, piece_idx):
        pc = PREV_CELL
        bitmaptools.fill_region(self._next_bitmap, 0, 0, 4 * pc, 4 * pc, 0)
        color_idx = piece_idx + 1
        for dr, dc in PIECES[piece_idx][0]:
            bitmaptools.fill_region(self._next_bitmap,
                                    dc * pc, dr * pc,
                                    dc * pc + pc, dr * pc + pc,
                                    color_idx)

    #helpers
    
    

    def _make_label(self, text, x, y, color):
        return label.Label(terminalio.FONT, text=text, color=color, x=x, y=y)

    def _fill(self, bitmap, bx, by, size, color_idx):
        bitmaptools.fill_region(bitmap, bx, by, bx + size, by + size, color_idx)

    def _restore(self, game, row, col):
        if self._in_grid(row, col):
            val = game.grid[row * GRID_W + col]
            self._fill(self._bitmap, col * CELL, row * CELL, CELL, val)

    @staticmethod
    def _in_grid(row, col):
        return 0 <= row < GRID_H and 0 <= col < GRID_W
    
