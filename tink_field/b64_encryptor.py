import base64

from .tink_encryptor import TinkEncryptor

class B64Encryptor(TinkEncryptor):
    """
    `TinkEncryptor` that deals with utf-8 strings. Ciphertext is encoded as base64.
    """
    def __init__(self):
        super().__init__()

    def encrypt(self, plaintext: bytes | str, associated_data: bytes | str = b"") -> str:
        if type(plaintext) == str:
            plaintext = plaintext.encode("utf-8")
        if type(associated_data) == str:
            associated_data = associated_data.encode("utf-8")

        ciphertext = super().encrypt(plaintext, associated_data)
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt(self, encoded_ciphertext: bytes | str, associated_data: bytes | str= b"") -> str:
        if type(encoded_ciphertext) == str:
            encoded_ciphertext = encoded_ciphertext.encode("utf-8")
        if type(associated_data) == str:
            associated_data = associated_data.encode("utf-8")

        ciphertext = base64.b64decode(encoded_ciphertext)
        return super().decrypt(ciphertext, associated_data).decode("utf-8")


_encryptor: B64Encryptor = None

def get_encryptor() -> B64Encryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = B64Encryptor()

    return _encryptor


