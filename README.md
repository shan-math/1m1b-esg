# ESG Report Analyzer

An **AI-powered ESG (Environmental, Social, Governance) report analyzer** that extracts and classifies information from company sustainability reports (PDFs).

The application allows users to **upload ESG or sustainability reports**, automatically extracts the text, and uses a **FinBERT-based NLP model** to classify sentences into:

* Environmental
* Social
* Governance

The results are processed and stored as structured datasets for further ESG analysis and exploration.

---

# Features

### PDF ESG Report Upload

* Upload company ESG or sustainability reports
* Supports **PDF documents**

### Automated ESG Classification

* Uses **FinBERT ESG model** for NLP classification
* Extracts sentences from reports
* Classifies them into ESG categories

### Data Processing Pipeline

* Text extraction from PDF files
* Sentence tokenization
* ESG classification using transformer model
* Structured data generation

### Data Output

Processed results are saved into:

* `esg_explorer.csv` → sentence-level ESG classification
* `esg_summary.csv` → aggregated ESG statistics

### Web Interface

Simple frontend interface to:

* Upload ESG reports
* Trigger analysis
* Interact with the backend API

---

# Project Architecture

```
User Uploads ESG Report
        │
        ▼
Flask API (app.py)
        │
        ▼
ESG Processing Pipeline (esg_pipeline.py)
        │
        ├── PDF Text Extraction (pdfplumber)
        ├── Sentence Tokenization (NLTK)
        ├── FinBERT ESG Classification
        │
        ▼
Structured Output
        ├── data/esg_explorer.csv
        └── data/esg_summary.csv
```

---

# Project Structure

```
1m1b-esg
│
├── app.py
│   Flask backend for handling file uploads and API requests
│
├── esg_pipeline.py
│   Core ESG processing pipeline and NLP classification
│
├── requirements.txt
│   Python dependencies
│
├── data
│   ├── esg_explorer.csv
│   └── esg_summary.csv
│
├── reports
│   Sample ESG reports
│
├── static
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── uploads
    Uploaded ESG reports
```

---

# Technologies Used

### Backend

* Python
* Flask

### NLP / Machine Learning

* Transformers (HuggingFace)
* FinBERT ESG Model
* NLTK

### Data Processing

* Pandas
* pdfplumber

### Frontend

* HTML
* CSS
* JavaScript

---

# Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/esg-report-analyzer.git
cd esg-report-analyzer
```

---

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Download FinBERT ESG Model

Update the model path in `esg_pipeline.py`:

```python
MODEL_PATH = "path_to_finbert_esg_model"
```

Example:

```
D:\esg\models\finbert-esg
```

---

### 4. Run the Application

```bash
python app.py
```

---

### 5. Open in Browser

```
http://localhost:5000
```

Upload an ESG report and start analyzing.

---

# ESG Classification Pipeline

The ESG pipeline performs the following steps:

1. **Extract text** from the uploaded PDF using `pdfplumber`.
2. **Split text into sentences** using NLTK tokenizer.
3. **Classify each sentence** using the FinBERT ESG transformer model.
4. **Store results** in structured CSV files.

---

# Output Files

### `esg_explorer.csv`

Contains detailed ESG classification results:

| Company | Sentence | ESG Category | Score |
| ------- | -------- | ------------ | ----- |

Used for detailed ESG exploration.

---

### `esg_summary.csv`

Aggregated ESG statistics:

| Company | Environmental | Social | Governance |

Used for ESG performance overview.

---

# Example Use Cases

* ESG research and analysis
* Sustainability reporting insights
* Financial risk assessment
* Corporate responsibility tracking
* Academic ESG studies

---

# Future Improvements

Possible enhancements include:

* ESG dashboard visualization
* Company comparison analytics
* ESG trend detection
* Integration with financial datasets
* Deployment with Docker or cloud services
* Real-time ESG scoring API

---

# License

This project is open-source and available under the **MIT License**.

---
