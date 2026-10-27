import requests
from requests.auth import HTTPDigestAuth
import base64
import json
import paho.mqtt.client as mqtt

# Hardware Info
# /stw-cgi/system.cgi?msubmenu=deviceinfo&action=view

# http://192.168.11.124/stw-cgi/attributes.cgi/attributes

# http://192.168.11.124/stw-cgi/eventsources.cgi?msubmenu=objectdetection&action=view&Channel=0&SunapiSeqId=15
# http://192.168.11.124/stw-cgi/attributes.cgi/cgis

# Snapshot erstellen
# http://192.168.11.124/stw-cgi/video.cgi?msubmenu=snapshot&action=view

# Stream
# http://192.168.11.124/stw-cgi/video.cgi?msubmenu=stream&action=view

# Kamera-Daten
# 

IP = "192.168.11.124"
USER = "admin"
PASS = "c6zAw5Su9h5wanwP"

url = f"http://{IP}/stw-cgi/attributes.cgi?action=listen&type=object_detection"

auth = HTTPDigestAuth(USER, PASS)

def setup_camera():
    # 1. Aktivieren des Kennzeichen-Bild-Transfers
    url = f"http://{IP}/stw-cgi/eventsources.cgi?msubmenu=metaimagetransfer&action=set&Channel=0&ObjectTypes=LicensePlate&Base64ObjectImageEnable=True"
    r = requests.get(url, auth=auth)
    print("Kamera-Setup Status:", r.status_code, r.content)

def listen_to_plates():
    # 2. Den Stream öffnen
    stream_url = f"http://{IP}/stw-cgi/eventservice.cgi?msubmenu=eventnotification&action=listen&eventtypes=ObjectDetection"
    
    print("Starte Kennzeichen-Monitoring...")
    with requests.get(stream_url, auth=auth, stream=True, timeout=None) as response:
        print(response.content)
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                
                # Suchen nach dem Kennzeichen-Event
                if "LicensePlate" in data:
                    print("Kennzeichen erkannt!")
                    process_meta_data(data)

def process_meta_data(xml_or_json_data):
    # Hier extrahierst du das Feld 'ObjectImage' (Base64)
    # Da Hanwha oft Multipart/Mixed sendet, nutzen wir einen einfachen String-Split 
    # oder einen JSON-Parser, je nachdem was die Kamera liefert.
    if "ObjectImage" in xml_or_json_data:
        # Beispielhafter Extraktions-Logik (vereinfacht)
        start_tag = "<ObjectImage>"
        end_tag = "</ObjectImage>"
        if start_tag in xml_or_json_data:
            base64_str = xml_or_json_data.split(start_tag)[1].split(end_tag)[0]
            
            # Bild speichern oder an OCR übergeben
            with open("current_plate.jpg", "wb") as f:
                f.write(base64.b64decode(base64_str))
            print("Bild 'current_plate.jpg' wurde gespeichert.")

if __name__ == "__main__":
    setup_camera()
    listen_to_plates()