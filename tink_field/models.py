import copy
from datetime import timedelta
from typing import Any

from django.db import models

from .tink_encryptor import get_encryptor as tink_encryptor
from .b64_encryptor import B64Encryptor
from .b64_encryptor import get_encryptor as b64_encryptor
from .legacy_encryptor import get_encryptor as legacy_encryptor
from .encrypted_field import EncryptedField, EncryptorInterface


class PlaintextEncryptor(EncryptorInterface):
    def encrypt(self, plaintext: Any, assocated_data: Any) -> Any:
        return plaintext

    def decrypt(self, ciphertext: Any, assocated_data: Any) -> Any:
        return ciphertext


class JsonEncryptor(B64Encryptor):
    def __init__(self):
        super().__init__()

    def encrypt(
        self, plaintext_dict: dict[Any, Any], associated_data: str | bytes = b""
    ) -> dict[Any, Any]:
        ciphertext = super().encrypt(plaintext_dict["secret"], associated_data)
        ciphertext_dict = copy.deepcopy(plaintext_dict)
        ciphertext_dict["secret"] = ciphertext
        return ciphertext_dict

    def decrypt(
        self, ciphertext_dict: dict[Any, Any], associated_data: str | bytes = b""
    ) -> dict[Any, Any]:
        plaintext = super().encrypt(ciphertext_dict["secret"], associated_data)
        plaintext_dict = copy.deepcopy(ciphertext_dict)
        plaintext_dict["secret"] = plaintext
        return plaintext_dict


class Secret(models.Model):
    name = models.CharField(max_length=50)
    _plaintext_secret = models.CharField(max_length=50, db_column="plaintext_secret")
    _plaintext_json = models.JSONField(db_column="plaintext_json")

    binary_encrypted_secret = models.BinaryField(blank=True, null=True)
    binary_reencryption_time = models.DateTimeField(blank=True, null=True)
    plaintext_from_binary = EncryptedField(
        encryptor=tink_encryptor(),
        ciphertext_attr="binary_encrypted_secret",
        last_reencryption_time_attr="binary_reencryption_time",
        fallback_encryptor=None,
        reencryption_window=timedelta(days=30),
        associated_data_attr="name",
    )

    b64_encrypted_secret = models.CharField(max_length=1000)
    b64_reencryption_time = models.DateTimeField(blank=True, null=True)
    plaintext_from_b64 = EncryptedField(
        encryptor=b64_encryptor(),
        ciphertext_attr="b64_encrypted_secret",
        last_reencryption_time_attr="b64_reencryption_time",
        fallback_encryptor=legacy_encryptor(),
        reencryption_window=timedelta(days=30),
        associated_data_attr="name",
    )

    json_with_encrypted_secret = models.JSONField()
    json_reencryption_time = models.DateTimeField(blank=True, null=True)
    plaintext_from_json = EncryptedField(
        encryptor=JsonEncryptor(),
        ciphertext_attr="json_with_encrypted_secret",
        last_reencryption_time_attr="json_reencryption_time",
        fallback_encryptor=legacy_encryptor(),
        reencryption_window=timedelta(days=30),
        associated_data_attr="name",
    )
