from app.integrations.mcp.registry import run_tool

if __name__ == "__main__":
    response = run_tool("arxiv_metadata", {"query": "TF-IDF", "max_results": 2})
    print(f"ok: {response.ok}")
    print(f"tool: {response.tool}")
    print(f"scraped_at: {response.scraped_at}")
    print(f"errors: {response.errors}")
    print(f"items ({len(response.items)}):")
    for item in response.items:
        print(f"  - {item.arxiv_id} | {item.title}")
        print(f"    authors: {item.authors}")
