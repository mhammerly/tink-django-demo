from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .legacy_encryptor import get_encryptor as legacy_encryptor

from .models import Secret


def create(request):
    if request.method == "GET":
        return render(request, "tink_field/create.html")
    else:
        name = request.POST["name"]
        plaintext = request.POST["plaintext"]
        plaintext_json = {
            "name": name,
            "secret": plaintext,
        }
        new_secret = Secret(
            name=name, _plaintext_secret=plaintext, _plaintext_json=plaintext_json
        )

        if request.POST["encryptor"] == "default":
            # Set all our encrypted fields the normal way
            new_secret.plaintext_from_binary = plaintext
            new_secret.plaintext_from_b64 = plaintext
            new_secret.plaintext_from_json = plaintext_json
        else:
            # Bypass `EncryptedField`. Not bothering with the binary one
            new_secret.b64_encrypted_secret = legacy_encryptor().encrypt(plaintext)
            new_secret.json_with_encrypted_secret = plaintext_json

        new_secret.save()
        return HttpResponseRedirect(reverse("create"))
