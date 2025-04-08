# -*- coding: utf-8 -*-
"""train.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1k7o8duMhzkcMjdEMn2LeaOZ6amPLp1_X
"""

from transformers import BertTokenizer, BertForMaskedLM
from torch.utils.data import DataLoader
from datasets import load_dataset
import torch
from loss import triple_loss
from model_init import build_student_from_teacher
from utils import dynamic_masking

batch_size = 8
accumulation_steps = 4
epochs = 3
max_length = 128
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
teacher = BertForMaskedLM.from_pretrained("bert-base-uncased").to(device)
student_bert = student_Architecture(teacher.bert, num_student_layers=6).to(device)
student = BertForMaskedLM(config=student_bert.config)
student.bert = student_bert
student.to(device)

dataset = load_dataset("wikitext", "wikitext-2-raw-v1", split="train")

def encode(example):
    return tokenizer(example["text"], truncation=True, padding="max_length", max_length=max_length)

tokenized_dataset = dataset.map(encode, batched=True).remove_columns(["text"])

def collate_fn(batch):
    input_ids = torch.tensor([x["input_ids"] for x in batch])
    attention_mask = torch.tensor([x["attention_mask"] for x in batch])
    masked_input_ids, labels = dynamic_masking(input_ids)
    return {
        "input_ids": masked_input_ids,
        "attention_mask": attention_mask,
        "labels": labels
    }

dataloader = DataLoader(tokenized_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)

optimizer = torch.optim.AdamW(student.parameters(), lr=5e-5)
student.train()
optimizer.zero_grad()

for epoch in range(epochs):
    for step, batch in enumerate(dataloader):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        with torch.no_grad():
            t_out = teacher(input_ids, attention_mask=attention_mask, output_hidden_states=True)

        s_out = student(input_ids, attention_mask=attention_mask, output_hidden_states=True)

        loss, loss_ce, loss_mlm, loss_cos = triple_loss(
            s_logits=s_out.logits,
            t_logits=t_out.logits,
            s_hidden=s_out.hidden_states[-1],
            t_hidden=t_out.hidden_states[-1],
            mlm_labels=labels
        )

        loss = loss / accumulation_steps
        loss.backward()

        if (step + 1) % accumulation_steps == 0:
            optimizer.step()
            optimizer.zero_grad()

        if step % 100 == 0:
            print(f"[Epoch {epoch}] Step {step} | Loss: {loss.item():.4f} | CE: {loss_ce.item():.4f} | MLM: {loss_mlm.item():.4f} | COS: {loss_cos.item():.4f}")