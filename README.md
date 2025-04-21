# Blog Vector Search CLI Tool

![OpenAI, Azure and Couchbase logos](./readme-images/logos_banner.png)

This is a Python CLI tool designed specifically for scraping iframe-based content from blogs that load posts dynamically via JavaScript. It uses Selenium to handle iframe rendering, extracts blog post links, generates vector embeddings via Azure OpenAI, stores the metadata and embeddings in Couchbase, and enables semantic search using vector similarity queries.

> [!NOTE]  
> It does NOT store the content of the blog posts. Only the title, URL, and embeddings are saved in Couchbase.

## Setup

1. Clone the repo or copy the script to your local environment.

2. Install dependencies:

   `pip install -r requirements.txt`

3. Create a `.env` file in the same directory with the following environment variables:

```bash
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-azure-endpoint.openai.azure.com
COUCHBASE_CONN_STRING=couchbases://your-cluster-url
COUCHBASE_USERNAME=your-couchbase-username
COUCHBASE_PASSWORD=your-couchbase-password
COUCHBASE_BUCKET=your-couchbase-bucket-name
COUCHBASE_SEARCH_INDEX=your-couchbase-search-index-name
```

## Usage

Run the script from the command line:

1. Scrape the blog and store new embeddings:

`python blog-search.py --scrape`

This command scrapes the blog homepage, extracts new post titles and URLs,
generates an embedding using Azure OpenAI, and stores the info in Couchbase.

2. Search blog posts by a natural language query:

`python blog-search.py --search "your search query"`

This command embeds the query, performs vector similarity search against
stored blog post embeddings in Couchbase, and prints the top matches.

3. Display help message:

`python blog-search.py --help`

## Data Stored in Couchbase

Each blog post is stored as a document with this structure:

```json
{
  "type": "blog_post",
  "url": "https://link-to-blog/blog/post_id...",
  "title": "Some Blog Title",
  "embedding": [float, float, float, ...]
}
```

The document key is the blog post URL.

## Requirements

- Python 3.8+
- Azure OpenAI account with access to the `text-embedding-3-small` model
- Couchbase Capella with a vector index enabled on the `embedding` field

## Troubleshooting

❌ **Azure OpenAI Resource Not Found API Error**? 

💡 Make sure you have deployed the `text-embedding-3-small` model inside the Azure OpenAI resource:

```
Open Azure AI Foundry > Deployments > + Deploy Model
```

Copy the new endpoint from the Azure AI Foundry display and paste it in the `.env` file. The API key will remain the same.

*See this [Stack Overflow post](https://stackoverflow.com/questions/77278712/azure-openai-the-api-deployment-for-this-resource-does-not-exist) for more details.*

❌ **Couchbase Connection Error**?

💡 Make sure you have the correct Couchbase connection string, username, password, and bucket name in the `.env` file. Ensure that you have allowed access to the Couchbase cluster from either your IP address specifically, or allow access from anywhere.

❌ **Couchbase Index Not Found Error**?

💡 Make sure you have created a vector index on the `embedding` field in your Couchbase bucket. You can do so inside the Couchbase Capella UI.

*See this [Couchbase Documentation Resource](https://docs.couchbase.com/cloud/vector-search/create-vector-search-index-ui.html) for more details.*

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

