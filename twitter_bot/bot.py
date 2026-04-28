"""
Smart Engagement Bot — Twitter/X auto-interaction.
Sentiment analysis uses DeepSeek V4 Flash via Docker Model Runner (local, free).
Original: OpenAI gpt-3.5-turbo → replaced with local AI, zero cost, zero privacy risk.
"""
import os
import time
import logging
import json

import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Twitter credentials ───────────────────────────────────────────────────────
TWITTER_API_KEY       = os.environ["TWITTER_API_KEY"]
TWITTER_API_SECRET    = os.environ["TWITTER_API_SECRET"]
TWITTER_ACCESS_TOKEN  = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]
TWITTER_BEARER_TOKEN  = os.environ["TWITTER_BEARER_TOKEN"]

# ── Local AI (Docker Model Runner) ────────────────────────────────────────────
MODEL_RUNNER_URL = os.environ.get("DOCKER_MODEL_RUNNER_URL", "http://localhost:12434/engines/llama.cpp/v1")
AI_MODEL         = os.environ.get("AI_MODEL_GENERAL", "ai/deepseek-v4-flash")

# ── Bot settings ──────────────────────────────────────────────────────────────
SEARCH_KEYWORD      = os.environ.get("SEARCH_KEYWORD", "الذكاء الاصطناعي")
SEARCH_LIMIT        = int(os.environ.get("SEARCH_LIMIT", "5"))
DELAY_BETWEEN_LIKES = float(os.environ.get("DELAY_BETWEEN_LIKES", "3"))

_SENTIMENT_SYSTEM = (
    "You are a strict sentiment filter for Arabic tweets. "
    "Reply with exactly ONE word: LIKE if the content is positive, educational, "
    "or inspiring. SKIP if it is negative, offensive, spam, or irrelevant."
)


class SmartEngagementBot:
    def __init__(self) -> None:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

        self.client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True,
        )

        # Docker Model Runner — local AI, no API key required
        self._ai = OpenAI(base_url=MODEL_RUNNER_URL, api_key="unused")

    # ── Sentiment analysis via local AI ───────────────────────────────────────

    def should_like(self, tweet_text: str) -> bool:
        try:
            resp = self._ai.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": _SENTIMENT_SYSTEM},
                    {"role": "user", "content": tweet_text},
                ],
                max_tokens=5,
                temperature=0,
                timeout=10,
            )
            decision = resp.choices[0].message.content.strip().upper()
            return decision == "LIKE"
        except Exception as exc:
            log.warning("Local AI call failed: %s — skipping tweet", exc)
            return False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self, keyword: str = SEARCH_KEYWORD, limit: int = SEARCH_LIMIT) -> dict:
        log.info("Searching: %s (limit=%d, model=%s)", keyword, limit, AI_MODEL)

        results = {"liked": 0, "skipped": 0, "errors": 0, "tweets": []}

        try:
            response = self.client.search_recent_tweets(
                query=f"{keyword} -is:retweet lang:ar",
                max_results=max(10, limit),
                tweet_fields=["id", "text", "author_id"],
            )
        except tweepy.TweepyException as exc:
            log.error("Twitter search failed: %s", exc)
            results["error"] = str(exc)
            return results

        if not response.data:
            log.info("No tweets found for: %s", keyword)
            return results

        for tweet in response.data[:limit]:
            if self.should_like(tweet.text):
                try:
                    self.client.like(tweet.id)
                    log.info("Liked %s: %.80s", tweet.id, tweet.text)
                    results["liked"] += 1
                    results["tweets"].append({"id": str(tweet.id), "text": tweet.text[:120], "action": "liked"})
                    time.sleep(DELAY_BETWEEN_LIKES)
                except tweepy.TweepyException as exc:
                    log.warning("Could not like %s: %s", tweet.id, exc)
                    results["errors"] += 1
            else:
                log.info("Skipped %s", tweet.id)
                results["skipped"] += 1
                results["tweets"].append({"id": str(tweet.id), "text": tweet.text[:120], "action": "skipped"})

        log.info("Done — liked %d / skipped %d / errors %d", results["liked"], results["skipped"], results["errors"])
        return results


if __name__ == "__main__":
    bot = SmartEngagementBot()
    bot.run()
