# menu.py
import displayio
import bitmaptools
import terminalio
import random
from pieces import COLORS, PIECES
from adafruit_display_text import label #type: ignore
from adafruit_ticks import ticks_ms, ticks_diff


_BS = 10



class Menu:

    def __init__(self, display):
        self._display = display
        self._group   = None
        self._blink_ms   = 600
        self._last_blink = ticks_ms()
        self._blink_on   = True
        self._screen     = None
        self._prompt_label = None
        self._blk_tile = None
        self._blk_y    = 0
        #buzzer select
        self.sound_on    = True
        self._prev_left  = False
        self._prev_right = False
        self._prev_other = False
        self._sound_lbl  = None
        self._on_lbl     = None
        self._off_lbl    = None
        
        self._blk_tiles   = []
        self._blk_data    = []
        self._blk_bitmaps = []
        self._last_fall   = ticks_ms()
        self._fall_ms     = 30

        self._on_lbl  = None
        self._off_lbl = None
        self._box_tile = None
        self._box_bmp  = None
        
    def show_title(self):
        if self._screen == 'title':
            return
        self._screen     = 'title'
        self._prev_left  = True
        self._prev_right = True
        self._prev_other = True
        self._group      = self._build_title()
        self._display.root_group = self._group

    def show_gameover(self, score, lines, level):
        self._screen     = 'gameover'
        self._prev_left  = True
        self._prev_right = True
        self._prev_other = True
        self._group      = self._build_gameover(score, lines, level)
        self._display.root_group = self._group

    def update(self, buttons):
        now = ticks_ms()
        if ticks_diff(now, self._last_blink) >= self._blink_ms:
            self._last_blink = now
            self._blink_on   = not self._blink_on
            if self._prompt_label:
                self._prompt_label.color = 0xFFFFFF if self._blink_on else 0x000000

        #falling blocks
        if self._blk_tiles:
            cols = 240 // (4 * _BS)
            for i, tile in enumerate(self._blk_tiles):
                self._blk_data[i][0] += self._blk_data[i][1]
                if self._blk_data[i][0] >= 320:
                    self._blk_data[i][0] = -(4 * _BS)
                    tile.x = random.randint(0, cols - 1) * (4 * _BS)
                tile.y = self._blk_data[i][0]

        #edge detect
        left  = buttons['left']  and not self._prev_left
        right = buttons['right'] and not self._prev_right
        other = buttons['drop'] and not self._prev_other

        #toggle sound
        if left and self.sound_on:
            self.sound_on = False
            self._update_sound_labels()
        elif right and not self.sound_on:
            self.sound_on = True
            self._update_sound_labels()

        #update prev
        self._prev_left  = buttons['left']
        self._prev_right = buttons['right']
        self._prev_other = buttons['drop']

        if other:
            return 'START'
        return None

    def _build_title(self):
        group = displayio.Group()
        self._prompt_label = None
        self._blk_tiles = []
        self._blk_data  = []

        NUM_BLOCKS = 6
        cols = 240 // (4 * _BS)

        for i in range(NUM_BLOCKS):
            rot   = random.randint(0, 3)
            piece = i % 7
            x     = random.randint(0, cols - 1) * (4 * _BS)
            y     = random.randint(-320, 0)
            pal   = displayio.Palette(2)
            pal[0] = 0x000000
            pal[1] = COLORS[piece + 1]
            bmp   = displayio.Bitmap(4 * _BS, 4 * _BS, 2)
            for dr, dc in PIECES[piece][rot]:
                bitmaptools.fill_region(bmp,
                                        dc * _BS, dr * _BS,
                                        dc * _BS + _BS, dr * _BS + _BS, 1)
            tile = displayio.TileGrid(bmp, pixel_shader=pal, x=x, y=y)
            group.append(tile)
            self._blk_tiles.append(tile)
            self._blk_data.append([y, 1])

        group.append(label.Label(terminalio.FONT, text="TETRIS",
                                color=COLORS[5], x=66, y=80, scale=3))
        group.append(label.Label(terminalio.FONT, text="By Andrew Nguyen",
                                color=0x888888, x=70, y=112, scale=1))

        instructions = (
            ("LEFT / RIGHT", "     move"),
            ("UP",           "   rotate"),
            ("DOWN",         "soft drop"),
            ("SELECT",       "hard drop"),
        )

        for idx, (btn, action) in enumerate(instructions):
            y = 150 + idx * 16
            group.append(label.Label(terminalio.FONT, text=btn,
                                    color=0x555555, x=30, y=y, scale=1))
            group.append(label.Label(terminalio.FONT, text=action,
                                    color=0x888888, x=145, y=y, scale=1))
        
        group.append(label.Label(terminalio.FONT, text="SOUND",
                         color=0x666666, x=30, y=220, scale=1))
        #sound bars
        self._off_lbl = label.Label(terminalio.FONT, text="OFF",
                                    color=0x666666, x=162, y=220, scale=1)
        self._on_lbl  = label.Label(terminalio.FONT, text="ON",
                                    color=0xFFFFFF, x=186, y=220, scale=1)
        group.append(self._off_lbl)
        group.append(self._on_lbl)
        
        #border bitmap that moves to selected option
        self._box_bmp = displayio.Bitmap(22, 12, 2)
        box_pal       = displayio.Palette(2)
        box_pal[0]    = 0x000000
        box_pal[1]    = 0xFFFFFF
        box_pal.make_transparent(0)
        for x in range(22):
            self._box_bmp[x, 0]  = 1
            self._box_bmp[x, 11] = 1
        for y in range(12):
            self._box_bmp[0, y]  = 1
            self._box_bmp[21, y] = 1
        self._box_tile = displayio.TileGrid(self._box_bmp, pixel_shader=box_pal,
                                            x=186, y=214)
        group.append(self._box_tile)

        self._update_sound_labels()
        
        prompt = label.Label(terminalio.FONT, text="- PRESS ANY BUTTON -",
            color=0xFFFFFF, x=60, y=246, scale=1)
        
        group.append(prompt)
        self._prompt_label = prompt
        
        return group

    def _build_gameover(self, score, lines, level):
        group = displayio.Group()
        self._prompt_label = None

        group.append(label.Label(terminalio.FONT, text="GAME", color=0xFF0000,
                                 x=84, y=70, scale=3))
        group.append(label.Label(terminalio.FONT, text="OVER", color=0xFF0000,
                                 x=84, y=100, scale=3))

        div_bmp = displayio.Bitmap(180, 2, 2)
        div_pal = displayio.Palette(2)
        div_pal[0] = 0x000000
        div_pal[1] = 0x444444
        for x in range(180):
            div_bmp[x, 0] = 1
            div_bmp[x, 1] = 1
        group.append(displayio.TileGrid(div_bmp, pixel_shader=div_pal, x=30, y=118))

        stats = (
            ("SCORE", str(score),  0xFFFF00),
            ("LINES", str(lines),  0xFFFF00),
            ("LEVEL", str(level),  0xFFFF00),
        )
        for i, (key, val, col) in enumerate(stats):
            y = 136 + i * 32
            group.append(label.Label(terminalio.FONT, text=key,
                                     color=0xAAAAAA, x=40, y=y, scale=1))
            group.append(label.Label(terminalio.FONT, text=val,
                                     color=col, x=130, y=y, scale=2))

        prompt = label.Label(terminalio.FONT, text="- PRESS HARD-DROP TO PLAY AGAIN -",
                             color=0xFFFFFF, x=15, y=255, scale=1)
        group.append(prompt)
        self._prompt_label = prompt

        return group
    
    def _update_sound_labels(self):
        if not self._on_lbl:
            return
        if self.sound_on:
            self._on_lbl.color  = 0xFFFFFF
            self._off_lbl.color = 0x666666
            self._box_tile.x    = 181   #on
        else:
            self._on_lbl.color  = 0x666666
            self._off_lbl.color = 0xFFFFFF
            self._box_tile.x    = 159   #off
