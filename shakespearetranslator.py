# -*- coding: utf-8 -*-
"""ShakespeareTranslator.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Lk9a-SIf-mZGanqc28IyLPCeQOjPPDhI
"""

!pip install transformers datasets torch spacy
!python -m spacy download en_core_web_sm

import pandas as pd
from datasets import Dataset

# Load dataset
file_path = "/content/modern-to-shakespeare.csv"
df = pd.read_csv(file_path)

# Ensure dataset formatting is correct
df["text"] = df.apply(lambda row: f"Modern: {row['modern']}\nShakespearean: {row['shakespearean']} [END]", axis=1)
dataset = Dataset.from_dict({"text": df["text"].tolist()})

# ✅ Split dataset into train and eval
dataset_split = dataset.train_test_split(test_size=0.1)
train_dataset = dataset_split["train"]
eval_dataset = dataset_split["test"]

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load model
model_name = "MBL2/gpt2-old-english"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Move model to GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Tokenize dataset
def tokenize_function(examples):
    tokens = tokenizer(examples["text"], padding=True, truncation=True, max_length=128)
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

# Tokenize both train and eval sets
tokenized_train = train_dataset.map(tokenize_function, batched=True)
tokenized_eval = eval_dataset.map(tokenize_function, batched=True)

from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

# Data collator for causal language modeling
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer, mlm=False
)

# Define training arguments
training_args = TrainingArguments(
    output_dir="./shakespeare-gpt2",
    evaluation_strategy="epoch",
    logging_strategy="epoch",
    save_strategy="epoch",
    per_device_train_batch_size=4,
    num_train_epochs=5,
    learning_rate=5e-5,
    weight_decay=0.01,
    save_total_limit=2,
    report_to="none"
)


# Initialize Trainer with both train and eval datasets
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_eval,
    data_collator=data_collator,
)

# Fine-tune the model
trainer.train()

def generate_shakespearean_text(modern_text):
    # Instruction-based prompt
    prompt = f"Translate the following Modern English sentence to Shakespearean English:\nModern: {modern_text}\nShakespearean:"

    # Tokenize prompt
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    # Generate Shakespearean text
    output = model.generate(
    **inputs,
    max_length=len(inputs["input_ids"][0]) + 20,
    repetition_penalty=1.3,
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
    )


    # Decode response
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)

    # Extract only the translated portion
    shakespearean_response = generated_text.split("Shakespearean:")[-1].split("\n")[0].strip()
    shakespearean_response = shakespearean_response.replace("[END]", "").strip()

    return shakespearean_response

# Ask user for modern English sentence
while True:
    user_input = input("\nEnter a modern English sentence (or type 'exit' to quit): ").strip()

    # Exit condition
    if user_input.lower() == "exit":
        print("Exiting translator. Fare thee well!")
        break

    # Prevent empty input
    if not user_input:
        print("Please enter a sentence.")
        continue

    # Generate translation
    shakespearean_translation = generate_shakespearean_text(user_input)
    print(f"Shakespearean: {shakespearean_translation}\n")