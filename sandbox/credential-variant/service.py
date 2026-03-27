access_key = "ak_live_Z8x4mQ2pL7nB5rV1cD9sF3hJ6kT0yW"
token = "ghp_variantsmoketest_00AaBbCcDdEeFfGgHhIiJjKkLl"


def get_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Access-Key": access_key,
    }


def fetch_profile() -> None:
    import requests

    requests.get("https://example.com/profile", verify=False, timeout=5)
