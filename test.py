import cv2

print("Camera connect karne ki koshish kar raha hai...")

# cv2.CAP_DSHOW use karna zaroori hai is error ke liye
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Camera index 0 par nahi chala, index 1 try kar rahe hain...")
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Camera bilkul detect nahi ho raha.")
    exit()

print("✅ Camera Connect Ho Gaya! Band karne ke liye 'q' dabayein.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
        break

cap.release()
cv2.destroyAllWindows()