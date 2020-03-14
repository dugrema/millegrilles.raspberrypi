import RF24
import RPi.GPIO as GPIO

radio = RF24.RF24(RF24.RPI_V2_GPIO_P1_22, RF24.BCM2835_SPI_CS0, RF24.BCM2835_SPI_SPEED_64MHZ)

if not radio.begin():
	raise Exception("Erreur demarrage radio")

radio.setChannel(0x0c)
radio.setDataRate(RF24.RF24_250KBPS)
radio.setPALevel(RF24.RF24_PA_MIN)
radio.setRetries(8, 15)
radio.setAutoAck(1)
radio.setCRCLength(RF24.RF24_CRC_16)

# radio.openWritingPipe(self.__adresse_serveur)
# radio.openReadingPipe(1, self.__adresse_reseau + bytes(0x0) + bytes(0x0))

# radio.openReadingPipe(1, addresseServeur)

print("Radio details")
print( radio.printDetails() )
print("Fin radio details")
