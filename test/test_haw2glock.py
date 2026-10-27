import sys
import os
import time
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# mapping = {
#     1: {"channel": 1, "address": 1},
#     2: {"channel": 1, "address": 2},
#     3: {"channel": 1, "address": 3},
#     4: {"channel": 1, "address": 4},
#     5: {"channel": 1, "address": 5},
#     6: {"channel": 1, "address": 6},
#     7: {"channel": 1, "address": 7},
#     8: {"channel": 1, "address": 8}, 
#     9: {"channel": 1, "address": 9},
#     10: {"channel": 1, "address": 10},
#     11: {"channel": 1, "address": 11},
#     12: {"channel": 1, "address": 12},
#     13: {"channel": 1, "address": 13},
#     14: {"channel": 1, "address": 14},
#     15: {"channel": 1, "address": 15},
#     16: {"channel": 1, "address": 16},
# }
#  Tabu 2 - 4
mapping = {
    1: {"channel": 1, "address": 1},
    2: {"channel": 1, "address": 8},
    3: {"channel": 1, "address": 9},
    4: {"channel": 1, "address": 31},
    5: {"channel": 1, "address": 27},
    6: {"channel": 1, "address": 2},
    7: {"channel": 1, "address": 7},
    8: {"channel": 1, "address": 12},
    9: {"channel": 1, "address": 14},
    10: {"channel": 1, "address": 29},
    11: {"channel": 1, "address": 3},
    12: {"channel": 1, "address": 6},
    13: {"channel": 1, "address": 11},
    14: {"channel": 1, "address": 25},
    15: {"channel": 1, "address": 28},
    16: {"channel": 1, "address": 4},
    17: {"channel": 1, "address": 5},
    18: {"channel": 1, "address": 10},
    19: {"channel": 1, "address": 15},
    20: {"channel": 1, "address": 13},
    21: {"channel": 1, "address": 17},
    22: {"channel": 1, "address": 32},
    23: {"channel": 1, "address": 26},
    24: {"channel": 1, "address": 24},
    25: {"channel": 1, "address": 23},
    26: {"channel": 1, "address": 22},



    27: {"channel": 0, "address": 1},
    28: {"channel": 0, "address": 24},
    29: {"channel": 0, "address": 14},
    30: {"channel": 0, "address": 19},
    31: {"channel": 0, "address": 11},
    32: {"channel": 0, "address": 20},
    33: {"channel": 0, "address": 12},
    34: {"channel": 0, "address": 8}, 
    35: {"channel": 0, "address": 22},
    36: {"channel": 0, "address": 17},
    37: {"channel": 0, "address": 23},
    38: {"channel": 0, "address": 18},
    39: {"channel": 0, "address": 21},
    40: {"channel": 0, "address": 15},
    41: {"channel": 0, "address": 3},
    42: {"channel": 0, "address": 16},
    43: {"channel": 0, "address": 13},

    44: {"channel": 2, "address": 3},
    45: {"channel": 2, "address": 4},
    46: {"channel": 2, "address": 2},
    47: {"channel": 2, "address": 8},
    48: {"channel": 2, "address": 15},
    49: {"channel": 2, "address": 24},
    50: {"channel": 2, "address": 9},
    51: {"channel": 2, "address": 10},
    52: {"channel": 2, "address": 1},
    53: {"channel": 2, "address": 7},
    54: {"channel": 2, "address": 14},
    55: {"channel": 2, "address": 23},
    56: {"channel": 2, "address": 11},
    57: {"channel": 2, "address": 6},
    58: {"channel": 2, "address": 22},
    59: {"channel": 2, "address": 12},
    60: {"channel": 2, "address": 5},
    61: {"channel": 2, "address": 21},
    62: {"channel": 2, "address": 13},
    63: {"channel": 2, "address": 16},
    64: {"channel": 2, "address": 20},

    65: {"channel": 2, "address": 41},
    66: {"channel": 2, "address": 42},
    67: {"channel": 2, "address": 43},
    68: {"channel": 2, "address": 44},
    69: {"channel": 2, "address": 45},
    70: {"channel": 2, "address": 46},
    71: {"channel": 2, "address": 47},
    72: {"channel": 2, "address": 48},
    
    73: {"channel": 2, "address": 49},
    74: {"channel": 2, "address": 50},
    75: {"channel": 2, "address": 51},
    76: {"channel": 2, "address": 52},
    77: {"channel": 2, "address": 53},
    78: {"channel": 2, "address": 54},
    79: {"channel": 2, "address": 55},
    80: {"channel": 2, "address": 56},

    81: {"channel": 2, "address": 64},
    82: {"channel": 2, "address": 63},
    83: {"channel": 2, "address": 62},
    84: {"channel": 2, "address": 61},
    85: {"channel": 2, "address": 60},
}

def openLock(publicAddress):
    # Prüfen, ob die Adresse im Mapping existiert
    if publicAddress in mapping:
        # Daten aus dem Dictionary holen
        channel = mapping[publicAddress]["channel"]
        address = mapping[publicAddress]["address"]
        
        # Den Request mit den gemappten Werten senden
        try:
            url = f"http://10.10.10.4/lock/open?channel={channel}&address={address}"
            response = requests.get(url)
            print(f"Öffne Schloss {publicAddress} (Ch: {channel}, Addr: {address})")
            print(f"Status: {response.status_code}, Antwort: {response.content}")
        except Exception as e:
            print(f"Fehler bei der Anfrage: {e}")
    else:
        print(f"Fehler: PublicAddress {publicAddress} nicht im Mapping gefunden!")

def stateLock(publicAddress):
    # Prüfen, ob die Adresse im Mapping existiert
    if publicAddress in mapping:
        # Daten aus dem Dictionary holen
        channel = mapping[publicAddress]["channel"]
        address = mapping[publicAddress]["address"]
        
        # Den Request mit den gemappten Werten senden
        try:
            url = f"http://10.10.10.4/lock/state?channel={channel}&address={address}"
            response = requests.get(url)
            print(f"Öffne Schloss {publicAddress} (Ch: {channel}, Addr: {address})")
            print(f"Status: {response.status_code}, Antwort: {response.content}")
        except Exception as e:
            print(f"Fehler bei der Anfrage: {e}")
    else:
        print(f"Fehler: PublicAddress {publicAddress} nicht im Mapping gefunden!")

# --- Terminal-Eingabe-Schleife ---
print("--- Schloss-Steuerung aktiv ---")
print("Gib eine Nummer (z.B. 27) ein oder 'q' zum Beenden.")

while True:
    eingabe = input("\nSchloss-Nummer: ").strip().lower()
    
    if eingabe in ['q', 'exit', 'quit']:
        print("Programm beendet.")
        break
    
    if eingabe.isdigit():
        stateLock(int(eingabe))
        time.sleep(0.5)
        openLock(int(eingabe))
        time.sleep(0.5)
        stateLock(int(eingabe))
    else:
        print("Bitte gib eine gültige Zahl ein.")

# 34 - 30