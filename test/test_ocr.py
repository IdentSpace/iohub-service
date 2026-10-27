import requests
import json
# import easyocr
from requests.auth import HTTPDigestAuth

from fast_plate_ocr import LicensePlateRecognizer

SNAP_URL = "http://192.168.16.207/stw-cgi/video.cgi?msubmenu=snapshot&action=view"
CAM_USER = "admin"
CAM_PASS = "c6zAw5Su9h5wanwP"

# reader = easyocr.Reader(['de', 'en'])

def process_lpr():
	print("Starte Bild-Download...")
	try:
		# Bild von der Kamera abrufen (Digest Auth ist Standard bei Hanwha)
		response = requests.get(SNAP_URL, auth=HTTPDigestAuth(CAM_USER, CAM_PASS), timeout=5)
		
		if response.status_code == 200:
			with open("temp_snapshot.jpg", "wb") as f:
				f.write(response.content)
			
			print("Analysiere Kennzeichen...")

			m = LicensePlateRecognizer('cct-xs-v1-global-model')
			print(m.run('temp_snapshot.jpg'))
			# OCR ausführen
			# results = reader.readtext("temp_snapshot.jpg")
			
			# if not results:
				# print("Kein Text im Bild gefunden.")
			
			# print(results)

			# for (bbox, text, prob) in results:
			# 	# Wir filtern nach einer gewissen Mindestwahrscheinlichkeit (z.B. 30%)
			# 	if prob > 0.3:
			# 		print(f"ERKANNTES KENNZEICHEN: {text} (Sicherheit: {int(prob*100)}%)")
		else:
			print(f"Fehler: Kamera antwortet mit Status {response.status_code}")
			
	except Exception as e:
		print(f"Fehler bei der Verarbeitung: {e}")


process_lpr()