from arduinolibslw import Acorn128, Ascon128
import json
import binascii

from Crypto.Random import get_random_bytes

header = b"header"
data = b"secret"
key = get_random_bytes(16)
iv = get_random_bytes(16)

# cipher = Ascon128()
cipher = Acorn128()
cipher.clear()
cipher.setKey(key)
cipher.setKey(iv)
cipher.addAuthData(header)
ciphertext = cipher.encrypt(data)
tag = cipher.computeTag()

print("Cipher Text : %s" % binascii.hexlify(ciphertext).decode('utf-8'))
print("Tag : %s" % binascii.hexlify(tag).decode('utf-8'))

# Tester le decryptage

cipher.clear()
cipher.setKey(key)
cipher.setKey(iv)
cipher.addAuthData(header)
cleartext = cipher.decrypt(ciphertext)

print("Clear text : %s" % cleartext.decode('utf-8'))
cipher.checkTag(tag)
print("Tag OK!")


# Test avec donnees du Arduino
header = binascii.unhexlify(b"0102030405060708")
key = binascii.unhexlify(b"233952DEE4D5ED5F9B9C6D6FF80FF478")
iv = binascii.unhexlify(b"2D2B10316ABE7766AABADFEFB8E139EA")
tag = binascii.unhexlify(b"3E67F10B7FD68BAA8206C62BD0026B1B")
buffer_crypte = binascii.unhexlify(b"136A14EC1F53E0C7CB19AADC38E70D274774E3CAC147223E")

cipher.clear()
cipher.setKey(key)
cipher.setIV(iv)
cipher.addAuthData(header)
cleartext = cipher.decrypt(buffer_crypte)

print("Clear text : %s" % binascii.hexlify(cleartext).decode('utf-8'))
cipher.checkTag(tag)
print("Tag OK!")
