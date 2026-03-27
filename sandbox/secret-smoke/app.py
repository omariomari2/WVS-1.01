API_KEY = "sk_live_51N8WQaAZD7bC5mNL2Qp9RstUvWxYz12"
TOKEN = "github_pat_11SMOKETEST00AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQr"


def build_auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-API-Key": API_KEY,
    }
