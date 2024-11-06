from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


import tink
from tink import aead
from tink import secret_key_access
from tink.integration import gcpkms

from tink_field.encryptor import can_use_kms, kms_path


class Command(BaseCommand):
    help = "Creates a tink keyset"

    def add_arguments(self, parser):
        parser.add_argument("--force-plaintext", action="store_true")
        parser.add_argument("--output-file", type=str, required=True)

    def handle(self, *args, **options):
        use_plaintext = options["force_plaintext"] or not can_use_kms()

        aead.register()
        key_template = aead.aead_key_templates.AES128_GCM
        keyset_handle = tink.new_keyset_handle(key_template)

        if use_plaintext:
            serialized_keyset = tink.json_proto_keyset_format.serialize(
                keyset_handle, secret_key_access.TOKEN
            )
        else:
            kms_uri = f"gcp-kms://{kms_path()}"
            client = gcpkms.GcpKmsClient(kms_uri, settings.GCP_CREDENTIAL_FILE)
            remote_aead = client.get_aead(kms_uri)

            serialized_keyset = tink.json_proto_keyset_format.serialize_encrypted(
                keyset_handle, remote_aead, b""
            )

        with open(options["output_file"], "wt") as f:
            f.write(serialized_keyset)
