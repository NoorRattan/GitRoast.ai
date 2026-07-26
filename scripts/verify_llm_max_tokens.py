import asyncio
import json
import os
from pathlib import Path

import httpx

from app.services.github_client import parse_profile_response
from app.services.llm_client import ANTHROPIC_MAX_TOKENS, AnthropicRoastClient, repo_evidence_from_profile
from app.services.scoring import score_profile


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
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set")
        return 2

    fixture_path = Path("tests/fixtures/github/whale_profile.json")
    profile = parse_profile_response(json.loads(fixture_path.read_text(encoding="utf-8")))
    scores_entry = score_profile(profile)

    async with httpx.AsyncClient(timeout=60) as http_client:
        client = AnthropicRoastClient(api_key, http_client)
        result = await client.generate_roast(
            username=profile["username"],
            scores=scores_entry["scores"],
            flags=scores_entry["flags"],
            findings=scores_entry["findings"],
            roast_intensity_applied="hell",
            repo_evidence=repo_evidence_from_profile(profile),
        )

    total_chars = len(json.dumps(result))
    print(f"Hell generation returned {total_chars} JSON chars with max_tokens={ANTHROPIC_MAX_TOKENS}")
    print(f"roadmap_items={len(result['roadmap'])} strengths={len(result['strengths'])} improvements={len(result['improvement_areas'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
