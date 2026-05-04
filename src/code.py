# code.py circuit python main loop
import time
from hardware import Hardware
from game import Game
from renderer import Renderer
from menu import Menu
import microcontroller



#init other files
hw       = Hardware()
game     = Game()
renderer = Renderer(hw.display)
menu     = Menu(hw.display)

#state machine
STATE_MENU     = 0
STATE_PLAYING  = 1
STATE_GAMEOVER = 2

microcontroller.cpu.frequency = 200_000_000

state = STATE_MENU
menu.show_title()

while True:
    
    buttons = hw.read_buttons()
    
    if state == STATE_MENU:
        result = menu.update(buttons)
        if result == 'START':
            game.reset()
            renderer.activate()
            renderer.draw(game)
            if menu.sound_on:
                hw.play_start()
            state = STATE_PLAYING

    elif state == STATE_PLAYING:
        prev_lines = game.lines
        game.update(buttons)
        renderer.draw(game)
        cleared = game.lines - prev_lines
        if cleared and menu.sound_on:
            hw.play_lines(cleared)
        if game.over:
            if menu.sound_on:
                hw.play_gameover()
            menu.show_gameover(game.score, game.lines, game.level)
            state = STATE_GAMEOVER

    elif state == STATE_GAMEOVER:
        result = menu.update(buttons)
        if result == 'START':
            game.reset()
            renderer.activate()
            renderer.draw(game)
            if menu.sound_on:
                hw.play_start()
            state = STATE_PLAYING
    #time.sleep(0.016)
