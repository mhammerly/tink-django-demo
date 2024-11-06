import base64

import tink
from tink import aead
from tink.integration import gcpkms
from tink import secret_key_access

from django.conf import settings

_encryptor = None


def can_use_kms():
    return all(
        map(
            lambda x: x is not None,
            [
                settings.GCP_PROJECT_ID,
                settings.KMS_LOCATION_ID,
                settings.KMS_KEY_RING_ID,
                settings.KMS_KEY_ID,
            ],
        ),
    )


def kms_path():
    if can_use_kms():
        return f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.KMS_LOCATION_ID}/keyRings/{settings.KMS_KEY_RING_ID}/cryptoKeys/{settings.KMS_KEY_ID}"


class Encryptor:
    def __init__(self):
        aead.register()

        remote_aead = None
        if can_use_kms():
            kms_uri = f"gcp-kms://{kms_path()}"
            client = gcpkms.GcpKmsClient(kms_uri, settings.GCP_CREDENTIAL_FILE)
            remote_aead = client.get_aead(kms_uri)

        keyset_contents = None
        if settings.KEYSET_FILE is not None:
            with open(settings.KEYSET_FILE, "rt") as f:
                keyset_contents = f.read()

        if keyset_contents is not None and remote_aead is not None:
            # Encrypted keyset
            keyset_handle = tink.json_proto_keyset_format.parse_encrypted(
                keyset_contents,
                remote_aead,
                None,  # associated data
            )
            self.encryptor = keyset_handle.primitive(aead.Aead)
        elif keyset_contents is not None:
            # Plaintext keyset
            keyset_handle = tink.json_proto_keyset_format.parse(
                keyset_contents, secret_key_access.TOKEN
            )
            self.encryptor = keyset_handle.primitive(aead.Aead)
        elif remote_aead is not None:
            # KmsEnvelopeAead
            self.encryptor = aead.KmsEnvelopeAead(
                aead.aead_key_templates.AES256_GCM, remote_aead
            )
        else:
            raise Exception("No encryptor settings provided")
        pass

    def encrypt(self, plaintext, associated_data):
        if type(plaintext) == str:
            plaintext = plaintext.encode("utf-8")
        if type(associated_data) == str:
            associated_data = associated_data.encode("utf-8")
        ciphertext = self.encryptor.encrypt(plaintext, associated_data)

        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt(self, encoded_ciphertext, associated_data):
        if type(associated_data) == str:
            associated_data = associated_data.encode("utf-8")

        ciphertext = base64.b64decode(encoded_ciphertext)
        return self.encryptor.decrypt(ciphertext, associated_data).decode("utf-8")


def get_encryptor():
    global _encryptor
    if _encryptor is None:
        _encryptor = Encryptor()

    return _encryptor
