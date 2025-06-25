import filecmp
import hashlib
import json

from feedgen.feed import FeedGenerator
import requests
from bs4 import BeautifulSoup

# Constants
BASE_URL = "https://www.paulgraham.com/"
ARTICLES_URL = BASE_URL + "articles.html"
FEED_FILE = "feed.xml"
FEED_FILE_WITHOUT_CONTENT = "feed_without_content.xml"
HASH_FILE = "articles.md5"
PREVIOUS_HASH_FILE = HASH_FILE + ".previous"


def fetch_article_content(url):
    """Fetches the content of a single article."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract the main content. Most PG essays are inside <font> tags.
    content = ""
    for font_tag in soup.find_all("font"):
        content += font_tag.get_text(separator="\n", strip=True)

    return content.strip()


def fetch_content(articles):
    """Fetches content of all articles.
    Modifies 'articles' object in-place.
    """
    for article in articles:
        content = fetch_article_content(article["url"])
        article["content"] = content


def fetch_articles():
    """Fetches the list of articles with title, URL, and content."""
    response = requests.get(ARTICLES_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    articles = []

    # TODO_HACK: Num of links to skip. The first 3 links are not the most recent essays.
    # Rather, Paul shares the best essays to start "if you're not sure which to read [first]

    # Skipping the first 3 links (non-recent, recommended essays)
    num_links_to_skip = 3

    # Find all 'a' tags with hrefs, skip those that have no actual text
    for link in soup.find_all("a", href=True)[num_links_to_skip + 1 :]:
        href = link["href"]
        title = link.get_text(strip=True)  # Extracts only the text, skips inner HTML tags
        if href.endswith(".html") and title:  # Only process if title has actual text
            url = BASE_URL + href
            articles.append({"title": title, "url": url})

    return articles


def generate_rss_feed(articles, file):
    """Generates the RSS feed with articles and their content."""
    fg = FeedGenerator()
    fg.id('http://www.paulgraham.com/')
    fg.title('Paul Graham: Essays')
    fg.author({'name':'Paul Graham'})
    fg.link(href='http://www.paulgraham.com/', rel='alternate')
    fg.description('Scraped feed by https://github.com/rlan/pgessays-rss')
    fg.link(href=f"https://raw.githubusercontent.com/rlan/pgessays-rss/main/{file}", rel='self')
    fg.language('en')

    for article in articles:
        fe = fg.add_entry()
        fe.title(article['title'])
        #fe.id(article['url'])
        fe.guid(guid=article['url'], permalink=True)
        fe.link(href=article['url'])
        if "content" in article:
            fe.description(article['content'])

    fg.rss_file(file)


def generate_hash(articles, file):
    """Generate a hash for list of articles."""
    data = json.dumps(articles).encode("utf-8")
    hash = hashlib.md5(data).hexdigest()
    with open(file, "w") as f:
        f.write(hash)


def main():
    """Main entry point of the script."""
    articles = fetch_articles()
    generate_hash(articles, HASH_FILE)
    if filecmp.cmp(PREVIOUS_HASH_FILE, HASH_FILE):
        print("No new articles")
    else:
        generate_rss_feed(articles, FEED_FILE_WITHOUT_CONTENT)
        fetch_content(articles) # modifies articles object
        generate_rss_feed(articles, FEED_FILE)
        print(f"RSS feed generated with {len(articles)} articles")


if __name__ == "__main__":
    main()
