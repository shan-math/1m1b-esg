# esg_pipeline.py (ML-powered ESG classifier using local FinBERT-ESG)

import os
import re
import hashlib
import warnings
import nltk
import pdfplumber
import pandas as pd
from transformers import BertTokenizer, BertForSequenceClassification, pipeline

warnings.filterwarnings("ignore", category=UserWarning, module="pdfminer")

# Download NLTK sentence tokenizer (only once)
nltk.download("punkt", quiet=True)

# === CONFIG ===
MODEL_PATH = r"D:\esg\models\finbert-esg"   # your local FinBERT-ESG model folder
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EXPLORER_CSV = os.path.join(DATA_DIR, "esg_explorer.csv")
SUMMARY_CSV = os.path.join(DATA_DIR, "esg_summary.csv")
MAX_TOKENS = 512

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ===== Model init (lazy load once) =====
tokenizer = None
model = None
nlp = None

def init_model():
    global tokenizer, model, nlp
    if tokenizer is None or model is None or nlp is None:
        tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
        model = BertForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=4)
        nlp = pipeline("text-classification", model=model, tokenizer=tokenizer, top_k=None)
    return tokenizer, model, nlp

# -----------------------
# Text cleaning & PDF extraction
# -----------------------
def clean_text(t: str) -> str:
    if not isinstance(t, str):
        return ""
    t = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", " ", t)
    t = re.sub(r"-{3,}", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_sentences_from_pdf(pdf_path):
    pages_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for p in pdf.pages:
                try:
                    ptext = p.extract_text()
                    if ptext:
                        pages_text.append(ptext)
                except Exception:
                    continue
    except Exception:
        return []

    if not pages_text:
        return []

    # Remove repeated headers/footers
    line_counts = {}
    for ptext in pages_text:
        for line in ptext.splitlines():
            ln = line.strip()
            if ln:
                line_counts[ln] = line_counts.get(ln, 0) + 1
    repeated_lines = {ln for ln, c in line_counts.items() if c > max(1, len(pages_text)//2)}

    cleaned_pages = []
    for ptext in pages_text:
        lines = []
        for line in ptext.splitlines():
            ln = line.strip()
            if ln and ln not in repeated_lines:
                lines.append(ln)
        cleaned_pages.append(" ".join(lines))

    full_text = clean_text(" ".join(cleaned_pages))
    try:
        sents = nltk.sent_tokenize(full_text)
    except Exception:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if s.strip()]

    final = []
    for s in sents:
        s2 = clean_text(s)
        if len(s2) < 20:
            continue
        if re.match(r'^[^A-Za-z0-9]{10,}$', s2):
            continue
        final.append(s2)
    return final

# -----------------------
# Classification
# -----------------------
def safe_classify(text):
    init_model()
    try:
        tokens = tokenizer.encode(text, truncation=False)
    except Exception:
        text = text[:2000]
        return nlp(text)[0]

    if len(tokens) > MAX_TOKENS:
        tokens = tokens[:510]
        text = tokenizer.decode(tokens, skip_special_tokens=True)
    return nlp(text)[0]   # returns list of label+score

def detect_sentiment(sentence):
    """Simple heuristic sentiment (can be swapped with a model if needed)."""
    s = sentence.lower()
    negatives = ["fined","violation","fraud","corruption","layoff","pollution","strike","lawsuit","penalty","sanction"]
    positives = ["reduced","improved","donated","volunteering","compliance","sustainable","cut","recycling","offset","recovery","renewable","solar","reduction"]
    if any(w in s for w in negatives):
        return "Negative"
    if any(w in s for w in positives):
        return "Positive"
    return "Neutral"

def apply_risk_weight(sentence, score, sentiment):
    if sentiment == "Negative":
        return float(score) * 1.0
    if sentiment == "Positive":
        return -float(score) * 0.5
    return float(score) * 0.2

# -----------------------
# classify sentences for one report
# -----------------------
def classify_sentences_for_report(sentences, company_name, source_filename):
    records = []
    seen_hashes = set()
    for sent in sentences:
        sig = hashlib.sha1((company_name + "|" + source_filename + "|" + sent).encode("utf-8")).hexdigest()
        if sig in seen_hashes:
            continue
        seen_hashes.add(sig)

        # run model
        results = safe_classify(sent)
        if not results:
            continue

        # pick top label
        best = max(results, key=lambda x: x["score"])
        label, raw_score = best["label"], best["score"]

        sentiment = detect_sentiment(sent)
        weighted = apply_risk_weight(sent, raw_score, sentiment)

        records.append({
            "Company": company_name,
            "Report_File": source_filename,
            "Sentence": sent,
            "Predicted_Label": label,
            "Raw_Score": float(raw_score),
            "Sentiment": sentiment,
            "Risk_Score": float(weighted)
        })
    return records

# -----------------------
# Aggregation
# -----------------------
def aggregate_from_df(df):
    if df is None or df.empty:
        return pd.DataFrame()

    # --- Aggregate raw risk scores per ESG bucket ---
    agg = df.groupby(["Company", "Predicted_Label"])["Risk_Score"].sum().unstack(fill_value=0)

    # --- Average per label ---
    counts = df.groupby(["Company", "Predicted_Label"]).size().unstack(fill_value=0)
    avg = agg.div(counts.replace(0, 1)).add_suffix("_Avg")

    # --- Sentiment counts ---
    sentiment_counts = df.groupby(["Company", "Sentiment"]).size().unstack(fill_value=0)

    # --- Company totals ---
    company_totals = agg.sum(axis=1).rename("Total")
    company_mentions = df.groupby("Company").size().rename("ESG_Mentions")
    company_avg = (company_totals / company_mentions).rename("Total_Avg")

    # --- Normalize each ESG dimension (column-wise max scaling 0–100) ---
    norm = agg.copy()
    for col in norm.columns:
        max_val = norm[col].max()
        if max_val > 0:
            norm[col] = (norm[col] / max_val) * 100
        else:
            norm[col] = 0
    norm = norm.add_suffix("_Norm")

    # --- Merge all parts ---
    final = pd.concat([agg, avg, norm, sentiment_counts], axis=1).fillna(0).reset_index()

    # Add totals, mentions, averages
    final = final.merge(company_totals.reset_index(), on="Company", how="left")
    final = final.merge(company_mentions.reset_index(), on="Company", how="left")
    final = final.merge(company_avg.reset_index(), on="Company", how="left")

    # --- Global normalization for TOTAL (not sum of pillar norms) ---
    max_total = final["Total"].max()
    if max_total > 0:
        final["Total_Norm"] = (final["Total"] / max_total) * 100
    else:
        final["Total_Norm"] = 0.0

    return final.fillna(0.0)
 

# -----------------------
# process one report
# -----------------------
def process_single_report(pdf_path, company_name=None):
    init_model()
    filename = os.path.basename(pdf_path)
    if company_name is None:
        company_name = os.path.splitext(filename)[0]

    sentences = extract_sentences_from_pdf(pdf_path)
    records = classify_sentences_for_report(sentences, company_name, filename)
    df_file = pd.DataFrame(records)

    if os.path.exists(EXPLORER_CSV):
        df_all = pd.read_csv(EXPLORER_CSV)
        df_all = df_all[df_all["Report_File"] != filename]
    else:
        df_all = pd.DataFrame(columns=df_file.columns)

    if not df_file.empty:
        df_all = pd.concat([df_all, df_file], ignore_index=True)

    df_all.to_csv(EXPLORER_CSV, index=False)

    summary_df = aggregate_from_df(df_all)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    return df_file, summary_df

# -----------------------
# UI helpers
# -----------------------
def list_companies():
    if not os.path.exists(SUMMARY_CSV):
        return []
    df = pd.read_csv(SUMMARY_CSV)
    return sorted(df["Company"].astype(str).unique().tolist())

def get_company_snapshot(company_name, top_n=5):
    df_all = pd.read_csv(EXPLORER_CSV) if os.path.exists(EXPLORER_CSV) else pd.DataFrame()
    df_sum = pd.read_csv(SUMMARY_CSV) if os.path.exists(SUMMARY_CSV) else pd.DataFrame()

    row = df_sum[df_sum["Company"] == company_name].iloc[0].to_dict() if not df_sum.empty and company_name in df_sum["Company"].values else {}
    df_company = df_all[df_all["Company"] == company_name] if not df_all.empty else pd.DataFrame()
    sentiment_counts = df_company["Sentiment"].value_counts().to_dict() if not df_company.empty else {}

    return {
        "company": company_name,
        "summary": row,
        "sentiment_counts": sentiment_counts,
        "example_sentences": df_company[["Sentence","Predicted_Label","Raw_Score","Sentiment","Risk_Score"]].head(12).to_dict(orient="records")
    }

def get_comparative_all():
    if not os.path.exists(SUMMARY_CSV):
        return []
    return pd.read_csv(SUMMARY_CSV).to_dict(orient="records")
