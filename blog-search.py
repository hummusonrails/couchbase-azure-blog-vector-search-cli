# Import necessary libraries and modules
import os
import argparse
import time
import couchbase.search as search
from urllib.parse import urljoin
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from openai import AzureOpenAI
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, SearchOptions
from couchbase.auth import PasswordAuthenticator
from couchbase.exceptions import DocumentNotFoundException
from couchbase.vector_search import VectorQuery, VectorSearch

# Load environment variables from a .env file
load_dotenv()

# Initialize Azure OpenAI client using environment variables
openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Initialize Couchbase cluster and collection using environment variables
cluster = Cluster.connect(
    os.getenv("COUCHBASE_CONN_STRING"),
    ClusterOptions(PasswordAuthenticator(
        os.getenv("COUCHBASE_USERNAME"),
        os.getenv("COUCHBASE_PASSWORD")
    ))
)
bucket = cluster.bucket(os.getenv("COUCHBASE_BUCKET"))
collection = bucket.default_collection()

# Parse the base URL from the blog iframe URL
IFRAME_URL = os.getenv("BLOG_IFRAME_URL")
PARSED = urlparse(IFRAME_URL)
BASE_URL = f"{PARSED.scheme}://{PARSED.netloc}"

# Function to start a headless Chrome browser using Selenium
def start_headless_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Failed to initialize WebDriver: {e}")
        raise

# Function to fetch blog post links from the blog iframe URL
def fetch_blog_links():
    try:
        driver = start_headless_browser()
        print(f"Accessing blog URL: {IFRAME_URL}")
        driver.get(IFRAME_URL)
        
        print("Waiting 5 seconds for page to load completely...")
        time.sleep(5)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        driver.quit()
        
        # Search for blog post links using multiple strategies
        print("🔍 Searching for blog post links...")
        all_anchors = soup.find_all("a")        
        links = []
        
        # Try the original selector
        title_links = soup.select("a.link_title")
        print(f"Found {len(title_links)} links.")
        
        # Use a more general approach to find all potential blog post links
        for anchor in all_anchors:
            href = anchor.get("href")
            title = anchor.get_text(strip=True)
            
            # Skip invalid or irrelevant links
            if not href or not title:
                continue
            if len(title) < 5:
                continue
            if href.startswith("#") or href.startswith("javascript:"):
                continue
                
            # Ensure the URL is absolute
            if not href.startswith(("http://", "https://")):
                full_url = urljoin(BASE_URL, href)
            else:
                full_url = href
                
            # Check if the link is likely a blog post
            if "blog" in full_url.lower() and ("post" in full_url.lower() or "entry" in full_url.lower() or "article" in full_url.lower()):
                links.append((full_url, title))
                print(f"Found potential blog link: {title} - {full_url}")
                
        return links
    except Exception as e:
        print(f"Error in fetch_blog_links: {e}")
        return []

# Function to generate an embedding for a given text using Azure OpenAI
def generate_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Function to check if a document with a given URL already exists in Couchbase
def document_exists(url):
    try:
        collection.get(url)
        return True
    except DocumentNotFoundException:
        return False

# Function to store a blog post's embedding in Couchbase
def store_embedding(url, title, embedding):
    doc = {
        "type": "blog_post",
        "url": url,
        "title": title,
        "embedding": embedding
    }
    collection.upsert(url, doc)

# Function to scrape blog posts and store their embeddings in Couchbase
def scrape_and_store():
    print("🔍 Starting blog scrape...")
    links = fetch_blog_links()
    print(f"✅ Found {len(links)} blog post links")

    for i, (url, title) in enumerate(links, start=1):
        print(f"\n{i}/{len(links)}: Checking → {title}")
        if not document_exists(url):
            print(f"New post detected. Generating embedding...")
            try:
                embedding = generate_embedding(title)
                store_embedding(url, title, embedding)
                print(f"✅ Stored embedding for: {title}")
            except Exception as e:
                print(f"Failed to process '{title}': {e}")
        else:
            print(f"Skipping (already exists in DB): {title}")

# Function to search blog posts using a query string and vector search
def search_blog_posts(query):
    embedding = generate_embedding(query)

    search_index = os.getenv("COUCHBASE_SEARCH_INDEX")
    scope = bucket.scope("_default")

    try:
        # Create a vector search request
        search_req = search.SearchRequest.create(
            search.MatchNoneQuery()
        ).with_vector_search(
            VectorSearch.from_vector_query(
                VectorQuery("embedding", embedding, num_candidates=10)
            )
        )

        # Execute the search and display results
        result = scope.search(search_index, search_req, SearchOptions(limit=5))

        print("\n🔎 Search results:")
        for row in result.rows():
            try:
                doc = collection.get(row.id).content_as[dict]
                title = doc.get("title", "N/A")
                url = doc.get("url", "N/A")
                score = round(row.score * 100, 2)
                print(f"- {title} ({url}) — Score: {score}%")
            except Exception as inner_ex:
                print(f"Could not fetch document for ID: {row.id}")
                print(f"Error: {inner_ex}")

        print(f"\nTotal results: {result.metadata().metrics().total_rows()}")

    except Exception as ex:
        import traceback
        print("An error occurred during vector search:")
        traceback.print_exc()

# Main function to handle CLI arguments and execute the appropriate functionality
def main():
    parser = argparse.ArgumentParser(description="CLI for scraping and searching Naver blog posts with vector search.")
    parser.add_argument("--scrape", action="store_true", help="Scrape the blog and store new embeddings")
    parser.add_argument("--search", type=str, help="Search blog posts using a query string")

    args = parser.parse_args()

    if args.scrape:
        scrape_and_store()
    elif args.search:
        search_blog_posts(args.search)
    else:
        parser.print_help()

# Entry point of the script
if __name__ == "__main__":
    main()
