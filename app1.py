from flask import Flask, render_template, request, jsonify, redirect, url_for
import joblib
import re
import os
from PIL import Image
import pytesseract

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# Tesseract path for Windows (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load models with error handling
try:
    model = joblib.load("models/model.pkl")
    vectorizer = joblib.load("models/vectorizer.pkl")
    print("✅ Models loaded successfully!")
except FileNotFoundError:
    print("❌ Models not found! Please run train_model.py first")
    model = None
    vectorizer = None

def preprocess_text(text):
    """Same preprocessing used during training"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    return text

def scan_text(text):
    """Analyze email text for phishing indicators"""
    if not text.strip():
        return 0, 0, ["No text found for analysis"]
    
    # Apply same preprocessing as training
    clean_text = preprocess_text(text)
    
    if model is None or vectorizer is None:
        return 0, 0, ["Model not loaded. Please train the model first."]
    
    X = vectorizer.transform([clean_text])
    prediction = model.predict(X)[0]
    confidence = int(max(model.predict_proba(X)[0]) * 100)
    
    reasons = []
    
    # Suspicious keywords with severity weights
    suspicious_words = {
        "urgent": 15, "verify": 20, "password": 25, "bank": 20, "login": 15,
        "free": 10, "gift": 10, "winner": 30, "kyc": 25, "blocked": 20,
        "lottery": 30, "account": 15, "security": 15, "update": 10,
        "confirm": 20, "alert": 15, "immediately": 20, "expired": 15,
        "congratulations": 25, "prize": 30, "claim": 20, "cash": 25,
        "reward": 20, "bonus": 15, "click": 10, "subscribe": 10,
        "suspended": 25, "unauthorized": 20, "limited": 15, "restricted": 15
    }
    
    for word, weight in suspicious_words.items():
        if word in text.lower():
            reasons.append(f"Suspicious keyword detected: '{word}' (severity: {weight}%)")
    
    # Additional phishing patterns
    phishing_patterns = [
        ("verify your account", "Account verification request detected", 25),
        ("click here", "Suspicious link prompt detected", 20),
        ("dear customer", "Generic greeting often used in phishing", 10),
        ("you have won", "Prize/winning claim detected", 30),
        ("call now", "Urgent call to action detected", 20),
        ("confirm your", "Suspicious confirmation request detected", 25),
        ("account suspended", "Account suspension threat detected", 30),
        ("update your", "Fake update request detected", 20),
        ("security alert", "Security alert phishing attempt", 28),
        ("limited time", "Urgency tactic detected", 15)
    ]
    
    for pattern, message, weight in phishing_patterns:
        if pattern in text.lower():
            reasons.append(f"{message} (severity: {weight}%)")
    
    return prediction, confidence, reasons

@app.route("/")
def home():
    """Home page route"""
    return render_template("Index.html")

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Analysis route - handles both GET and POST"""
    
    # Handle GET requests - redirect to home
    if request.method == "GET":
        return redirect(url_for("home"))
    
    # Handle POST requests
    input_type = request.form.get("input_type")
    email_text = request.form.get("email_text", "")
    
    final_score = 0
    reasons = []
    prediction_text = "SAFE"
    extracted_text = ""
    
    if input_type == "email":
        prediction, confidence, text_reasons = scan_text(email_text)
        
        final_score = confidence if prediction == 1 else 100 - confidence
        prediction_text = "PHISHING" if prediction == 1 else "SAFE"
        reasons.extend(text_reasons)
        
        if prediction == 1:
            reasons.append(f"🤖 AI Model confidence: {confidence}% that this is phishing")
        else:
            reasons.append(f"🤖 AI Model confidence: {confidence}% that this is legitimate")
    
    elif input_type == "screenshot":
        file = request.files.get("screenshot")
        
        if file and file.filename:
            os.makedirs("uploads", exist_ok=True)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            
            # Extract text from screenshot
            try:
                extracted_text = pytesseract.image_to_string(Image.open(filepath))
                
                if extracted_text.strip():
                    prediction, confidence, text_reasons = scan_text(extracted_text)
                    
                    final_score = confidence if prediction == 1 else 100 - confidence
                    prediction_text = "PHISHING" if prediction == 1 else "SAFE"
                    
                    reasons.append("📸 Text extracted from screenshot using OCR technology")
                    reasons.extend(text_reasons)
                else:
                    prediction_text = "INCONCLUSIVE"
                    reasons.append("No readable text found in the screenshot")
                    final_score = 0
            except Exception as e:
                prediction_text = "ERROR"
                reasons.append(f"Error processing screenshot: {str(e)}")
                final_score = 0
        else:
            prediction_text = "ERROR"
            reasons.append("No screenshot file uploaded")
            final_score = 0
    
    else:
        prediction_text = "ERROR"
        reasons.append("Invalid input type selected")
        final_score = 0
    
    # Determine risk level
    if final_score >= 70:
        risk_level = "HIGH"
        risk_color = "danger"
    elif final_score >= 40:
        risk_level = "MEDIUM"
        risk_color = "medium"
    else:
        risk_level = "LOW"
        risk_color = "safe"
    
    return render_template(
        "Result.html",
        prediction=prediction_text,
        score=final_score,
        risk_level=risk_level,
        risk_color=risk_color,
        reasons=reasons,
        extracted_text=extracted_text,
        input_type=input_type
    )

# Test route to verify server is running
@app.route("/test")
def test():
    """Test route to check if server is running"""
    return jsonify({"status": "success", "message": "PHISH-Detector is running!"})

if __name__ == "__main__":
    # Run on all available IPs, port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)