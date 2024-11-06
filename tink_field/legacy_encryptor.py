import base64
from cryptography.fernet import Fernet
from django.conf import settings


class Encryptor:
    def __init__(self):
        self.fernet = Fernet(settings.LEGACY_KEY)

    def encrypt(self, plaintext):
        return self.fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext):
        print(type(ciphertext), ciphertext)
        return self.fernet.decrypt(ciphertext)


legacy_encryptor = Encryptor()
