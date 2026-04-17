from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

os.makedirs("models/intent_model", exist_ok=True)

print("📥 Downloading Bangla BERT model...")
print("⏳ This may take 5-10 minutes (model size ~660MB)...")

tokenizer = AutoTokenizer.from_pretrained("sagorsarker/bangla-bert-base")
model = AutoModelForSequenceClassification.from_pretrained(
    "sagorsarker/bangla-bert-base",
    num_labels=8
)

model.save_pretrained("models/intent_model")
tokenizer.save_pretrained("models/intent_model")

print("\n✅ Model downloaded and saved successfully!")
print(f"📁 Location: models/intent_model/")