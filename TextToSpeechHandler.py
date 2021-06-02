import logging
import azure.functions as func
import azure.cognitiveservices.speech as speechsdk
# Request module must be installed.
# Run pip install requests if necessary.
import random
import requests
import json
import dropbox
from azure.cognitiveservices.speech import AudioDataStream
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__

# API keys
speech_key, service_region = "XXXXXXXXXX", "westeurope"
connect_str = "XXXXXXXXXXX"

speeach_format = "Audio48Khz96KBitRateMonoMp3"
CHARGE_PER_HARACTER = 0.01
MINIMAL_CHARGE = 20

## Create ID form first word on number code
def createFileSlug(text):
    words = text[0:10].split(' ')
    words.pop()
    join_words =  "-".join(words).translate({ord(i): None for i in ',.[]¨?=`@#$~^&*'})
    number = str(random.randint(1000,9999)) 
    #timeUnits = [str(now.month), str(now.day), str(now.hour), str(now.minute), str(now.second)]
    slugWithDate = join_words + "-" + number
    return slugWithDate

## API to save MP3 and JSON formats to storage
def storage_driver(file, fileName, mine):
    # Create the BlobServiceClient object which will be used to create a container client
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    # Create a blob client using the local file name as the name for the blob
    blob = fileName + mine
    blob_client = blob_service_client.get_blob_client(container="audiofiles", blob=blob)
    result = blob_client.upload_blob(file)

## API to save files to Dropbox
# def dropbox_driver(stream, filePath):
#     dropBox_key = "jbbMrzBdcggAAAAAAAAAAcia0T9uniVxpColCUJ1CfjhUBUVDzaj0LQTpbZHYgPs"
#     dbx = dropbox.Dropbox(dropBox_key)
#     result = dbx.files_upload(stream, filePath, mode=dropbox.files.WriteMode.overwrite)
#     shared_link_metadata = dbx.sharing_create_shared_link_with_settings(filePath)
#     url =  shared_link_metadata.url
#     return url

# API settup for SpeechSynthesizer
def speech_synthesis_to_audio_data_stream(lang, voice, sampleText):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat[speeach_format])
    speech_config.speech_synthesis_language = lang
    speech_config.speech_synthesis_voice_name = voice
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = speech_synthesizer.speak_text_async(sampleText).get()
    synthesisResult = speechsdk.SpeechSynthesisResult(result)
    data = synthesisResult.audio_data
    return data

# Check if text lenght is in limit
def textLenghtCheck(inputString, limit):
    characterCount = inputString.count("")
    if characterCount > limit:
        shortSample = inputString[0:limit].rsplit('.', 1)[0] + ". Konec ukázky."
        return shortSample
    else:
        return inputString

# Separate plain text from JSON schema
def getPlainText(schema):
    plainText = ""
    for paragraph in schema:
        for children in paragraph["children"]:
            text = children["text"] + ". "
            plainText = plainText + text

    return plainText

# Main client app API handlers 
def main(req: func.HttpRequest) -> func.HttpResponse:

    try:
        req_body = req.get_json()
        lang = req_body["lang"]
        voice = req_body["voice"]
        schema = req_body["schema"]
        testCode = req_body["testCode"]

        # Check if test code is correct
        if testCode != "Beta99":
            return func.HttpResponse(
                "unauthorized",
                status_code=401
            )

        sampleLimit = 20000

        # get plain text from json schema
        text = textLenghtCheck(getPlainText(schema), sampleLimit)
        
        # generate audio stream
        stream = speech_synthesis_to_audio_data_stream(lang, voice, text)

        # create files ID
        fileSlug = createFileSlug(text)
        result = storage_driver(stream, fileSlug, ".mp3")

        jsonDoc = json.dumps(schema)
        resultDoc = storage_driver(jsonDoc, fileSlug, ".json")

    except Exception:
        return func.HttpResponse(
            "Basic wavepage JSON missing in POST request",
            status_code=200
        )
        
    return func.HttpResponse(
        fileSlug,
        status_code=200
    )
