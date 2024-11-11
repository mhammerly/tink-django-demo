from datetime import timedelta

from django.db import models

from .b64_encryptor import get_encryptor as b64_encryptor
from .legacy_encryptor import get_encryptor as legacy_encryptor
from .encrypted_field import EncryptedField


class Secret(models.Model):
    name = models.CharField(max_length=50)

    encrypted_secret = models.CharField(max_length=1000, blank=True, null=True)
    last_reencryption_time = models.DateTimeField(blank=True, null=True)

    plaintext = EncryptedField(
        encryptor=b64_encryptor(),
        ciphertext_attr="encrypted_secret",
        last_reencryption_time_attr="last_reencryption_time",
        fallback_encryptor=legacy_encryptor(),
        reencryption_window=timedelta(days=30),
        associated_data_attr="name",
    )
