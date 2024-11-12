import builtins
import base64
from datetime import datetime, timedelta, timezone


class EncryptorInterface:
    def encrypt(self, plaintext, associated_data=b""):
        raise NotImplementedError()

    def decrypt(self, ciphertext, associated_data=b""):
        raise NotImplementedError()


class DecryptedValueWrapper:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "<redacted>"

    def __repr__(self):
        return "<redacted>"

    def decrypted_value(self):
        return self.value


class EncryptedField:
    def __init__(
        self,
        *,
        encryptor: EncryptorInterface,
        ciphertext_attr: str,
        last_reencryption_time_attr: str,
        associated_data_attr: str | None = None,
        fallback_encryptor: EncryptorInterface | None = None,
        reencryption_window: timedelta = timedelta(days=30),
    ):
        self.encryptor = encryptor
        self.ciphertext_attr = ciphertext_attr
        self.last_reencryption_time_attr = last_reencryption_time_attr
        self.associated_data_attr = associated_data_attr
        self.fallback_encryptor = fallback_encryptor
        self.reencryption_window = reencryption_window

    def _get_associated_data(self, obj):
        associated_data = b""
        if self.associated_data_attr is not None:
            associated_data = getattr(obj, self.associated_data_attr, b"")

        match type(associated_data):
            case builtins.bytes:
                associated_data = associated_data
            case builtins.str:
                associated_data = associated_data.encode("utf-8")
            case builtins.int:
                associated_data = associated_data.to_bytes()
            case _:
                raise Exception(f"Unhandled type {type(associated_data)}")

        return associated_data

    def _encrypt(self, obj, plaintext):
        associated_data = self._get_associated_data(obj)
        print(f"encrypting {plaintext} with associated {associated_data}")
        ciphertext = self.encryptor.encrypt(plaintext, associated_data)
        return ciphertext

    def _decrypt(self, obj, encoded_ciphertext):
        associated_data = self._get_associated_data(obj)
        print(type(encoded_ciphertext))
        try:
            return self.encryptor.decrypt(encoded_ciphertext, associated_data)
        except Exception as e:
            print(f"failed to decrypt: {e}")
            if self.fallback_encryptor is None:
                raise
            else:
                return self.fallback_encryptor.decrypt(encoded_ciphertext)

    def __get__(self, obj, objtype=None):
        encoded_ciphertext = getattr(obj, self.ciphertext_attr, None)
        print(f"encoded ciphertext |||{encoded_ciphertext}|||")
        last_reencryption_time = getattr(obj, self.last_reencryption_time_attr, None)

        if encoded_ciphertext is None:
            return None

        try:
            plaintext = self._decrypt(obj, encoded_ciphertext)
        except Exception as e:
            print("failed to decrypt; nulling out value", e)
            setattr(obj, self.ciphertext_attr, None)
            setattr(obj, self.last_reencryption_time_attr, None)
            obj.save()
            return

        print(f"got plaintext {plaintext}")

        def now(other):
            if other.tzinfo is not None and other.tzinfo.utcoffset(None) is not None:
                return datetime.now(timezone.utc)
            else:
                return datetime.utcnow()

        if (
            last_reencryption_time is None
            or now(last_reencryption_time) - last_reencryption_time
            > self.reencryption_window
        ):
            if last_reencryption_time is not None:
                print(now(last_reencryption_time))
            print("trying to reencrypt")
            print(f"encoded {encoded_ciphertext} and plaintext {plaintext}")
            self.__set__(obj, plaintext)
            obj.save(
                update_fields=[self.ciphertext_attr, self.last_reencryption_time_attr]
            )

        return DecryptedValueWrapper(plaintext)

    def __set__(self, obj, value):
        new_ciphertext = self._encrypt(obj, value)
        print(f"encryption produced {new_ciphertext}")
        setattr(obj, self.ciphertext_attr, new_ciphertext)
        setattr(obj, self.last_reencryption_time_attr, datetime.now())
