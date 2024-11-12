import copy

from django.contrib import admin

from .models import Secret


class SecretAdmin(admin.ModelAdmin):

    def binary_secret(self, obj):
        if not obj.binary_encrypted_secret:
            return ""
        return (
            f"{obj.binary_encrypted_secret[0:5]}...{obj.binary_encrypted_secret[-5:]}"
        )

    def b64_secret(self, obj):
        return f"{obj.b64_encrypted_secret[0:5]}...{obj.b64_encrypted_secret[-5:]}"

    def json_with_secret(self, obj):
        secret = obj.json_with_encrypted_secret["secret"]
        if len(secret) > 30:
            secret = f"{secret[0:5]}...{secret[-5:]}"
        abbreviated = copy.deepcopy(obj.json_with_encrypted_secret)
        abbreviated["secret"] = secret
        return abbreviated

    def maybe_trigger_reencryption(self, request, queryset):
        for secret in queryset.iterator():
            print(f"Maybe re-encrypt binary: {secret.plaintext_from_binary}")
            print(f"Maybe re-encrypt b64: {secret.plaintext_from_b64}")
            print(f"Maybe re-encrypt json: {secret.plaintext_from_json}")
        pass

    list_display = [
        "name",
        "_plaintext_secret",
        "_plaintext_json",
        "binary_secret",
        "binary_reencryption_time",
        "b64_secret",
        "b64_reencryption_time",
        "json_with_secret",
        "json_reencryption_time",
    ]

    actions = ["maybe_trigger_reencryption"]


admin.site.register(Secret, SecretAdmin)
