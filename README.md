# WVS Product Security

WVS runs a product-security PR pipeline for changes under `sandbox/**`, scanning only the touched sandbox projects during each pull request. The pipeline posts a security summary back to the PR, fails the check when blocking findings are introduced, and includes an `Open in WVS` link for deeper review in the app. Imported PR findings then flow into the existing findings, AI, and rectify experience inside WVS.
