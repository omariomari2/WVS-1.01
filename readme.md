Website Vulnerability Scanner

## Overview

This Python-based vulnerability scanner is designed to identify common security vulnerabilities in websites. It uses asynchronous programming with `asyncio` and `aiohttp` to efficiently crawl and scan multiple URLs concurrently. The scanner includes checks for SQL injection, cross-site scripting (XSS), missing security headers, and directory listing.
**Disclaimer**: Use on unauthorized websites is unethical and may be illegal!!!!


## Demo 
[Demo][https://github.com/omariomari2/Website-Vulnerability-Scanner/blob/main/wvs%20demo.gif]
## Features

-   **Asynchronous Scanning**: Utilizes `asyncio` and `aiohttp` for concurrent crawling and scanning, improving performance.
-   **Web Crawling**: Discovers URLs within a specified depth, limited to the same domain as the base URL.
-   **Vulnerability Checks**:
    -   SQL Injection: Detects potential SQL injection vulnerabilities by injecting payloads into query parameters.
    -   Cross-Site Scripting (XSS): Identifies XSS vulnerabilities by injecting script payloads and checking for reflection.
    -   Security Headers: Checks for the presence of essential security headers such as Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Strict-Transport-Security.
    -   Directory Listing: Checks if directory listing is enabled, which can expose sensitive files.
-   **Configurable Crawling Depth**: Allows users to specify the depth of crawling.
-   **Error Handling**: Gracefully handles exceptions during crawling and scanning.

## Requirements

-   Python 3.7+
-   aiohttp
-   beautifulsoup4

Install the required packages using pip:
```bash
pip install aiohttp beautifulsoup4
pip install colorama
```

## Usage

1.  Clone the repository:

```bash
git clone [repository_url]
cd [repository_directory]
```

2.  Run the scanner:

```bash
python large_scale_vulnerability_scanner.py
```

3.  Enter the base URL of the website you want to scan when prompted. For example:

```
Enter the base URL to scan (e.g., https://example.com): https://example.com
```

4.  Enter the crawling depth. The default depth is 2. A higher depth will crawl more pages but will also take more time.

```
Enter the crawling depth (default 2): 3
```

5.  View the results. The scanner will output the findings for each URL, indicating any detected vulnerabilities or errors.

## Code Structure

-   `large_scale_vulnerability_scanner.py`: Contains the main application logic, including:
    -   `test_sql_injection`: Tests for SQL injection vulnerabilities.
    -   `test_xss`: Tests for XSS vulnerabilities.
    -   `test_security_headers`: Checks for the presence of security headers.
    -   `test_directory_listing`: Checks for directory listing.
    -   `scan_vulnerabilities`: Orchestrates the vulnerability tests for a single URL.
    -   `crawl_website`: Crawls the website to discover URLs.
    -   `process_urls`: Manages concurrent scanning of URLs.
    -   `main`: The main function that drives the scanning process.

## Limitations

-   The scanner performs basic vulnerability checks and may not detect all types of vulnerabilities.
-   It relies on pattern matching for SQL injection and XSS detection, which may lead to false positives or negatives.
-   The crawler is limited to the same domain as the base URL and does not handle complex website structures.
-   The tool is intended for educational and testing purposes only.

## Contributing

Contributions to improve the scanner are welcome. Please submit pull requests with detailed descriptions of the changes.

## License

This project is licensed under the [License Name] License - see the [LICENSE.md](LICENSE.md) file for details.
