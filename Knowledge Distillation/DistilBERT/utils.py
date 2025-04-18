# -*- coding: utf-8 -*-
"""utils.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1k7o8duMhzkcMjdEMn2LeaOZ6amPLp1_X
"""

import torch
import random

def dynamic_masking(input_ids, mask_token_id=103, vocab_size=30522, mlm_probability=0.15):
    labels = input_ids.clone()
    probability_matrix = torch.full(labels.shape, mlm_probability)
    masked_indices = torch.bernoulli(probability_matrix).bool()
    labels[~masked_indices] = -100

    mask_token_mask = torch.bernoulli(torch.full(labels.shape, 0.8)).bool() & masked_indices
    input_ids[mask_token_mask] = mask_token_id

    random_token_mask = torch.bernoulli(torch.full(labels.shape, 0.5)).bool() & masked_indices & ~mask_token_mask
    random_tokens = torch.randint(low=0, high=vocab_size, size=labels.shape, dtype=torch.long)
    input_ids[random_token_mask] = random_tokens[random_token_mask]

    return input_ids, labels