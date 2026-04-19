"""Smart Engagement AI Bot — Twitter/X auto-interaction using OpenAI sentiment."""

import os
import time
import logging

import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── API credentials from environment variables (never hard-code secrets) ──────
TWITTER_API_KEY       = os.environ["TWITTER_API_KEY"]
TWITTER_API_SECRET    = os.environ["TWITTER_API_SECRET"]
TWITTER_ACCESS_TOKEN  = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]
TWITTER_BEARER_TOKEN  = os.environ["TWITTER_BEARER_TOKEN"]
OPENAI_API_KEY        = os.environ["OPENAI_API_KEY"]

# Keyword to search for — override via env var to avoid code changes
SEARCH_KEYWORD = os.environ.get("SEARCH_KEYWORD", "الذكاء الاصطناعي")
SEARCH_LIMIT   = int(os.environ.get("SEARCH_LIMIT", "5"))
# Seconds to wait between likes to avoid rate-limit bans
DELAY_BETWEEN_LIKES = float(os.environ.get("DELAY_BETWEEN_LIKES", "3"))


class SmartEngagementBot:
    def __init__(self) -> None:
        # OAuth 1.0a client — needed for write actions (like, tweet)
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

        # OAuth 2.0 Bearer client — needed for search
        self.client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True,
        )

        # OpenAI client (v1.x SDK)
        self.openai = OpenAI(api_key=OPENAI_API_KEY)

    # ── Sentiment analysis ────────────────────────────────────────────────────

    def should_like(self, tweet_text: str) -> bool:
        """Return True if the tweet is positive/educational and worth liking."""
        try:
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict sentiment filter. "
                            "Reply with exactly one word: "
                            "LIKE if the content is positive, educational, or inspiring. "
                            "SKIP if it is negative, offensive, or irrelevant."
                        ),
                    },
                    {"role": "user", "content": tweet_text},
                ],
                max_tokens=5,
                temperature=0,
            )
            decision = response.choices[0].message.content.strip().upper()
            return decision == "LIKE"
        except Exception as exc:
            log.warning("OpenAI call failed: %s — skipping tweet", exc)
            return False

    # ── Main interaction loop ─────────────────────────────────────────────────

    def run(self, keyword: str = SEARCH_KEYWORD, limit: int = SEARCH_LIMIT) -> None:
        log.info("🔍 Searching for: %s (limit=%d)", keyword, limit)

        try:
            response = self.client.search_recent_tweets(
                query=f"{keyword} -is:retweet lang:ar",
                max_results=max(10, limit),   # API minimum is 10
                tweet_fields=["id", "text", "author_id"],
            )
        except tweepy.TweepyException as exc:
            log.error("Twitter search failed: %s", exc)
            return

        if not response.data:
            log.info("No tweets found for: %s", keyword)
            return

        liked = 0
        for tweet in response.data[:limit]:
            if self.should_like(tweet.text):
                try:
                    self.client.like(tweet.id)
                    log.info("✅ Liked tweet %s: %.80s", tweet.id, tweet.text)
                    liked += 1
                    time.sleep(DELAY_BETWEEN_LIKES)
                except tweepy.TweepyException as exc:
                    log.warning("Could not like tweet %s: %s", tweet.id, exc)
            else:
                log.info("⏩ Skipped tweet %s", tweet.id)

        log.info("Done — liked %d / %d tweets", liked, limit)


if __name__ == "__main__":
    bot = SmartEngagementBot()
    bot.run()
