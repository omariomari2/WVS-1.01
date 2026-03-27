import asyncio
import traceback
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Finding, Scan
from app.scanner.a01_broken_access import BrokenAccessControlScanner
from app.scanner.a02_crypto_failures import CryptographicFailuresScanner
from app.scanner.a03_injection import InjectionScanner
from app.scanner.a04_insecure_design import InsecureDesignScanner
from app.scanner.a05_security_misconfig import SecurityMisconfigScanner
from app.scanner.a06_vulnerable_components import VulnerableComponentsScanner
from app.scanner.a07_auth_failures import AuthFailuresScanner
from app.scanner.a08_integrity_failures import IntegrityFailuresScanner
from app.scanner.a09_logging_monitoring import LoggingMonitoringScanner
from app.scanner.a10_ssrf import SSRFScanner
from app.scanner.http_client import create_http_client
from app.websocket.scan_progress import progress_manager

SCANNER_MODULES = [
    BrokenAccessControlScanner,
    CryptographicFailuresScanner,
    InjectionScanner,
    InsecureDesignScanner,
    SecurityMisconfigScanner,
    VulnerableComponentsScanner,
    AuthFailuresScanner,
    IntegrityFailuresScanner,
    LoggingMonitoringScanner,
    SSRFScanner,
]


async def run_scan(scan_id: str, target_url: str):
    """Run all scanner modules sequentially against the target."""
    async with create_http_client() as client:
        async with async_session() as db:
            # Mark scan as running
            scan = await db.get(Scan, scan_id)
            if not scan:
                return
            scan.status = "running"
            await db.commit()

            all_findings = []
            total_modules = len(SCANNER_MODULES)

            try:
                for i, module_cls in enumerate(SCANNER_MODULES):
                    module = module_cls(client, target_url)
                    module_name = f"{module.category}: {module.name}"

                    # Update progress
                    scan.current_module = module_name
                    scan.progress = i / total_modules
                    await db.commit()

                    await progress_manager.broadcast(scan_id, {
                        "type": "progress",
                        "progress": scan.progress,
                        "current_module": module_name,
                        "findings_so_far": len(all_findings),
                    })

                    # Run the module
                    try:
                        findings = await asyncio.wait_for(
                            module.scan(),
                            timeout=60,  # 60s per module max
                        )
                        all_findings.extend(findings)
                    except asyncio.TimeoutError:
                        pass  # Skip timed-out modules
                    except Exception:
                        pass  # Don't let one module failure kill the scan

                # Persist findings
                for f in all_findings:
                    db_finding = Finding(
                        scan_id=scan_id,
                        owasp_category=f.owasp_category,
                        owasp_name=f.owasp_name,
                        severity=f.severity.value if hasattr(f.severity, "value") else f.severity,
                        title=f.title,
                        description=f.description,
                        evidence=f.evidence,
                        url=f.url,
                        remediation=f.remediation,
                        confidence=f.confidence.value if hasattr(f.confidence, "value") else f.confidence,
                    )
                    db.add(db_finding)

                scan.status = "completed"
                scan.progress = 1.0
                scan.current_module = None
                scan.total_findings = len(all_findings)
                scan.completed_at = datetime.now(timezone.utc).isoformat()
                await db.commit()

                await progress_manager.broadcast(scan_id, {
                    "type": "completed",
                    "progress": 1.0,
                    "total_findings": len(all_findings),
                })

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.now(timezone.utc).isoformat()
                await db.commit()

                await progress_manager.broadcast(scan_id, {
                    "type": "error",
                    "message": str(e),
                })
