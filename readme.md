# Website Vulnerability Scanner

A powerful, asynchronous web security scanner that detects common vulnerabilities in websites. Built in Python, this tool leverages `asyncio`, `aiohttp`, and modular configuration for efficient, customizable, and scalable vulnerability scanning. Enhanced with AI-powered analysis and a vivid, user-friendly workflow.

⚠️ **Important Disclaimer**  
This tool is for **educational and authorized testing purposes only**. Using this scanner on websites without explicit permission is unethical and may be illegal.

---
If encountering issues, or for any basic enquiry, please email: `owusuomaribright@gmail.com`, 
or contact through my website at [Portfolio](https://omariomari2.github.io/Personal-Website/)
Do not disclose security vulnerabilities publicly. Responsible disclosure is appreciated.

## 🚀 Features

- **Asynchronous Scanning:** High-performance concurrent scanning using `asyncio` and `aiohttp`.
- **Smart Crawling:** Automatically discovers and scans URLs within a specified depth.
- **AI-Powered Analysis:** Uses DeepSeek AI for detailed vulnerability assessments.
- **Multiple Vulnerability Checks:**  
  - SQL Injection Detection
  - Cross-Site Scripting (XSS)
  - Security Headers Analysis
  - Directory Listing Vulnerabilities

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.7 or higher
- `pip` package manager
- A DeepSeek API key for AI analysis

---

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/omariomari2/Website-Vulnerability-Scanner.git
   cd Website-Vulnerability-Scanner
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage

1. Run the scanner:
   ```bash
   python large_scale_vulnerability_scanner.py
   ```

2. Follow the interactive menu:
   - **Option 1:** Start a new scan  
     Enter the target URL (e.g., `https://example.com`)  
     Specify the crawling depth (default: `2`).
   - **Option 2:** View previous results.
   - **Option 3:** Exit.

---

## 🏗️ Project Structure

Website-Vulnerability-Scanner/
├── large_scale_vulnerability_scanner.py   # Main scanner implementation
├── vulnerability_analyzer.py              # AI-powered analysis
├── web_app.py                             # (If present) Web interface
├── requirements.txt                       # Project dependencies
├── scanner_config.yaml                    # Scan configuration
├── description.txt                        # Vivid workflow and project overview
├── .env                                   # Environment variables (create this)
├── .github/
│   └── workflows/
│       └── main.yml                       # CI/CD configuration
└── README.md                              # This file

---

## 🔧 Configuration Options

- **Scanning Parameters:**
  - **Crawling Depth:** Control how deep the scanner traverses the website.
  - **Concurrent Scans:** Adjust the number of simultaneous scans.
  - **Timeout Settings:** Modify request timeouts.
  - **Custom Headers:** Add specific HTTP headers for scanning.

- **Vulnerability Tests:**
  - SQL Injection patterns
  - XSS payload configurations
  - Security header requirements
  - Directory listing detection

---

## 🚦 Error Handling

The scanner includes robust error handling for:

- Network connectivity issues
- Invalid URLs
- Timeout scenarios
- API failures
- Authentication errors

---

## 📊 Output Format

Results are displayed in a color-coded format in the terminal and are saved in your chosen format (TXT, HTML, CSV) as configured. Each finding includes:
- Vulnerability type & severity
- Affected URLs/parameters
- Payloads used
- Remediation recommendations

---

## 🤝 Contributing

We welcome contributions! Here’s how you can help:

1. Fork the repository
2. Create a new feature branch:
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. Commit your changes:
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/AmazingFeature
   ```
5. Open a Pull Request.

### Coding Standards

- Follow **PEP 8** guidelines.
- Include docstrings for new functions.
- Add appropriate error handling.
- Update tests for new features.

---

## 🔍 Testing

Run the test suite to ensure everything is working:

```bash
python -m unittest discover tests/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔐 Security

For security issues, please email: `owusuomaribright@gmail.com`. or through my website at @omariomari2@github.io
Do not disclose security vulnerabilities publicly. Responsible disclosure is appreciated.

---

## 📜 Changelog

**Version 1.0.0**  
- Initial release  
- Basic vulnerability scanning  
- AI-powered analysis  
- Async crawling implementation
- Modular YAML configuration
- Vivid workflow documentation

---

Made with ❤️ by Omari!

---
