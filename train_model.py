import os
import pandas as pd
import joblib
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

os.makedirs("models", exist_ok=True)

# Load dataset
df = pd.read_csv("dataset/mails.csv")  # Changed from emails.csv to mails.csv

# Fill missing text
df["text"] = df["text"].fillna("")

# Clean labels - strip whitespace
df["label"] = df["label"].astype(str).str.strip()

print("=" * 50)
print("ORIGINAL LABELS FOUND:")
print(df["label"].value_counts())
print("=" * 50)

# Convert labels to binary (0 = Legitimate/Ham/Safe, 1 = Phishing/Spam)
label_mapping = {
    "Legitimate Mail": 0,
    "Phishing Mail": 1,
    "safe": 0,
    "phishing": 1,
    "ham": 0,
    "spam": 1
}

df["label"] = df["label"].map(label_mapping)

# Show invalid rows
invalid_rows = df[df["label"].isna()]
print(f"\nInvalid/unmapped rows: {len(invalid_rows)}")

if len(invalid_rows) > 0:
    print("Sample of unmapped labels:")
    print(invalid_rows["label"].head())

# Remove invalid rows
df = df.dropna(subset=["label"])

# Convert label type to int
df["label"] = df["label"].astype(int)

print("\n" + "=" * 50)
print("FINAL DATASET STATISTICS:")
print(f"Total samples: {len(df)}")
print(f"Legitimate (0): {(df['label'] == 0).sum()}")
print(f"Phishing (1): {(df['label'] == 1).sum()}")
print(f"Phishing percentage: {(df['label'] == 1).mean() * 100:.2f}%")
print("=" * 50)

# Optional: Text preprocessing function
def preprocess_text(text):
    """Basic text preprocessing"""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    # Remove numbers (optional - can be kept for some datasets)
    # text = re.sub(r'\d+', '', text)
    return text

# Apply preprocessing
df["clean_text"] = df["text"].apply(preprocess_text)

# Train vectorizer and model
print("\nTraining model...")
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=5000,  # Limit features for better performance
    ngram_range=(1, 2),  # Use both unigrams and bigrams
    min_df=2,  # Ignore terms that appear in less than 2 documents
    max_df=0.95  # Ignore terms that appear in more than 95% of documents
)

X = vectorizer.fit_transform(df["clean_text"])
y = df["label"]

# Split data for validation
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training samples: {X_train.shape[0]}")
print(f"Test samples: {X_test.shape[0]}")
print(f"Features: {X_train.shape[1]}")

# Train model with class balancing
model = LogisticRegression(
    max_iter=1000,
    class_weight='balanced',  # Handle imbalanced classes
    C=1.0,  # Regularization strength
    solver='liblinear'  # Good for smaller datasets
)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 50)
print("MODEL EVALUATION ON TEST SET:")
print(f"Accuracy: {accuracy * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Legitimate', 'Phishing']))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("=" * 50)

# Save model and vectorizer
joblib.dump(model, "models/model.pkl")
joblib.dump(vectorizer, "models/vectorizer.pkl")

print("\n✅ Model and vectorizer saved successfully to 'models/' directory!")

# Optional: Test with sample phishing email
print("\n" + "=" * 50)
print("QUICK TEST WITH SAMPLE PHISHING EMAIL:")
sample_phishing = "Congratulations! You have won a free iPhone! Click here to claim your prize now!"
sample_processed = preprocess_text(sample_phishing)
sample_vectorized = vectorizer.transform([sample_processed])
prediction = model.predict(sample_vectorized)[0]
confidence = max(model.predict_proba(sample_vectorized)[0]) * 100
print(f"Text: {sample_phishing}")
print(f"Prediction: {'PHISHING' if prediction == 1 else 'LEGITIMATE'}")
print(f"Confidence: {confidence:.2f}%")
print("=" * 50)