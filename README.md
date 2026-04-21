# VeriSift

### **`Precise PDF Audits. Private by Design`**

**VeriSift** is a professional-grade, local-first PDF comparison engine designed for developers and privacy-conscious organizations. Unlike cloud-based tools that require sensitive documents to be uploaded to external servers, Verisift runs entirely on your local machine.

It employs a unique Hybrid Similarity Scoring system that combines Semantic Text Analysis (to detect meaning changes) with Structural Visual Diffing (to catch layout and image shifts). Whether integrated as a Python library or run through a streamlined CLI, Verisift provides high-fidelity, interactive HTML reports that turn complex document audits into a clear, actionable experience. VeriSift is ideal for developers building document validation workflows, QA teams verifying layout consistency, or security teams ensuring no unauthorized changes occur in critical documents. VeriSift uses `all-MiniLM-L6-v2` for semantic comparisons.

---

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Modes](#-usage-modes)
  - [1. CLI Usage](#1-cli-usage)
  - [2. Library Usage](#2-library-usage)
- [Use Cases & Recommended Settings](#-use-cases--recommended-settings)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Installation

```bash
# Basic installation
pip install verisift

# With semantic analysis support (AI-powered)
pip install verisift[nlp]
```

### Prerequisites

**Poppler** is required for PDF rendering:
 recommended to place the poppler in  `"C:\Program Files\poppler\"`
- **Windows**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
- **macOS**: `brew install poppler`
- **Linux**: `sudo apt-get install poppler-utils`


### Verify installation:
use `verisift health-check` to check if the installation is successful and all dependencies are in place.

Note: by default only libraries required for literal comparison are installed. If you need semantic analysis, install with `nlp` extra by using `pip install verisift[nlp]`.  

&nbsp;
---

## ⚡ Quick Start

### CLI Quick Start

```bash
# Compare two PDFs - Uses default configuration settings
verisift compare --actual "\path\to\pdf\invoice_v2.pdf" --expected "\path\to\pdf\invoice_v1.pdf" # raw string paths can be passed directly without r"<path>" prefix

# Check system health
verisift health-check
```

### Library Quick Start

```python
import verisift

# Simple comparison
report, report_path = verisift.compare_and_generate_report(
    actual= r"\path\to\pdf\invoice_v2.pdf", # using raw string literals for paths to avoid escape issues
    expected= r"\path\to\pdf\invoice_v1.pdf"
)

print(f"Match: {report.overall_match}")
print(f"Report: {report_path}") # path for the HTMl report
```

---

## 📖 Usage Modes

VeriSift supports two primary usage modes:

1. **CLI (Command-Line Interface)** - For terminal/script usage
2. **Library (Python API)** - For programmatic integration

---

## 1. CLI Usage

### Available Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `compare` | Compare two PDF documents | `verisift compare --actual <file> --expected <file> [options]` |
| `set-config` | Save default settings permanently | `verisift set-config [options]` |
| `display-config` | View current configuration | `verisift display-config` |
| `reset-config` | Reset to factory defaults | `verisift reset-config` |
| `health-check` | Verify system dependencies | `verisift health-check` |

### Configuration Options (applicable for compare and set-config command)

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `--mode` | string | `literal`, `semantic` | `literal` | Comparison mode |
| `--text_threshold` | float | 0.0 - 1.0 | 0.95 | Text similarity threshold |
| `--visual_threshold` | float | 0.0 - 1.0 | 0.98 | Visual similarity threshold |
| `--semantic_threshold` | float | 0.0 - 1.0 | 0.80 | Semantic match threshold (semantic mode only) |
| `--text_weightage` | float | 0.0 - 1.0 | 0.80 | Text weight in overall score (visual = 1 - text) |
| `--dpi` | integer | 50 - 300 | 150 | PDF rendering quality |
| `--enable_visual` | boolean | `true`, `false` | `true` | Enable/disable visual comparison |
| `--enable_exclusions` | boolean | `true`, `false` | `false` | Enable regex pattern exclusions. Use `--enable_exclusions` while using it with `comapre`. use `--enable_exclusions true` or `--enable_exclusions false` while using it with `set-config`. |  
| `--exclusion_patterns` | list | - | `[]` | Regex patterns to ignore |
| `--semantic_max_phrase` | integer | 1 - 100 | 20 | Max words for semantic matching |
| `--outputdir` | string | - | `~/Downloads/verisift` | Output directory path |
| `--reportname` | string | - | `verisift_report_<timestamp>.html` | Report filename |
| `--popplerpath` | string | - | System default | Path to Poppler binaries |

### Threshold Behavior

#### Text Threshold

| Value | Behavior | Use Case |
|-------|----------|----------|
| **High (0.95-1.0)** | Strict matching - catches minor changes like spacing, punctuation | Legal documents, contracts, compliance |
| **Medium (0.85-0.94)** | Balanced - ignores trivial differences | General document comparison |
| **Low (0.70-0.84)** | Lenient - focuses on major content changes | Draft reviews, content updates |

#### Visual Threshold

| Value | Behavior | Use Case |
|-------|----------|----------|
| **High (0.95-1.0)** | Strict - detects subtle layout/image changes | Design verification, branding compliance |
| **Medium (0.85-0.94)** | Balanced - catches significant visual differences | General visual comparison |
| **Low (0.70-0.84)** | Lenient - only major structural changes | Content-focused comparison |

#### Semantic Threshold (Semantic Mode Only)

| Value | Behavior | Use Case |
|-------|----------|----------|
| **High (0.85-1.0)** | Strict - requires very similar meaning | Legal, technical documentation |
| **Medium (0.75-0.84)** | Balanced - allows paraphrasing | Business documents, reports |
| **Low (0.60-0.74)** | Lenient - accepts different wording with same intent | Marketing, creative content |

### CLI Examples

#### Basic Comparison

```bash
# Simple comparison with defaults
verisift compare --actual "\path\to\pdf\invoice_new.pdf" --expected "\path\to\pdf\invoice_old.pdf"
```

#### Semantic Mode Comparison

```bash
# AI-powered semantic comparison
verisift compare \
  --actual "\path\to\pdf\contract_v2.pdf" \
  --expected "\path\to\pdf\contract_v1.pdf" \
  --mode semantic \
  --semantic_threshold 0.85
```

#### High-Precision Comparison

```bash
# Strict matching for legal documents
verisift compare \
  --actual "\path\to\pdf\legal_doc_v2.pdf" \
  --expected "\path\to\pdf\legal_doc_v1.pdf" \
  --text_threshold 0.98 \
  --visual_threshold 0.99 \
  --dpi 200
```

#### With Exclusion Patterns

Note on Regex Patterns: VeriSift CLI natively supports Python raw string syntax (r'...'), eliminating the need for backslash escaping typically required in shell environments. Patterns can be used identically in both CLI and library contexts, ensuring consistency across your workflow. Regular CLI (`"[r'\\d{4}-\\d{2}-\\d{2}', r'ID:\\s*\\d+', r'Page \\d+ of \\d+']"`) >>> VeriSift CLI (`"[r'\d{4}-\d{2}-\d{2}', r'ID:\s*\d+', r'Page \d+ of \d+']"`)

```bash
# Ignore dates and IDs
verisift compare \
  --actual "\path\to\pdf\report_new.pdf" \
  --expected "\path\to\pdf\report_old.pdf" \
  --enable_exclusions \
  --exclusion_patterns "[r'\d{4}-\d{2}-\d{2}', r'ID:\s*\d+', r'Page \d+ of \d+']"
```

#### Custom Output Location

```bash
# Specify output directory and filename
verisift compare \
  --actual "\path\to\pdf\doc_a.pdf" \
  --expected "\path\to\pdf\doc_b.pdf" \
  --outputdir "\path\to\pdf_folder\comparison_reports" \
  --reportname "my_comparison_report.html"
```

#### Configuration Management
VeriSift supports setting permanent configuration settings in your local configuration file. This allows you to set defaults that persist across sessions. This is particularly useful for setting up consistent comparison parameters across multiple projects or users. This can be achieved using `set-config` command. The configuration file is stored at `~/.verisift/config.json` (i.e in the user's home directory) and can be edited manually if needed. Factory defaults can be restored using `reset-config`. You can also check the system health using `health-check`. To display current configuration, use `display-config`.

```bash
# Set permanent defaults
verisift set-config \
  --mode semantic \
  --text_threshold 0.92 \
  --visual_threshold 0.95 \
  --outputdir "\path\to\pdf_folder\reports"

# View current settings
verisift display-config

# Reset to factory defaults
verisift reset-config

# Check system health
verisift health-check
```

---

## 2. Library Usage

### Available Functions

| Function | Description | Returns | Comments/Notes |
|----------|-------------|---------|----------------|
| `create_config(**kwargs)` | Create configuration with CLI-style names | `config object` |  |
| `compare_pdfs(actual, expected, config)` | Compare two PDFs | `ComparisonReport` |  |
| `generate_report(report, output_path)` | Generate HTML from comparison result | `str` (path) | Returns path to generated report |  
| `compare_and_generate_report(...)` | Compare and generate report in one call | `(ComparisonReport, str)` | `ComparisonReport`- report object, same as that generated by `compare_pdfs()`, `str` - generated report path |
| `create_comparator(config)` | Create reusable comparator instance | `Comparator` |  |
| `display_config()` | View current settings as dictionary | `dict` |  |
| `set_config(key, value)` | Save single setting permanently | `None` |  |
| `set_configs(**kwargs)` | Save multiple settings permanently | `dict` |  |
| `reset_config()` | Reset to factory defaults | `bool` | Returns "True" if success  |
| `health_check()` | Check system dependencies | `(bool, list)` | `bool` - `True` if system has all the required installations else  `False` with `list` of missing dependencies |
  |

### Configuration Parameters (Library)

Same parameters as CLI, but use Python-friendly names:

```python
config = verisift.create_config(
    mode="semantic",                                # Comparison mode
    text_threshold=0.95,                            # Text similarity (0.0-1.0)
    visual_threshold=0.98,                          # Visual similarity (0.0-1.0)
    semantic_threshold=0.85,                        # Semantic match (0.0-1.0)
    text_weightage=0.75,                            # Text weight (0.0-1.0)
    dpi=180,                                        # Rendering quality (50-300)
    enable_visual=True,                             # Enable visual comparison
    enable_exclusions=True,                         # Enable pattern exclusions
    exclusion_patterns=[...],                       # List of regex patterns
    semantic_max_phrase=20,                         # Max words for semantic (1-100)
    outputdir="\path\to\generated\report\folder",   # Output directory
    reportname="generated_report.html",             # Generated report filename
    popplerpath=r"C:\...\bin"                       # Poppler path
)
```

### Library Examples

#### Example 1: Simple Comparison

```python
import verisift

# Quick comparison with defaults
report, report_path = verisift.compare_and_generate_report(
    actual="\path\to\pdf\invoice_v2.pdf",
    expected="\path\to\pdf\invoice_v1.pdf"
)

# Check results
if report.overall_match:
    print("✅ Documents match!")
else:
    print(f"❌ Mismatch detected (Score: {report.overall_score:.2%})")
    
print(f"Detailed report: {report_path}")
```

#### Example 2: Custom Configuration

```python
import verisift

# Create custom configuration
config = verisift.create_config(
    mode="semantic",
    text_threshold=0.90,
    visual_threshold=0.95,
    text_weightage=0.70,
    enable_exclusions=True,
    exclusion_patterns=[
        r'\d{4}-\d{2}-\d{2}',          # Dates
        r'ID:\s*\d+',                   # IDs
        r'Page \d+ of \d+'              # Page numbers
    ]
)

# Compare with custom config
report = verisift.compare_pdfs(
    actual="\path\to\pdf\contract_v2.pdf",
    expected="\path\to\pdf\contract_v1.pdf",
    config=config
)

# Access detailed results
print(f"Overall Match: {report.overall_match}")
print(f"Overall Score: {report.overall_score:.2%}")
print(f"Text Score: {report.text_score:.2%}")
print(f"Visual Score: {report.visual_score:.2%}")

# Page-level details
for page in report.page_results:
    print(f"Page {page.page_number}:")
    print(f"  Text Match: {page.text_comparison['is_match']}")
    print(f"  Visual Match: {page.visual_comparison['is_match']}")
```

#### Example 3: Two-Step Process (Compare then Generate)

```python
import verisift

# Step 1: Compare documents
config = verisift.create_config(
    mode="literal",
    text_threshold=0.95
)

report = verisift.compare_pdfs(
    actual="document_a.pdf",
    expected="document_b.pdf",
    config=config
)

# Step 2: Analyze results programmatically
if report.overall_score < 0.90:
    print("⚠️ Significant differences detected!")
    
    # Generate detailed report 
    report_path = verisift.generate_report(
        report=report,
        output_path="\path\to\generated\report\critical_diff_report.html"
    )
    print(f"Report saved: {report_path}")
else:
    print("✅ Documents are similar enough")
```

#### Example 4: Batch Processing

```python
import verisift
import os

# Setup configuration
config = verisift.create_config(
    mode="literal",
    text_threshold=0.95,
    dpi=150
)

# Create reusable comparator
comparator = verisift.create_comparator(config)

# Process multiple document pairs
document_pairs = [
    ("invoice1_actual.pdf", "invoice1_expected.pdf"),
    ("invoice2_actual.pdf", "invoice2_expected.pdf"),
    ("invoice3_actual.pdf", "invoice3_expected.pdf"),
]

results = []
for actual, expected in document_pairs:
    # Compare
    report = comparator.compare(actual, expected)
    
    # Generate report
    report_name = f"report_{os.path.basename(actual)}.html"
    report_full_path = os.path.join("\path\to\generated\report\folder", report_name)
    report_path = verisift.generate_report(report, report_full_path)
    
    # Store results
    results.append({
        "files": (actual, expected),
        "match": report.overall_match,
        "score": report.overall_score,
        "report": report_path
    })

# Summary
print("\n=== Batch Comparison Results ===")
for r in results:
    status = "✅ PASS" if r["match"] else "❌ FAIL"
    print(f"{status} {r['files'][0]} - Score: {r['score']:.2%}")
```

#### Example 5: Persistent Configuration

```python
import verisift

# Set up preferred defaults once and reuse everytime you run without setting configuration options for everyrun


verisift.set_configs(
    mode="semantic",
    text_threshold=0.92,
    visual_threshold=0.95,
    dpi=180,
    outputdir="\path\to\generated\report\folder\comparison_reports",
    enable_exclusions=True,
    exclusion_patterns=[
        r'\d{4}-\d{2}-\d{2}',
        r'Transaction ID:\s*\w+'
    ]
)

# Now all comparisons use these settings automatically
report1 = verisift.compare_pdfs("\path\to\pdf\doc1_a.pdf", "\path\to\pdf\doc1_b.pdf")
report2 = verisift.compare_pdfs("\path\to\pdf\doc2_a.pdf", "\path\to\pdf\doc2_b.pdf")

# View current settings
current = verisift.display_config()
print(f"Using mode: {current['mode']}")
print(f"Text threshold: {current['text_threshold']}")

# Reset when needed
verisift.reset_config()
```

#### Example 6: Health Check Before Processing

```python
import verisift
import sys

# Check system health first
is_healthy, missing_deps = verisift.health_check()

if not is_healthy:
    print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
    print("Install Poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
    sys.exit(1)

print("✅ System ready!")

# Proceed with comparison
config = verisift.create_config(mode="semantic")
report = verisift.compare_pdfs("a.pdf", "b.pdf", config=config)
```

---

## 🎯 Use Cases & Recommended Settings

### 1. Legal & Compliance Documents

**Requirements:** Strict matching, catch every change

```python
config = verisift.create_config(
    mode="literal",
    text_threshold=0.98,      # Very strict
    visual_threshold=0.99,    # Very strict
    text_weightage=0.85,      # Prioritize text
    dpi=200                   # High quality
)
```

**Why these settings:**
- High thresholds catch minor changes (punctuation, spacing)
- Literal mode ensures exact word matching
- High DPI captures fine details

---

### 2. Contracts & Agreements

**Requirements:** Detect meaning changes, allow minor formatting

```python
config = verisift.create_config(
    mode="semantic",
    text_threshold=0.92,
    visual_threshold=0.95,
    semantic_threshold=0.88,  # Strict semantic matching
    text_weightage=0.80,
    enable_exclusions=True,
    exclusion_patterns=[
        r'\d{4}-\d{2}-\d{2}',  # Dates
        r'Signature:.*'         # Signatures
    ]
)
```

**Why these settings:**
- Semantic mode detects paraphrasing
- High semantic threshold ensures meaning preservation
- Exclusions ignore expected changes (dates, signatures)

---

### 3. Financial Reports & Invoices

**Requirements:** Verify numbers, ignore dynamic fields

```python
config = verisift.create_config(
    mode="literal",
    text_threshold=0.93,
    visual_threshold=0.96,
    text_weightage=0.75,
    enable_exclusions=True,
    exclusion_patterns=[
        r'Date:\s*\d{2}/\d{2}/\d{4}',
        r'Invoice #:\s*\d+',
        r'Transaction ID:\s*[A-Z0-9]+'
    ]
)
```

**Why these settings:**
- Literal mode for exact number matching
- Exclusions for dynamic IDs and dates
- Balanced thresholds for content verification

---

### 4. Marketing & Creative Content

**Requirements:** Focus on major changes, allow rewording

```python
config = verisift.create_config(
    mode="semantic",
    text_threshold=0.85,      # Lenient
    visual_threshold=0.88,    # Lenient
    semantic_threshold=0.75,  # Allow paraphrasing
    text_weightage=0.60,      # Balance text/visual
    dpi=150
)
```

**Why these settings:**
- Lower thresholds allow creative variations
- Semantic mode accepts different wording
- Balanced weightage for content and design

---

### 5. Technical Documentation

**Requirements:** Catch technical changes, ignore version numbers

```python
config = verisift.create_config(
    mode="semantic",
    text_threshold=0.90,
    visual_threshold=0.93,
    semantic_threshold=0.82,
    text_weightage=0.80,
    enable_exclusions=True,
    exclusion_patterns=[
        r'Version \d+\.\d+\.\d+',
        r'Last Updated:.*',
        r'Page \d+ of \d+'
    ]
)
```

**Why these settings:**
- Semantic mode for technical terminology
- Exclusions for version info and metadata
- High text weightage for content accuracy

---

### 6. Design Mockups & Layouts

**Requirements:** Focus on visual changes, less on text

```python
config = verisift.create_config(
    mode="literal",
    text_threshold=0.85,
    visual_threshold=0.96,    # Very strict
    text_weightage=0.30,      # Prioritize visual
    dpi=250,                  # High quality for design
    enable_visual=True
)
```

**Why these settings:**
- High visual threshold catches layout changes
- Low text weightage focuses on design
- High DPI for detailed visual comparison

---

## 🔧 Troubleshooting

### Common Issues

**1. "Poppler not found" Error**

```bash
# Check health
verisift health-check

# Set Poppler path. configure VeriSift to the right poppler path on your system
verisift set-config --popplerpath "C:\Program Files\poppler\poppler-<version>\Library\bin" 
```

**2. Slow Performance**  
Higher DPI values increase processing time but improve image clarity in reports and comparison accuracy. Balance performance needs with required precision.

- Reduce DPI: `--dpi 100`
- Disable visual comparison: `--enable_visual false`
- Use literal mode if semantic analysis is not required for your use case

**3. Too Many False Positives**

- Lower thresholds: `--text_threshold 0.85`
- Use semantic mode: `--mode semantic`
- Add exclusion patterns for dynamic content like date, page numbers, timestamps, user IDs, sessions IDs, etc.

**4. Missing Differences**

- Increase thresholds: `--text_threshold 0.98`
- Increase DPI: `--dpi 200`
- Check visual comparison is enabled

---

## 📝 License

[Your License Here]

## 🤝 Contributing

[Contributing Guidelines]

## 📧 Support

[Support Information]
