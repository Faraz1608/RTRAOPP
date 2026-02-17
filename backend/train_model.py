import pandas as pd
import numpy as np
import torch
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset
import os
import shutil

# 1. Configuration
MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
DATA_FILE = "dataset.csv"
MODEL_DIR = "models/risk_bert"

# 2. Prepare Dataset Class
class RiskDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

def train():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run 'python build_dataset.py' first.")
        return

    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    df = df.dropna()

    # Map categories to IDs
    labels = df['category'].unique().tolist()
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for i, label in enumerate(labels)}
    print(f"Original dataset size: {len(df)}")
    # Limit to 2000 samples for faster training (CPU)
    if len(df) > 2000:
        print("Downsampling to 2000 samples for faster CPU training...")
        df = df.sample(n=2000, random_state=42)
    
    print(f"Training on {len(df)} samples.")

    # Map categories to IDs

    df['label'] = df['category'].map(label2id)

    # Split Data
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        df['text'].tolist(), df['label'].tolist(), test_size=0.2, random_state=42
    )

    # Tokenize
    # Tokenize
    print("Tokenizing data...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=128)

    train_dataset = RiskDataset(train_encodings, train_labels)
    val_dataset = RiskDataset(val_encodings, val_labels)

    # Model
    print("Initializing model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(labels), id2label=id2label, label2id=label2id
    )

    # Training Arguments
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    # Train
    print("Starting training...")
    trainer.train()

    # Save Model
    print(f"Saving model to {MODEL_DIR}...")
    if os.path.exists(MODEL_DIR):
        shutil.rmtree(MODEL_DIR)
    
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    print("Training complete and model saved!")

if __name__ == "__main__":
    train()
