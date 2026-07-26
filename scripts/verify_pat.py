import asyncio
import os
from pathlib import Path

import httpx


QUERY = """
query {
  repository(owner: "torvalds", name: "linux") {
    name
  }
}
"""


def load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def main() -> int:
    load_dotenv()
    token = os.environ.get("GITHUB_PAT")
    if not token:
        print("GITHUB_PAT is not set")
        return 2
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.github.com/graphql",
            json={"query": QUERY},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        print(payload["errors"])
        return 1
    repo_name = payload["data"]["repository"]["name"]
    print(f"GitHub PAT smoke check passed for torvalds/{repo_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
