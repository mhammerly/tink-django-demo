import base64
from cryptography.fernet import Fernet
from django.conf import settings

from .encrypted_field import EncryptorInterface

class LegacyEncryptor(EncryptorInterface):
    """
    Fernet-based encryptor. Deals with utf-8 strings. Does not support associated data.
    """
    def __init__(self):
        self.fernet = Fernet(settings.LEGACY_KEY)

    def encrypt(self, plaintext: str | bytes, _associated_data: str | bytes = b"") -> str:
        if type(plaintext) == str:
            plaintext = plaintext.encode("utf-8")
        return self.fernet.encrypt(plaintext).decode("utf-8")

    def decrypt(self, ciphertext: str | bytes, _associated_data: str | bytes = b"") -> str:
        return self.fernet.decrypt(ciphertext)

_encryptor: LegacyEncryptor = None

def get_encryptor() -> LegacyEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = LegacyEncryptor()

    return _encryptor


