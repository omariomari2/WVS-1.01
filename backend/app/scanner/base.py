from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from app.scanner.severity import Confidence, Severity


@dataclass
class FindingData:
    owasp_category: str
    owasp_name: str
    severity: Severity
    title: str
    description: str
    url: str
    remediation: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: str | None = None


class BaseScannerModule(ABC):
    category: str = ""
    name: str = ""
    description: str = ""

    def __init__(self, client: httpx.AsyncClient, target_url: str):
        self.client = client
        self.target_url = target_url.rstrip("/")

    def _url(self, path: str = "") -> str:
        if path:
            return urljoin(self.target_url + "/", path.lstrip("/"))
        return self.target_url

    async def _get(self, path: str = "", **kwargs) -> httpx.Response | None:
        try:
            return await self.client.get(self._url(path), **kwargs)
        except httpx.RequestError:
            return None

    async def _request(self, method: str, path: str = "", **kwargs) -> httpx.Response | None:
        try:
            return await self.client.request(method, self._url(path), **kwargs)
        except httpx.RequestError:
            return None

    def _finding(
        self,
        severity: Severity,
        title: str,
        description: str,
        remediation: str,
        url: str | None = None,
        evidence: str | None = None,
        confidence: Confidence = Confidence.MEDIUM,
    ) -> FindingData:
        return FindingData(
            owasp_category=self.category,
            owasp_name=self.name,
            severity=severity,
            title=title,
            description=description,
            url=url or self.target_url,
            remediation=remediation,
            evidence=evidence,
            confidence=confidence,
        )

    @abstractmethod
    async def scan(self) -> list[FindingData]:
        ...
