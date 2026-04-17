from flask import Flask, render_template, Response, request, jsonify
import cv2
import time
from collections import Counter
from blockchain import Blockchain
import requests
import numpy as np

app = Flask(__name__)
blockchain = Blockchain()

# 🔥 API KEY (Security Note: Hackathon ke baad isse environment variable mein daal dena)
OPENROUTER_API_KEY = "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"

# 🔥 CAMERA SETUP - Retry Logic ke saath
# 🔥 CAMERA SETUP - BULLETPROOF VERSION
def start_camera():
    # CAP_DSHOW ke bajaye default (0) try karo, ya CAP_MSMF
    cap = cv2.VideoCapture(0) 
    
    # Agar default nahi chala toh MSMF (Windows Media Foundation) try karo
    if not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
    
    # Format settings ko thoda "loose" rakho taaki camera sync ho sake
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Buffer size 1 rakho taaki "Purana/Corrupted" data na dikhe
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    return cap

camera = start_camera()
time.sleep(1.0) # Camera ko ready hone ka time do

# 🔥 GENERATE FRAMES
def generate_frames():
    global last_emotion, stable_emotion, emotion_lock_time, last_saved_emotion, last_saved_time, points, camera, daily_points, last_reset_date

    while True:
        # 1. Camera Liveness Check
        if not camera or not camera.isOpened():
            camera = start_camera()
            time.sleep(1.0)

        success, frame = camera.read()
        
        if not success:
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Waking up Camera...", (160, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            continue

        # 2. Image Pre-processing (Display ke liye thoda blur, noise hatane ke liye)
        display_frame = cv2.GaussianBlur(frame, (3, 3), 0)
        display_frame = cv2.resize(display_frame, (640, 480))
        display_frame = cv2.flip(display_frame, 1)
        
        # Detection ke liye sharp gray image
        gray = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)

        # 3. Sensitive Face Detection
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        detected_emotion = last_emotion

       # 4. ROI-Based Emotion Detection Logic (Anti-Freeze Version)
        if len(faces) > 0:
            (x, y, w, h) = faces[0]

            if w >= 60 and h >= 60:
                face_gray = gray[y:y+h, x:x+w]
                
                # --- 🔥 STEP 1: IMAGE KO CLEAR KARO (CLAHE) ---
                # Isse andhere mein bhi features (Angry/Sad) saaf dikhenge
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                face_gray = clahe.apply(face_gray)

                # Face Split (Top and Bottom)
                top_half = face_gray[0:int(h/2), 0:w]
                bottom_half = face_gray[int(h/2):h, 0:w]

                # --- 🔥 STEP 2: SENSITIVITY FIX ---
                # Eyes detection ko super sensitive kar diya (minNeighbors=2)
                eyes = eye_cascade.detectMultiScale(top_half, 1.1, 2, minSize=(15, 15))
                # Smile ko strict rakha hai taaki false Happy na aaye
                smiles = smile_cascade.detectMultiScale(bottom_half, 1.7, 22, minSize=(25, 25))

                eye_count = len(eyes)
                smile_count = len(smiles)
                avg_brightness = face_gray.mean()

                detected_emotion = "neutral" 

                # --- 🔥 STEP 3: IMPROVED LOGIC FOR ANGRY & SAD ---
                
                # 1. Sabse pehle Happy check karo
                if smile_count > 0:
                    detected_emotion = "happy"
                
                # 2. Surprise (Aankhein phati ki phati)
                elif eye_count >= 3:
                    detected_emotion = "surprise"
                
                # 3. Angry: Sirf tab jab brightness bahut zyada ho aur aankhein narrow ho
                elif eye_count <= 1 and avg_brightness > 130: 
                    detected_emotion = "angry"
                
                # 4. Sad: Sirf tab jab light sach mein kam ho (85 se niche)
                elif smile_count == 0 and avg_brightness < 85: 
                    detected_emotion = "sad"
                
                # 5. NEUTRAL: Agar upar ka kuch bhi match nahi hua, toh pakka Neutral hai
                else:
                    detected_emotion = "neutral"

                # Buffer update and other logic follows...

            # 5. Buffer & Smoothing
            emotion_buffer.append(detected_emotion)
            if len(emotion_buffer) > 10:
                emotion_buffer.pop(0)

            new_emotion = get_stable_emotion()
            current_time = time.time()
            
            if current_time - emotion_lock_time > 0.5: # Lock duration kam kiya fast response ke liye
                if new_emotion != stable_emotion:
                    stable_emotion = new_emotion
                    emotion_lock_time = current_time

            last_emotion = stable_emotion

            # 6. Point System & Blockchain
            award_points(stable_emotion)
            if (stable_emotion != last_saved_emotion) or (current_time - last_saved_time > 5):
                blockchain.add_block(stable_emotion)
                emotion_history.append(stable_emotion)
                last_saved_emotion = stable_emotion
                last_saved_time = current_time

            # 7. Rendering UI on Frame
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 0, 255), 2)
            cv2.putText(display_frame, stable_emotion.upper(), (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)

        else:
            cv2.putText(display_frame, last_emotion.upper(), (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # 8. Encoding and Yielding
        ret, buffer = cv2.imencode('.jpg', display_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 🔥 CASCADES
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# 🔥 GLOBALS
points = 0
daily_points = 0
achievements = []
last_reset_date = time.strftime("%Y-%m-%d")

visit_streak = 0
last_visit_date = ""
last_streak_increment_time = time.time()
STREAK_INCREMENT_INTERVAL = 86400  # 24 hours in seconds

last_emotion = "neutral"
last_manual_emotion_time = 0
MANUAL_EMOTION_COOLDOWN = 86400 
emotion_buffer = []
stable_emotion = "neutral"

last_points_time = 0
POINT_COOLDOWN = 3
camera_active = False

last_saved_time = 0
last_saved_emotion = ""

emotion_history = []
emotion_lock_time = 0
LOCK_DURATION = 2

suggestions = {
    "happy": "Keep smiling 😄",
    "sad": "Take a break 💙",
    "angry": "Relax and breathe 😌",
    "neutral": "Stay focused 💡",
    "surprise": "Wow moment 😲"
}

def get_stable_emotion():
    if len(emotion_buffer) < 5:
        return last_emotion
    
    count = Counter(emotion_buffer)
    most_common, freq = count.most_common(1)[0]

    if freq >= len(emotion_buffer) * 0.6:
        return most_common
    return last_emotion

def award_points(current_emotion): # 🔥 Ab ye emotion maangega
    global points, last_points_time
    current_time = time.time()
    
    # 3 second ka wait (Cooldown)
    if current_time - last_points_time > POINT_COOLDOWN:
        add_map = {
            "happy": 10,
            "surprise": 7,
            "neutral": 5,
            "sad": 3,
            "angry": 2
        }
        points += add_map.get(current_emotion, 1)
        last_points_time = current_time
        check_achievements() # Points badhne par badge check

'''def generate_frames():
    global last_emotion, stable_emotion, emotion_lock_time, last_saved_emotion, last_saved_time, points, camera, daily_points, last_reset_date

    # Make sure camera is opened
    if not camera.isOpened():
        camera = cv2.VideoCapture(0, cv2.CAP_MSMF)
    
    print("Camera feed started...")

    while True:
        # 1. Daily points reset logic
        today = time.strftime("%Y-%m-%d")
        if today != last_reset_date:
            daily_points = 0
            last_reset_date = today

        # 2. Read frame
        success, frame = camera.read()
        if not success:
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Camera Feed Corrupted", (100, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            continue

        # 3. Image Pre-processing
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.2, 6)
        detected_emotion = last_emotion

        # 4. Emotion Detection Logic
        if len(faces) > 0:
            (x, y, w, h) = faces[0]

            if w >= 80 and h >= 80:
                face_gray = gray[y:y+h, x:x+w]
                face_gray = cv2.equalizeHist(face_gray)
                face_gray = cv2.GaussianBlur(face_gray, (5, 5), 0)

                # DETECTION (STRONG)
                smiles = smile_cascade.detectMultiScale(face_gray, scaleFactor=1.3, minNeighbors=15, minSize=(30, 30))
                eyes = eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=4, minSize=(15, 15))

                brightness = face_gray.mean()

                # DEBUG (Green box around smiles)
                for (sx, sy, sw, sh) in smiles:
                    cv2.rectangle(frame, (x+sx, y+sy), (x+sx+sw, y+sy+sh), (0, 255, 0), 2)

                # FINAL LOGIC
                has_strong_smile = len(smiles) >= 2 
                has_any_smile = len(smiles) >= 1
                eye_count = len(eyes)

                if has_strong_smile:
                    detected_emotion = "happy"
                elif not has_any_smile and eye_count == 0 and brightness > 95:
                    detected_emotion = "angry"
                elif not has_any_smile and eye_count >= 2 and brightness > 120:
                    detected_emotion = "surprise"
                elif not has_any_smile and brightness < 110:
                    detected_emotion = "sad"
                else:
                    detected_emotion = "neutral"

            # 5. Buffer & Smoothing
            emotion_buffer.append(detected_emotion)
            if len(emotion_buffer) > 12:
                emotion_buffer.pop(0)

            new_emotion = get_stable_emotion()

            current_time = time.time()
            if current_time - emotion_lock_time > LOCK_DURATION:
                if new_emotion != stable_emotion:
                    stable_emotion = new_emotion
                    emotion_lock_time = current_time

            last_emotion = stable_emotion

            # 6. Smart Point System & Blockchain Save
            award_points()

            if (stable_emotion != last_saved_emotion) or (current_time - last_saved_time > 5):
                blockchain.add_block(stable_emotion)
                emotion_history.append(stable_emotion)
                last_saved_emotion = stable_emotion
                last_saved_time = current_time

            # 7. Drawing Box on Face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 255), 2)
            cv2.putText(frame, stable_emotion.upper(), (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)

        else:
            # If no face is detected
            cv2.putText(frame, last_emotion.upper(), (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # 8. Encoding and Yielding
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')'''

def check_achievements():
    global achievements, points
    if points >= 50 and "Beginner 🟢" not in achievements:
        achievements.append("Beginner 🟢")
    if points >= 100 and "Explorer 🔵" not in achievements:
        achievements.append("Explorer 🔵")
    if points >= 200 and "Master 🔥" not in achievements:
        achievements.append("Master 🔥")

# 🔥 ROUTES
@app.route('/')
def index():
    global visit_streak, last_visit_date
    today = time.strftime("%Y-%m-%d")
    if today != last_visit_date:
        visit_streak += 1
        last_visit_date = today
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_data')
def get_data():
    global visit_streak, last_streak_increment_time
    
    current_time = time.time()
    if current_time - last_streak_increment_time >= STREAK_INCREMENT_INTERVAL:
        visit_streak += 1
        last_streak_increment_time = current_time

    return jsonify({
        "points": points,
        "streak": visit_streak,
        "emotions": blockchain.get_emotions(),
        "suggestion": suggestions.get(last_emotion, ""),
        "achievements": achievements,
        "current_emotion": last_emotion
    })

@app.route('/analytics_data')
def analytics_data():
    range_type = request.args.get('range', 'daily')
    count = Counter(emotion_history)
    if range_type == "daily":
        data = list(count.values())[-5:]
    elif range_type == "weekly":
        data = list(count.values())[-7:]
    elif range_type == "monthly":
        data = list(count.values())[-30:]
    else:
        data = list(count.values())

    return jsonify({
        "labels": list(count.keys()),
        "values": data
    })

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    data = request.json
    user_msg = data.get("message", "")
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI"},
                    {"role": "user", "content": user_msg}
                ]
            }
        )
        result = response.json()
        reply = result["choices"][0]["message"]["content"] 
        return jsonify({"reply": reply})
    except:
        return jsonify({"reply": "AI error 😓"})

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/music')
def music():
    return render_template('music.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/set_camera_status', methods=['POST'])
def set_camera_status():
    global camera_active
    data = request.get_json(silent=True) or {}
    camera_active = bool(data.get('active', False))
    return jsonify({"status": "ok", "camera_active": camera_active})

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/submit_emotion', methods=['POST'])
def submit_emotion():
    global last_manual_emotion_time
    data = request.get_json(silent=True) or {}
    emotion = data.get('emotion', 'neutral')
    current_time = time.time()
    time_remaining = max(0, MANUAL_EMOTION_COOLDOWN - (current_time - last_manual_emotion_time))
    
    if current_time - last_manual_emotion_time < MANUAL_EMOTION_COOLDOWN:
        return jsonify({
            "status": "cooldown",
            "message": "Please wait before submitting another emotion",
            "time_remaining": int(time_remaining)
        }), 429
    
    last_manual_emotion_time = current_time
    blockchain.add_block(emotion)
    emotion_history.append(emotion)
    return jsonify({"status": "ok", "message": "Thanks for sharing!"})

@app.route('/emotion_cooldown')
def emotion_cooldown():
    current_time = time.time()
    time_remaining = max(0, MANUAL_EMOTION_COOLDOWN - (current_time - last_manual_emotion_time))
    return jsonify({
        "time_remaining": int(time_remaining),
        "available": time_remaining == 0
    })

@app.route('/add_points', methods=['POST'])
def add_points_route():
    global points
    points += 10
    check_achievements()
    return jsonify({"status": "ok", "points": points})

if __name__ == "__main__":
    app.run(debug=True , port='5001')
