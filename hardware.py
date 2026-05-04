# hardware.py
import board
import busio
import displayio
import digitalio
from adafruit_debouncer import Debouncer
import fourwire
import adafruit_ili9341 #type: ignore
import pwmio
import time

#pin assignmetns
PIN_LEFT   = board.GP21
PIN_RIGHT  = board.GP22
PIN_ROTATE = board.GP24
PIN_DOWN   = board.GP23
PIN_DROP   = board.GP20  #hard drop
PIN_BUZZER = board.GP14

# ILI9341 spi pins left to right not including 3.3v,grnd,led
PIN_CS     = board.GP5
PIN_RST    = board.GP7
PIN_DC     = board.GP6
PIN_MOSI   = board.GP3
PIN_SCK    = board.GP2
PIN_MISO   = board.GP4

DISPLAY_W  = 240
DISPLAY_H  = 320


#create each button
def _make_button(pin):
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.INPUT
    io.pull = digitalio.Pull.UP  
    return Debouncer(io)


class Hardware:

    def __init__(self):
        #buttons
        self._left   = _make_button(PIN_LEFT)
        self._right  = _make_button(PIN_RIGHT)
        self._rotate = _make_button(PIN_ROTATE)
        self._down   = _make_button(PIN_DOWN)
        self._drop   = _make_button(PIN_DROP)

        self._all_buttons = (
            self._left,
            self._right,
            self._rotate,
            self._down,
            self._drop,
        )
        #buzzer
        self._buzzer = pwmio.PWMOut(PIN_BUZZER, frequency=440,
                             duty_cycle=0, variable_frequency=True)
        
        #ili display setup
        displayio.release_displays()
        spi = busio.SPI(clock=PIN_SCK, MOSI=PIN_MOSI, MISO=PIN_MISO)
        bus = fourwire.FourWire(spi, command=PIN_DC, chip_select=PIN_CS,reset=PIN_RST, baudrate=32000000)
        self.display = adafruit_ili9341.ILI9341(bus,width=DISPLAY_W,height=DISPLAY_H, rotation=270)
         
    def read_buttons(self):
        for btn in self._all_buttons:
            btn.update()

        return {
            'left':   not self._left.value,    #inverted b/c 
            'right':  not self._right.value,   #false = pressed
            'rotate': not self._rotate.value,
            'down':   not self._down.value,
            'drop':   not self._drop.value,
        }
        
    #BUZZER TONES
    def play_tone(self, freq, duration_ms):
        self._buzzer.frequency  = freq
        self._buzzer.duty_cycle = 32768
        time.sleep(duration_ms / 1000)
        self._buzzer.duty_cycle = 0

    def play_start(self):
        for freq, dur in ((523, 80), (659, 80), (784, 120)):
            self.play_tone(freq, dur)

    def play_lines(self, count):
        tones = {
            1: ((523, 80),),
            2: ((523, 70), (659, 70)),
            3: ((523, 60), (659, 60), (784, 60)),
            4: ((523, 60), (659, 60), (784, 60), (1047, 120)),
        }
        for freq, dur in tones.get(count, ()):
            self.play_tone(freq, dur)

    def play_gameover(self):
        for freq, dur in ((440, 180), (330, 300)):
            self.play_tone(freq, dur)