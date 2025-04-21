from dotenv import load_dotenv
from openai import OpenAI
import os
import openai
import feedparser
import json
import random
import tweepy

load_dotenv()  # This loads the .env file
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

# Now you can safely access your keys
openai_api_key = os.getenv("OPENAI_API_KEY")
twitter_api_key = os.getenv("TWITTER_API_KEY")
twitter_api_secret = os.getenv("TWITTER_API_SECRET")
twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
openai.api_key = openai_api_key

# === RSS feed (you can swap later) ===
RSS_FEED_URL = "https://www.ft.com/?format=rss"
HEADLINES_FILE = "headlines.json"
MAX_TWEETS_PER_RUN = 3  # adjust as you like

# Define flavor intensity levels with example phrases for guidance
flavor_pack = {
    0: [],
    1: ["Just the basics, no frills.", "Keep it neutral and factual."],
    2: ["Economics at work.", "Just stating the obvious here."],
    3: ["In case you missed it...", "Here’s the deal."],
    4: ["Fed’s on the move!", "Market’s watching this one closely."],
    5: ["Brace yourselves, folks.", "Hold onto your seats."],
    6: ["The economy’s a wild ride.", "Here’s some spice for your portfolio."],
    7: ["Powell’s making moves, but why?", "Looks like we’re in for a show."],
    8: ["Jerome’s at it again. Bet you didn’t see that coming.", "Fed's playing chess. 🧠💥"],
    9: ["Central bankers do their thing while we just cope.", "This is the financial circus, people. 🎪"],
    10: ["The Fed just pulled a fast one — chaos incoming.", "Inflation is still running wild and so is Jerome. 🔥🤡"]
}

# Function to generate tweet with random flavor intensity
def generate_tweet_with_flavour(headline):
    try:
        # Randomly select a flavor intensity level
        flavour = random.randint(1, 10)
        flavor_phrases = flavor_pack[flavour]

        # Create a prompt to generate the tweet with the selected flavor
        prompt = f"Rewrite this financial news headline into a tweet in the style of a {flavour} finance Twitter influencer, absolutely do not include hashtags or any social media jargon:\n\n{headline}"

        # Make the API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial influencer who tweets sharp, opinionated takes on markets and economics."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
        )

        # Return the generated tweet
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating tweet: {str(e)}"

def create_twitter_client():
    return tweepy.Client(
        consumer_key=twitter_api_key,
        consumer_secret=twitter_api_secret,
        access_token=twitter_access_token,
        access_token_secret=twitter_access_token_secret
    )

# Function to post tweet
def post_tweet(tweet_text):
    try:
        client = create_twitter_client()
        client.create_tweet(text=tweet_text)
        print(f"Tweet posted: {tweet_text}")
    except Exception as e:
        print(f"Error posting tweet: {e}")

# Ask ChatGPT to classify the headline
def score_headline_priority(headline):
    try:
        prompt = f"""Rate the importance of this headline from 0 to 10 for a financial Twitter audience, where 10 means it's a high-priority macroeconomic or central bank story, and 0 means it's not financial at all.

Headline: "{headline}"

Just reply with a single number between 0 and 10."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analyst scoring headline importance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=5,
        )

        score = int(response.choices[0].message.content.strip())
        return score

    except Exception as e:
        print(f"Error scoring headline: {e}")
        return 0

# === Load or initialize saved headlines ===
def load_saved_headlines():
    if os.path.exists(HEADLINES_FILE):
        with open(HEADLINES_FILE, "r") as f:
            return json.load(f)
    return []

def save_headlines(headlines):
    with open(HEADLINES_FILE, "w") as f:
        json.dump(headlines, f, indent=2)

# === Get latest headlines ===
def get_latest_headlines():
    feed = feedparser.parse(RSS_FEED_URL)

    # Check feedparser raw output
    # print("DEBUG: Full feed data:", feed)
    # print("DEBUG: Feed entries returned:", len(feed.entries))

    # Check if feed.entries contains anything useful
    if len(feed.entries) > 0:
        return [entry.title.strip() for entry in feed.entries]
    else:
        return []

# === Filter only new ones ===
def filter_new_headlines(all_headlines, saved_headlines):
    return [hl for hl in all_headlines if hl not in saved_headlines]

# === Main process ===
def main():
    saved = load_saved_headlines()
    latest = get_latest_headlines()
    new = filter_new_headlines(latest, saved)

    if not new:
        print("No new headlines.")
        return

    # Score and prioritize financial headlines
    scored_headlines = []
    for hl in new:
        score = score_headline_priority(hl)
        if score >= 5:  # filter out low-relevance
            scored_headlines.append((hl, score))
        else:
            print(f"Skipped (low score {score}): {hl}")

    # Sort headlines by score, descending
    scored_headlines.sort(key=lambda x: x[1], reverse=True)

    # Take top N
    top_headlines = [hl for hl, _ in scored_headlines[:MAX_TWEETS_PER_RUN]]

    if not top_headlines:
        print("No high-priority headlines to post.")
        return

    for headline in top_headlines:
        rewritten = generate_tweet_with_flavour(headline)
        post_tweet(rewritten)
        print(rewritten)

    save_headlines(saved + top_headlines)

if __name__ == "__main__":
    main()