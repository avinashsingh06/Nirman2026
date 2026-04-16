import cv2

cap = cv2.VideoCapture(0, cv2.CAP_MSMF)

# Force resolution (VERY IMPORTANT)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while True:
    ret, frame = cap.read()

    if not ret or frame is None:
        print("Frame not received")
        continue

    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()