# tink django example

this repository demonstrates an encrypted field on a django model that supports key rotation.

## demo site

first set up the environment:
```
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python manage.py createsuperuser # create an admin account
```

next, in `demo/settings.py` or `demo/settings_local.py`, configure one or both of:
- the GCP project/location/keyring/key details
  - see `gcloud_setup.sh` for some commands that create an acceptable keyring/key
- a tink keyset path
  - run `python manage.py tink_keyset --output-file tink-keyset.json` to generate a keyset

finally, run migrations and start the development server:
```
$ python manage.py migrate
$ python manage.py runserver
```

the demo revolves around the `Secret` model and the `EncryptedField` class it uses. new secrets should be created using the `/secrets/create` endpoint. existing secrets should be viewed in the admin UI at `/admin/tink_field/secret/`. re-encryption can be triggered in the admin interface by selecting one or more `Secret`s and running the "Maybe trigger reencryption" action.

when creating a new secret with the `/secrets/create` view, there is an "Encryptor" option to choose how the value will be encrypted. if "Default" is selected, a tink-based encryptor will be used for encryption and last-reencrypted timestamps will be filled out. if "Legacy" is selected, either a Fernet-based encryptor or no encryptor at all will be used for encryption and last-reencrypted timestamps will be left null.

each time a secret is accessed through `EncryptedField`, the `EncryptedField` will check the secret's last-reencrypted timestamp to decide whether the secret needs to be re-encrypted. if the timestamp is too long ago, or if it's non-existent (as it would be if the secret was created with the legacy encryptor), it will re-encrypt. accessing the secret through `EncryptedField` is all the "Maybe trigger reencryption" action does to re-encrypt values; in a real system, the reencryption will happen transparently whenever you access the secret.

## `EncryptedField`

`EncryptedField` is not actually a `ModelField` and is not part of the database schema. instead, it's a wrapper around existing database columns:
- a ciphertext column which contains encrypted data
- a timestamp column containing the last time the data was re-encrypted
- (optional) a column containing associated data (such as a name/id) that should be bound to the ciphertext

it additionally take three more parameters:
- an encryption module to actually handle encryption and decryption. this should subclass `EncryptorInterface`
- a `timedelta` representing the cutoff after which re-encryption should happen
- (optional) a fallback encryption module that will be used to decrypt if the primary module fails.
  - existing encrypted fields can be gradually migrated to a new encryptor this way

`tink_field/models.py` demonstrate a few different usages. one simple usage could look like:
```python
class Secret(models.Model):
    name = models.CharField(max_length=50)

    encrypted_secret = models.CharField(max_length=1000, blank=True, null=True)
    last_reencryption_time = models.DateTimeField(blank=True, null=True)

    plaintext = EncryptedField(
        encryptor=get_encryptor(),
        ciphertext_attr="encrypted_secret",
        last_reencryption_time_attr="last_reencryption_time",
        fallback_encryptor=legacy_encryptor,
        reencryption_window=timedelta(days=30),
        associated_data_attr="name",
    )
```

`EncryptedField` implements the descriptor interface and handles encryption/decryption under the hood. it is used almost as if it is a plaintext column:
- assigning a plaintext value to `my_secret.plaintext` will automatically encrypt the value and update the database fields for the ciphertext and last-reencrypted time
- reading `my_secret.plaintext` will:
  - automatically decrypt the value
    - if the primary encryptor fails, it will attempt to decrypt with the fallback decryptor
    - if the primary and fallback encryptors both fail, it will null out the field
  - if the last re-encryption time was too long ago, automatically re-encrypt it
  - return a `DecryptedValueWrapper` (if decryption succeeded) or `None` (if decryption failed)

`DecryptedValueWrapper` is essentially a reminder to developers that the data they are dealing with is supposed to be secret. the actual plaintext value is accessed via the `decrypted_value()` method (e.g. `my_secret.plaintext.decrypted_value()`).

### supported field types

`tink` expects plaintext/ciphertext/associated data to all be passed in as `bytes`. as long as your `EncryptorInterface` does that, anything should work.

`tink_field/models.py` shows a few django field types that can be encrypted with `EncryptedField`:
- a `CharField` with the ciphertext stored as a base64-encoded utf-8 string
- a `BinaryField` with the ciphertext stored as raw bytes
- a `JSONField` (or rather, a specific key inside a `JSONField`) with the ciphertext stored as a base64-encoded utf-8 string


## cryptography

the primary encryptor is driven by `tink` in one of three modes:
- tink's `KmsEnvelopeAead` powered by a key-encryption key in Google Cloud KMS
- tink's `Aead` powered by a tink keyset that was encrypted with a key-encryption key in Google Cloud KMS
- tink's `Aead` powered by a plaintext tink keyset

see tink's documentation for details. tink itself supports other KMS solutions, but this demo builds on GCP.

KMS details are configured in `demo/settings.py`. a django admin command that generates tink keysets (encrypted or unencrypted) is included:
```
$ python manage.py tink_keyset --force-plaintext --output-file tink-plaintext.json
$ python manage.py tink_keyset --output-file tink-encrypted.json # assumes KMS details are provided
```

### key rotation

fully automated key rotation, including disabling/destroying old key versions, should be achievable with any of the tink modes described above. it is relatively straightforward with `KmsEnvelopeAead` and a way to do it is described here. with tink keysets, the concepts are there but you have to manage storing/synchronizing the keyset across deployed hosts yourself.

first, create or choose a keyring + key to use for your encrypted field. configure a rotation schedule with gcloud or the console web UI or whatever you prefer. tell this project which key to use, and that's enough to say you're doing key rotation.

the trickier side of key rotation is automatically disabling or destroying old key versions because ensuring all records have been re-encrypted recently is difficult. in this demo, however, data that has not been accessed (and thus not been re-encrypted) recently is _intended_ to become inaccessible. this demo relies on key version invalidation as a cheap way to implement expiration dates on secrets. it's not incompatible with a scheme to ensure everything has been re-encrypted, but such a scheme is not included here.

one way to automate disabling/destroying old key versions is to deploy a cron job which runs the provided django admin command:
```python
$ python manage.py expire_key_versions --cutoff 30d            # just disables them
$ python manage.py expire_key_versions --cutoff 30d --destroy  # schedules them for destruction
```

another way is to deploy a Cloud Run function triggered by new key versions. see `gcloud_setup.sh` for a script that probably isn't actually runnable but illustrates all the steps.
