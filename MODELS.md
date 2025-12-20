# Models Used in HR Conversational Agent

This document describes the Hugging Face models used for each task.

## Model Architecture

### 1. Intent Detection
- **Model**: `facebook/bart-large-mnli` (primary) or `typeform/distilbert-base-uncased-mnli` (fallback)
- **Type**: Zero-shot classification
- **Why**: Works without fine-tuning, can classify into any intent categories
- **Free**: Yes
- **Location**: `intent/intent_router.py`

### 2. Slot Selection
- **Model**: `distilbert-base-uncased`
- **Type**: Sequence classification (binary per slot)
- **Why**: Lightweight, fast, reliable for determining if utterance can answer a slot question
- **Free**: Yes
- **Location**: `slots/slot_selector.py`

### 3. Slot Extraction
- **Model**: `distilbert-base-uncased-distilled-squad`
- **Type**: Question-answering (span extraction)
- **Why**: Pre-trained on SQuAD, excellent for extracting answers from text
- **Free**: Yes
- **Location**: `slots/slot_extractor.py`

## Model Loading

All models:
- Load automatically on initialization
- Fall back to rule-based methods if loading fails
- Print status messages when loaded successfully
- Use CPU by default (GPU if available)

## First Run

On first run, models will be downloaded from Hugging Face:
- This may take a few minutes depending on internet speed
- Models are cached locally after first download
- Subsequent runs will be faster

## Model Sizes

- BART-large-MNLI: ~1.6 GB
- DistilBERT-base: ~250 MB
- DistilBERT-SQuAD: ~250 MB

Total: ~2.1 GB (one-time download)

## Troubleshooting

If models fail to load:
1. Check internet connection (needed for first download)
2. Ensure sufficient disk space (~3 GB recommended)
3. Check that transformers library is up to date: `pip install --upgrade transformers`
4. System will automatically fall back to rule-based methods

