# Module pour appareils TWI (I2C) sur le RaspberryPi

import time
import logging
import datetime 

import smbus  # Installer sur RPi (bus TWI)

from threading import Event

class LcdHandler:

    # Define some device parameters
    I2C_ADDR = 0x27  # I2C device address
    LCD_WIDTH = 16  # Maximum characters per line

    # Define some device constants
    LCD_CHR = 1  # Mode - Sending data
    LCD_CMD = 0  # Mode - Sending command

    LCD_LINE_1 = 0x80  # LCD RAM address for the 1st line
    LCD_LINE_2 = 0xC0  # LCD RAM address for the 2nd line
    LCD_LINE_3 = 0x94  # LCD RAM address for the 3rd line
    LCD_LINE_4 = 0xD4  # LCD RAM address for the 4th line
    LCD_LINES = [LCD_LINE_1, LCD_LINE_2, LCD_LINE_3, LCD_LINE_4]

    LCD_BACKLIGHT_ON = 0x08  # On
    LCD_BACKLIGHT_OFF = 0x00  # Off

    ENABLE = 0b00000100  # Enable bit

    # Timing constants
    E_PULSE = 0.0005
    E_DELAY = 0.0005

    def __init__(self):
        self.__logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.lines = dict()
        self.lines[0] = "Initialising"
        self.lines[1] = "0%"
        self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_ON
        self.bus = None

    def initialise(self):
        self.__logger.debug("LcdHandler.initialise()")
        self.bus = smbus.SMBus(1)  # Rev 2 Pi uses 1

        # Initialise display
        self.lcd_byte(0x33, LcdHandler.LCD_CMD)  # 110011 Initialise
        self.lcd_byte(0x32, LcdHandler.LCD_CMD)  # 110010 Initialise
        self.lcd_byte(0x06, LcdHandler.LCD_CMD)  # 000110 Cursor move direction
        self.lcd_byte(0x0C, LcdHandler.LCD_CMD)  # 001100 Display On,Cursor Off, Blink Off
        self.lcd_byte(0x28, LcdHandler.LCD_CMD)  # 101000 Data length, number of lines, font size
        self.lcd_byte(0x01, LcdHandler.LCD_CMD)  # 000001 Clear display
        time.sleep(LcdHandler.E_DELAY)
        
    # Close LCD, shut down the backlight. Write "Stopped".
    def close(self):
        self.lcd_string("Stopped", LcdHandler.LCD_LINE_1)
        self.lcd_string("", LcdHandler.LCD_LINE_2)
        time.sleep(LcdHandler.E_DELAY)

        self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_OFF
        self.lcd_byte(0x01, LcdHandler.LCD_CMD)  # 000001 Clear display
        time.sleep(LcdHandler.E_DELAY)

    def lcd_byte(self, bits, mode):
        # Send byte to data pins
        # bits = the data
        # mode = 1 for data
        #        0 for command

        bits_high = mode | (bits & 0xF0) | self.LCD_BACKLIGHT
        bits_low = mode | ((bits << 4) & 0xF0) | self.LCD_BACKLIGHT

        # High bits
        self.bus.write_byte(LcdHandler.I2C_ADDR, bits_high)
        self.lcd_toggle_enable(bits_high)

        # Low bits
        self.bus.write_byte(LcdHandler.I2C_ADDR, bits_low)
        self.lcd_toggle_enable(bits_low)

    def lcd_toggle_enable(self, bits):
        # Toggle enable
        time.sleep(LcdHandler.E_DELAY)
        self.bus.write_byte(LcdHandler.I2C_ADDR, (bits | LcdHandler.ENABLE))
        time.sleep(LcdHandler.E_PULSE)
        self.bus.write_byte(LcdHandler.I2C_ADDR, (bits & ~LcdHandler.ENABLE))
        time.sleep(LcdHandler.E_DELAY)

    def lcd_string(self, message, line):
        # Send string to display

        message = message.ljust(LcdHandler.LCD_WIDTH, " ")

        self.lcd_byte(line, LcdHandler.LCD_CMD)

        for i in range(LcdHandler.LCD_WIDTH):
            self.lcd_byte(ord(message[i]), LcdHandler.LCD_CHR)
            
    def set_backlight(self, actif):
        if actif:
            self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_ON
        else:
            self.LCD_BACKLIGHT = LcdHandler.LCD_BACKLIGHT_OFF
        
        # Ecrire un byte dummy pour activer le changement
        self.lcd_byte(0x00, LcdHandler.LCD_CMD)  # 000000 No effect

    def afficher(self, lignes_lcd: list):
        for no_ligne in range(0, min(2, len(lignes_lcd))):
            self.lcd_string(lignes_lcd[no_ligne], self.LCD_LINES[no_ligne])

    def toggle_lcd_onoff(self, valeur: str):
        super().toggle_lcd_onoff(valeur)
        self.set_backlight(self._affichage_actif)


def main():
    test = LcdHandler()
    test.initialise()
    test.set_backlight(False)
    Event().wait(1)
    test.set_backlight(True)
    test.afficher(['Un lapin', 'se promene'])
    Event().wait(1)
    test.afficher(['pour souper', 'poutine!'])
    Event().wait(4)
    test.set_backlight(False)


if __name__ == '__main__':
    main()

