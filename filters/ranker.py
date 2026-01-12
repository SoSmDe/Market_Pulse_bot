"""Scoring and ranking of content."""

from collectors.twitter import Tweet


def rank_tweets(
    tweets: list[Tweet],
    priority_topics: list[str],
    category_bonuses: dict = None
) -> list[Tweet]:
    """
    Score = likes + retweets*3 + replies*2
    + category bonus
    + topic match bonus
    """
    if category_bonuses is None:
        category_bonuses = {
            "regulatory": 1.5,
            "institutional": 1.5,
            "vc": 1.4,
            "research": 1.3,
            "founder": 1.2,
        }

    for tweet in tweets:
        base_score = tweet.likes + tweet.retweets * 3 + tweet.replies * 2

        # Category multiplier
        multiplier = category_bonuses.get(tweet.author_category, 1.0)

        # Topic bonus
        topic_bonus = 0
        text = tweet.text.lower()
        for topic in priority_topics:
            if topic.lower() in text:
                topic_bonus += 10

        tweet.score = base_score * multiplier + topic_bonus

    tweets.sort(key=lambda x: x.score, reverse=True)
    return tweets
