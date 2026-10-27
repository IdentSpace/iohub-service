import cv2
import imutils
import numpy as np
import pytesseract # Du musst Tesseract auf deinem System installiert haben

# 1. Bild laden und vorbereiten
image = cv2.imread('temp_snapshot.jpg')
image = imutils.resize(image, width=500)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 2. Rauschen filtern und Kanten finden
gray = cv2.bilateralFilter(gray, 11, 17, 17) # Erhält Kanten, glättet Flächen
edged = cv2.Canny(gray, 30, 200) # Canny-Algorithmus zur Kantendetektion

# 3. Konturen suchen
cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]

# screenCnt = None
# for c in cnts:
#     # Kontur annähern
#     peri = cv2.arcLength(c, True)
#     approx = cv2.approxPolyDP(c, 0.018 * peri, True)
    
#     # Wenn die Kontur 4 Eckpunkte hat, haben wir unser Kennzeichen
#     if len(approx) == 4:
#         screenCnt = approx
#         break

# # 4. Maskieren und OCR
# mask = np.zeros(gray.shape, np.uint8)
# new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
# new_image = cv2.bitwise_and(image, image, mask=mask)

# cv2.imwrite('processed_plate.jpg', image)

# Jetzt könnte man 'new_image' an Tesseract übergeben
text = pytesseract.image_to_string(image, config='--psm 11')

# print("Erkanntes Kennzeichen:", text.strip())