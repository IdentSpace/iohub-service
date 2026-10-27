import paho.mqtt.client as mqtt
import json



# 1. Callback: Wird aufgerufen, wenn der Client eine Bestätigung vom Broker erhält
def on_connect(client, userdata, flags, rc):
	# topics = [("#",0), ("küche/sensor", 0), ("garten/pumpe", 1), ("auto/status", 0)]
	topics = [("E4:30:22:BA:CD:3B/onvif-ej/RuleEngine/ObjectDetection/Object/&VideoSourceToken-0/ObjectDetectionRule-1", 0)]
	if rc == 0:
		print("Erfolgreich verbunden!")
		# Hier abonnieren wir das Topic
		client.subscribe(topics)
	else:
		print(f"Verbindung fehlgeschlagen mit Code {rc}")

# 2. Callback: Wird aufgerufen, wenn eine Nachricht auf einem abonnierten Topic eingeht
def on_message(client, userdata, msg):
	payload = msg.payload.decode()
	try:
		data = json.loads(payload)
		if "Data" in data and "ClassTypes" in data["Data"]:
			print("Objekterkennung erkannt!")
			detected_classes = data["Data"]["ClassTypes"]

			if "LicensePlate" in detected_classes:
				print("Kennzeichen erkannt!")
				# Hier kannst du weitere Aktionen durchführen, z.B. das Kennzeichen extrahieren oder speichern
				urlSnapshot = "http://192.168.16.207/stw-cgi/video.cgi?msubmenu=snapshot&action=view"

			
	except json.JSONDecodeError:
		print(f"Topic: {msg.topic} | Nachricht: {payload}")
	
	# print(f"Topic: {msg.topic} | Nachricht: {msg.payload.decode()}")

# 3. Client-Instanz erstellen
client = mqtt.Client()

# Callbacks zuweisen
client.on_connect = on_connect
client.on_message = on_message

# 4. Verbindung zum Broker aufbauen (z.B. öffentlicher Test-Broker oder lokal)
broker_address = "192.168.16.235" # Oder "localhost" / IP-Adresse
client.connect(broker_address, 1883, 60)

# 5. Endlosschleife starten, um auf Nachrichten zu warten
client.loop_forever()