import re
from datetime import timedelta, timezone, datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from google.cloud import kms

from tink_field.encryptor import can_use_kms, kms_path

# Example: 30d5h16m30s
# Each component is optional but they must appear in that relative order
cutoff_regex = re.compile(
    r"((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?"
)


def parse_cutoff(cutoff_str):
    if match := cutoff_regex.match(cutoff_str):
        time_components = {
            name: int(value)
            for name, value in match.groupdict().items()
            if value is not None
        }
        return timedelta(**time_components)


def disable_key_version(version_name, client):
    key_version = {
        "name": version_name,
        "state": kms.CryptoKeyVersion.CryptoKeyVersionState.DISABLED,
    }
    update_mask = {"paths": ["state"]}
    disabled_version = client.update_crypto_key_version(
        request={"crypto_key_version": key_version, "update_mask": update_mask},
    )
    print(f"Disabled key version: {version_name}")


def destroy_key_version(version_name, client):
    destroyed_version = client.destroy_crypto_key_version(
        {"name": version_name},
    )
    print(f"Scheduled key version for destruction: {version_name}")


class Command(BaseCommand):
    help = "Expires key versions older than the cutoff"

    def add_arguments(self, parser):
        parser.add_argument("--destroy", action="store_true")
        parser.add_argument("--cutoff", type=str, default="30d")

    def handle(self, *args, **options):
        cutoff = parse_cutoff(options["cutoff"])
        if not can_use_kms() or not cutoff:
            return

        client = kms.KeyManagementServiceClient()
        request = kms.ListCryptoKeyVersionsRequest(
            parent=kms_path(),
            filter="state=ENABLED",
        )
        key_version_iter = client.list_crypto_key_versions(request=request)

        for version in key_version_iter:
            if datetime.now(timezone.utc) - version.create_time > cutoff:
                if options["destroy"]:
                    destroy_key_version(version.name, client)
                else:
                    disable_key_version(version.name, client)
