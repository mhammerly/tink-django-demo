#!/bin/sh

# set up gcloud + ADC (assumes gcloud is already installed)
gcloud init
gcloud auth application-default login

# attempt to deduce project name
PROJECT=$(gcloud config configurations list --filter "IS_ACTIVE=True" --format json | jq -r '.[0].properties.core.project')

# create demo keyring + key with rotation schedule
gcloud kms keyrings create tink_demo --location us-west1
gcloud kms keys create tink_demo \
    --keyring tink_demo \
    --location us-west1 \
    --rotation-period 1d \
    --purpose encryption \
    --next-rotation-time $(date -v+1d +%Y-%m-%d)

# create pub/sub topic + feed that publishes new key version events to it
gcloud pubsub topics create key-rotation
gcloud asset feeds create kms-rotation \
    --project $PROJECT \
    --asset-types="cloudkms.googleapis.com/CryptoKeyVersion" \
    --pubsub-topic="projects/$PROJECT/topics/key-rotation"

# in the web console, deploy a Cloud Run Function with code like the following:
# # main.py
# import functions_framework
# import datetime
# from google.cloud import kms
# 
# @functions_framework.cloud_event
# def on_key_rotation(_cloud_event):
#     client = kms.KeyManagementServiceClient()
#     request = kms.ListCryptoKeyVersionsRequest(
#         parent="projects/$PROJECT/locations/us-west1/keyRings/tink_demo/cryptoKeys/tink_demo",
#     )
#     page_result = client.list_crypto_key_versions(request=request)
# 
#     for response in page_result:
#         if datetime.datetime.now(datetime.UTC) - response.create_time > datetime.timedelta(minutes=30):
#             print("Version is too old", response)
# 
#             key_version = {
#                 "name": response.name,
#                 "state": kms.CryptoKeyVersion.CryptoKeyVersionState.DISABLED,
#             }
# 
#             # Build the update mask.
#             update_mask = {"paths": ["state"]}
# 
#             # Call the API.
#             disabled_version = client.update_crypto_key_version(
#                 request={"crypto_key_version": key_version, "update_mask": update_mask}
#             )
#             print(f"Disabled key version: {disabled_version.name}")
#         else:
#             print("Version is new enough", response)

# # requirements.txt
# functions-framework==3.*
# google-cloud-kms
