from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .legacy_encryptor import legacy_encryptor

from .models import Secret


def index(request):
    secrets = Secret.objects.all()
    response = "<table><tr><th>name</th><th>plaintext</th><th>last reencrypted</th><th>ciphertext</th></tr>"

    def print_secret(s):
        plaintext = s.plaintext.decrypted_value() if s.plaintext else ""
        return f"<tr><td>{s.name}</td><td>{plaintext}</td><td>{s.last_reencryption_time}</td><td>{s.encrypted_secret}</td>"

    response += "".join(map(print_secret, secrets))
    return HttpResponse(response)


def create(request):
    if request.method == "GET":
        return render(request, "tink_field/create.html")
    else:
        print(request.POST)

        if request.POST["encryptor"] == "default":
            secret = Secret(name=request.POST["name"])
            secret.plaintext = request.POST["plaintext"]
            secret.save()
        else:
            secret = Secret(name=request.POST["name"])
            ciphertext = legacy_encryptor.encrypt(request.POST["plaintext"])
            print(f"saving ciphertext {ciphertext}")
            secret.encrypted_secret = ciphertext
            secret.save()

        return HttpResponseRedirect(reverse("index"))
