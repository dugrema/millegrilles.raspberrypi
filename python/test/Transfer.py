#!/usr/bin/env python

#
# Example using Dynamic Payloads
# 
#  This is an example of how to use payloads of a varying (dynamic) size.
# 

from __future__ import print_function
import time
import RF24
import RPi.GPIO as GPIO

irq_gpio_pin = None

########### USER CONFIGURATION ###########
# See https://github.com/TMRh20/RF24/blob/master/pyRF24/readme.md

# CE Pin, CSN Pin, SPI Speed

# Setup for GPIO 22 CE and CE0 CSN with SPI Speed @ 8Mhz
# radio = RF24(RPI_V2_GPIO_P1_15, BCM2835_SPI_CS0, BCM2835_SPI_SPEED_8MHZ)

# RPi B
# Setup for GPIO 15 CE and CE1 CSN with SPI Speed @ 8Mhz
# radio = RF24(RPI_V2_GPIO_P1_15, BCM2835_SPI_CS0, BCM2835_SPI_SPEED_8MHZ)

# RPi B+
# Setup for GPIO 22 CE and CE0 CSN for RPi B+ with SPI Speed @ 8Mhz
# radio = RF24(RPI_BPLUS_GPIO_J8_15, RPI_BPLUS_GPIO_J8_24, BCM2835_SPI_SPEED_8MHZ)

# RPi Alternate, with SPIDEV - Note: Edit RF24/arch/BBB/spi.cpp and  set 'this->device = "/dev/spidev0.0";;' or as listed in /dev
radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_8MHZ)
# radio = RF24.RF24(22, 0);


# Setup for connected IRQ pin, GPIO 24 on RPi B+; uncomment to activate
# irq_gpio_pin = RPI_BPLUS_GPIO_J8_18
# irq_gpio_pin = 24

##########################################
def try_read_data(channel=0):
    if radio.available():
        while radio.available():
            len = radio.getDynamicPayloadSize()
            receive_payload = radio.read(len)
            print('Got payload size={}'.format(len))

 
pipes = [0xABCDABCD71, 0x544d52687C]
min_payload_size = 4
max_payload_size = 32
payload_size_increments_by = 1
next_payload_size = max_payload_size
inp_role = 'none'
send_payload = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ789012'
millis = lambda: int(round(time.time() * 1000))

print('pyRF24/examples/pingpair_dyn/')
radio.begin()
radio.setChannel(0x24)
radio.setPALevel(RF24.RF24_PA_MAX)
# radio.enableDynamicPayloads()
radio.setRetries(15, 1)
radio.setDataRate(RF24.RF24_250KBPS)
radio.setAutoAck(1)
radio.setCRCLength(RF24.RF24_CRC_16)

print(' ************ Role Setup *********** ')
while (inp_role != '0') and (inp_role != '1'):
    inp_role = str(input('Choose a role: Enter 0 for receiver, 1 for transmitter (CTRL+C to exit) '))

if inp_role == '0':
    print('Role: Pong Back, awaiting transmission')
    # radio.openWritingPipe(pipes[0])
    radio.openReadingPipe(1, pipes[1])
    radio.startListening()
else:
    print('Role: Ping Out, starting transmission')
    # radio.openWritingPipe(pipes[1])
    radio.openReadingPipe(1, pipes[0])

radio.printDetails()

counter = 0

# forever loop
while 1:
    if inp_role == '1':  # ping out
        # The payload will always be the same, what will change is how much of it we send.

        # First, stop listening so we can talk.
        radio.stopListening()

        # Take the time, and send it.  This will block until complete
        print('Now sending length %d ' % next_payload_size)
        compteur = 0
        tranmission = False
        for i in range(0, 200):
            transmission = radio.write(send_payload[:next_payload_size])
            if transmission:
                print("Nombre paquets avant success: %d" % compteur)
                break
            compteur = compteur + 1
        if not transmission:
            print("Echec transmission apres %d paquets" % compteur)

        # Now, continue listening
        radio.startListening()


        time.sleep(2)
    else:
        # if there is data ready
        try_read_data()
