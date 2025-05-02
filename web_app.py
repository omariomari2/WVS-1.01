import os
import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify
from threading import Thread
from queue import Queue
from dotenv import load_dotenv
from large_scale_vulnerability_scanner import crawl_website, process_urls, classify_severity

app = Flask(__name__)
load_dotenv()

import json
scan_results = {}

# Attempt to import CLI scan state if present
MEMORY_FILE = 'cli_to_web_memory.json'
if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            cli_state = json.load(f)
        scan_id = 'imported_cli'
        scan_results[scan_id] = {
            'status': 'imported',
            'results': [(cli_state.get('url', ''), cli_state.get('vulns', []))],
            'url': cli_state.get('base_url', cli_state.get('url', '')),
            'depth': cli_state.get('depth', 2)
        }
        # Optionally delete memory file after import
        # os.remove(MEMORY_FILE)
    except Exception as e:
        print(f"Failed to import CLI scan state: {e}")

# Helper to run async functions in threads
loop = asyncio.new_event_loop()
def run_async(coro):
    return loop.run_until_complete(coro)

@app.route('/', methods=['GET', 'POST'])
def index():
    imported_url = None
    imported_depth = 2
    # If imported scan exists and has no results, prefill form
    imported_scan = scan_results.get('imported_cli')
    if imported_scan:
        imported_url = imported_scan.get('url')
        imported_depth = imported_scan.get('depth', 2)
    if request.method == 'POST':
        url = request.form['url']
        depth = int(request.form.get('depth', 2))
        scan_id = str(len(scan_results) + 1)
        scan_results[scan_id] = {'status': 'pending', 'results': None, 'url': url, 'depth': depth}
        def scan_task(scan_id, url, depth):
            async def do_scan():
                import aiohttp, ssl
                from aiohttp import ClientTimeout, TCPConnector
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                timeout = ClientTimeout(total=10)
                connector = TCPConnector(limit=20, ssl=ssl_context)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    urls = await crawl_website(session, url, depth)
                    results = await process_urls(session, urls)
                    scan_results[scan_id]['results'] = [(u, v) for u, v in results]
                    scan_results[scan_id]['status'] = 'done'
            run_async(do_scan())
        Thread(target=scan_task, args=(scan_id, url, depth), daemon=True).start()
        return redirect(url_for('scan_status', scan_id=scan_id))
    return render_template('index.html', imported_url=imported_url, imported_depth=imported_depth)

@app.route('/scan/<scan_id>')
def scan_status(scan_id):
    result = scan_results.get(scan_id)
    if not result:
        return 'Scan not found', 404
    # Aggregate all vulnerabilities for a single summary
    all_vulns = []
    if result.get('results') is not None:
        for _, vulns in result['results']:
            all_vulns.extend(vulns)
    summary_rows = [
        [classify_severity(v), v.split(':')[0] if ':' in v else v, v if ':' not in v else v.split(':', 1)[1].strip()]
        for v in all_vulns
    ]
    # Pass classify_severity and summary_rows to the template context
    return render_template('scan_status.html', scan=result, scan_id=scan_id, classify_severity=classify_severity, summary_rows=summary_rows)

@app.route('/download_report/<scan_id>')
def download_report(scan_id):
    from flask import make_response, abort
    result = scan_results.get(scan_id)
    if not result or not result.get('results'):
        return abort(404)
    # Build plain text report
    lines = []
    lines.append(f"Website Vulnerability Scan Report\nScan ID: {scan_id}\n{'='*60}\n")
    for url, vulns in result['results']:
        lines.append(f"Results for: {url}\n")
        for idx, vuln in enumerate(vulns):
            lines.append(f"  {idx+1}. {vuln}")
        lines.append("\n" + "-"*50 + "\n")
    # Summary Table
    all_vulns = [v for _, vulns in result['results'] for v in vulns]
    lines.append("SUMMARY TABLE:\n")
    lines.append(f"{'Severity':<10} | {'Type':<20} | Details")
    lines.append("-"*60)
    for v in all_vulns:
        sev = classify_severity(v)
        typ = v.split(':')[0] if ':' in v else v
        details = v if ':' not in v else v.split(':', 1)[1].strip()
        lines.append(f"{sev:<10} | {typ:<20} | {details}")
    lines.append("\nNEXT STEPS:\n")
    lines.append("1. Implement missing security headers (see above).\n2. Disable directory listing on your web server.\n3. Regularly review and update security configurations.\n4. Conduct periodic security audits and penetration tests.\n5. Educate developers on secure coding practices.\n")
    lines.append("Trusted Remediation Resources:\n- https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers\n- https://owasp.org/www-project-top-ten/\n")
    text_report = "\n".join(lines)
    response = make_response(text_report)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=scan_report_{scan_id}.txt'
    return response

@app.route('/api/explanation', methods=['POST'])
def get_explanation():
    url = request.form['url']
    vuln = request.form['vuln']
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'explanation': 'Error: GEMINI_API_KEY not set. Please configure your API key.'})
    try:
        from vulnerability_analyzer import VulnerabilityAnalyzer
        analyzer = VulnerabilityAnalyzer(api_key)
        # Run the async analysis in the event loop
        explanation = loop.run_until_complete(analyzer.analyze_vulnerabilities(url, [vuln]))
        return jsonify({'explanation': explanation})
    except Exception as e:
        return jsonify({'explanation': f'Error: {str(e)}'})

@app.route('/results')
def results():
    return render_template('results.html', scans=scan_results)

if __name__ == '__main__':
    app.run(debug=True)
