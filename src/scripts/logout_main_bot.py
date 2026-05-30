import json
import urllib.error
import urllib.request

import config


def main() -> None:
    token: str = config.MAIN_BOT_TOKEN or ""
    if not token:
        raise SystemExit("MAIN_BOT_TOKEN env var is required.")

    url: str = f"https://api.telegram.org/bot{token}/logOut"
    print(f"Calling cloud Bot API logOut for the main bot...")

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw: bytes = resp.read()
    except urllib.error.HTTPError as exc:
        body: str = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from cloud API:\n{body}")

    parsed: dict = json.loads(raw.decode("utf-8"))
    ok: bool = bool(parsed.get("ok"))
    description: str = str(parsed.get("description", ""))

    if ok:
        print("Success. Cloud API session is closed; bot can now connect to the local server.")
    else:
        print(f"Cloud API replied: ok={ok}, description={description!r}")


if __name__ == "__main__":
    main()
