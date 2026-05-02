import random
import urllib.request

target_1 = "https://youtu.be/IN6ExP07bTY?si=B8ZtAdmRIiHzFG0o"
target_2 = "https://youtu.be/aW-a8xOrG8U?si=okSH3Kedvmhm-dZs"

# target_3 = "https://www.youtube.com/watch?v=P4BVmrahsDk"
# target_4 = "https://www.youtube.com/watch?v=8bQWDdARrlU"
# target_5 = "https://www.youtube.com/watch?v=_WvXe61Grgo"
# target_6 = "https://www.youtube.com/watch?v=wNYFWO2WbRI"
# target_7
# target_8
# target_9
# target_10
# target_11
# target_13
# target_14
# target_15
# target_16

targets = [target_1, target_2]#, target_3, target_4, target_5, target_6]


def _is_url_reachable(url: str, timeout: int = 8) -> bool:
    """Return True if the URL returns a 2xx/3xx HTTP response."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        return False


def get_random_target(validate: bool = True) -> str:
    """
    Return a random target URL.
    When validate=True (default), unreachable URLs are skipped so the caller
    always receives a URL that is at least network-reachable.
    Falls back to returning any target if all fail the check.
    """
    shuffled = random.sample(targets, len(targets))
    if not validate:
        return shuffled[0]
    for url in shuffled:
        if _is_url_reachable(url):
            print(f"✅ Target validated: {url}")
            return url
        print(f"⚠️  Target unreachable, skipping: {url}")
    # All failed — return a random one and let the browser agent handle it
    fallback = random.choice(targets)
    print(f"⚠️  All targets failed validation, falling back to: {fallback}")
    return fallback