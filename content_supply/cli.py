"""CLI entry point — calls local API endpoints."""

import json
import sys

import click


def _api(method: str, path: str, data: dict = None, base: str = "http://localhost:8010"):
    """Call a local API endpoint."""
    import httpx

    url = f"{base}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                r = client.get(url, params=data)
            elif method == "POST":
                r = client.post(url, json=data)
            elif method == "PUT":
                r = client.put(url, json=data)
            elif method == "DELETE":
                r = client.delete(url)
            else:
                raise ValueError(f"Unknown method: {method}")
        if r.status_code >= 400:
            click.echo(f"Error {r.status_code}: {r.text[:200]}", err=True)
            sys.exit(1)
        return r.json() if r.text else {}
    except httpx.ConnectError:
        click.echo("Error: Cannot connect to API server. Is it running?", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Content Supply Platform CLI."""
    pass


# ---------- serve ----------

@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8010, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the API server + scheduler."""
    import uvicorn
    uvicorn.run("content_supply.main:app", host=host, port=port, reload=reload)


# ---------- health ----------

@cli.command()
def health():
    """Check API health."""
    r = _api("GET", "/api/health")
    click.echo(json.dumps(r, indent=2, ensure_ascii=False))


# ---------- feeds ----------

@cli.group()
def feed():
    """Manage RSS/Atom feeds."""
    pass


@feed.command("add")
@click.argument("name")
@click.argument("url")
@click.option("--category", default="", help="Feed category")
@click.option("--interval", default=1800, help="Poll interval in seconds")
@click.option("--source-type", default="rss", help="Source type: rss/atom/web")
def feed_add(name: str, url: str, category: str, interval: int, source_type: str):
    """Add a new feed source."""
    r = _api("POST", "/api/feeds", {
        "name": name, "url": url, "category": category,
        "poll_interval": interval, "source_type": source_type,
    })
    click.echo(f"Created feed #{r.get('id', '?')}: {r.get('name', name)}")


@feed.command("list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--limit", default=100, help="Max results")
def feed_list(status, limit):
    """List all feeds."""
    params = {"limit": limit}
    if status:
        params["status"] = status
    feeds = _api("GET", "/api/feeds", params)
    if not feeds:
        click.echo("No feeds found.")
        return
    for f in feeds:
        status_icon = "+" if f.get("status") == "active" else "-"
        click.echo(f"  [{status_icon}] #{f['id']} {f['name']} ({f['source_type']}) "
                    f"[{f.get('category', '')}] interval={f.get('poll_interval', '?')}s")


@feed.command("remove")
@click.argument("feed_id", type=int)
def feed_remove(feed_id: int):
    """Remove a feed."""
    _api("DELETE", f"/api/feeds/{feed_id}")
    click.echo(f"Removed feed #{feed_id}")


@feed.command("toggle")
@click.argument("feed_id", type=int)
def feed_toggle(feed_id: int):
    """Toggle feed active/paused."""
    r = _api("POST", f"/api/feeds/{feed_id}/toggle")
    click.echo(f"Feed #{feed_id} → {r.get('status', '?')}")


# ---------- crawl ----------

@cli.group()
def crawl():
    """Trigger content crawling."""
    pass


@crawl.command("now")
@click.option("--feed-id", type=int, default=None, help="Crawl specific feed")
@click.option("--url", default=None, help="Crawl specific URL")
@click.option("--category", default="", help="Category for manual URL")
def crawl_now(feed_id, url, category):
    """Trigger a crawl job."""
    if url:
        r = _api("POST", "/api/crawl/url", {"url": url, "category": category})
        click.echo(f"Crawled URL: {r.get('status', '?')} | found={r.get('items_found', 0)} new={r.get('items_new', 0)}")
    elif feed_id:
        r = _api("POST", f"/api/crawl/feed/{feed_id}")
        click.echo(f"Crawled feed #{feed_id}: {r.get('status', '?')} | found={r.get('items_found', 0)} new={r.get('items_new', 0)}")
    else:
        click.echo("Specify --feed-id or --url")


@crawl.command("url")
@click.argument("url")
@click.option("--category", default="", help="Category tag")
def crawl_url(url: str, category: str):
    """Scrape a single URL and extract content."""
    r = _api("POST", "/api/crawl/url", {"url": url, "category": category})
    task = r.get("task", r)
    click.echo(f"Status: {task.get('status', '?')}")
    click.echo(f"Found: {task.get('items_found', 0)} | New: {task.get('items_new', 0)}")
    item = r.get("item")
    if item:
        click.echo(f"Title: {item.get('title', 'N/A')}")
        click.echo(f"Author: {item.get('author', 'N/A')}")
        click.echo(f"Content length: {len(item.get('content', ''))}")
    if task.get("error_message"):
        click.echo(f"Error: {task['error_message']}")


@crawl.command("jimeng")
def crawl_jimeng():
    """Batch crawl Jimeng AI artworks."""
    r = _api("POST", "/api/crawl/jimeng")
    task = r.get("task", r)
    click.echo(f"Status: {task.get('status', '?')}")
    click.echo(f"Found: {task.get('items_found', 0)} | Valid: {task.get('items_new', 0)}")
    artworks = r.get("items", [])
    for a in artworks[:5]:
        click.echo(f"  {a.get('title', 'N/A')[:50]} | by {a.get('author', 'N/A')}")
    if len(artworks) > 5:
        click.echo(f"  ... and {len(artworks) - 5} more")


@crawl.command("web-source")
@click.argument("source_name", required=False, default=None)
def crawl_web_source(source_name: str):
    """Trigger web source crawl. Omit name to list available sources."""
    if not source_name:
        r = _api("GET", "/api/crawl/web-sources")
        sources = r.get("sources", [])
        if not sources:
            click.echo("No web sources configured.")
            return
        for s in sources:
            icon = "+" if s.get("enabled") else "-"
            click.echo(f"  [{icon}] {s['name']} | {s['list_url'][:60]} | interval={s.get('poll_interval', '?')}s")
        click.echo("\nUsage: supply crawl web-source <name>")
        return
    r = _api("POST", f"/api/crawl/web-source/{source_name}")
    click.echo(f"WebSource '{source_name}': status={r.get('status', '?')} | "
                f"found={r.get('items_found', 0)} new={r.get('items_new', 0)}")


# ---------- items ----------

@cli.group()
def items():
    """Manage content items."""
    pass


@items.command("list")
@click.option("--status", default="published", help="Filter by status")
@click.option("--source-type", default=None, help="Filter by source type")
@click.option("--category", default=None, help="Filter by category")
@click.option("--limit", default=20, help="Max items to show")
def items_list(status: str, source_type, category, limit: int):
    """List content items."""
    params = {"page_size": limit, "status": status}
    if source_type:
        params["source_type"] = source_type
    if category:
        params["category"] = category
    result = _api("GET", "/api/items", params)
    if not result:
        click.echo("No items found.")
        return
    for item in result:
        rw = " [R]" if item.get("is_rewritten") else ""
        click.echo(f"  #{item['id'][:8]}… {item['title'][:60]} | "
                    f"score={item.get('quality_score', 0):.2f} | {item.get('source_type', '')}{rw}")


@items.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def items_search(query: str, limit: int):
    """Search items by keyword."""
    r = _api("POST", "/api/items/search", {"query": query, "page_size": limit})
    if not r:
        click.echo("No results found.")
        return
    for item in r:
        click.echo(f"  #{item['id'][:8]}… {item['title'][:60]}")


@items.command("get")
@click.argument("item_id")
def items_get(item_id: str):
    """Show item detail."""
    r = _api("GET", f"/api/items/{item_id}")
    click.echo(f"ID:       {r.get('id', 'N/A')}")
    click.echo(f"Title:    {r.get('title', 'N/A')}")
    click.echo(f"URL:      {r.get('url', 'N/A')}")
    click.echo(f"Author:   {r.get('author', 'N/A')}")
    click.echo(f"Source:   {r.get('source_name', 'N/A')} ({r.get('source_type', 'N/A')})")
    click.echo(f"Score:    {r.get('quality_score', 0):.2f}")
    click.echo(f"Tags:     {r.get('tags', 'N/A')}")
    click.echo(f"Status:   {r.get('status', 'N/A')}")
    click.echo(f"Rewritten:{' Yes' if r.get('is_rewritten') else ' No'}")
    content = r.get("content", "")
    if content:
        preview = content[:500] + ("..." if len(content) > 500 else "")
        click.echo(f"\nContent preview:\n{preview}")


@items.command("delete")
@click.argument("item_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def items_delete(item_id: str, confirm: bool):
    """Delete an item from content pool."""
    if not confirm:
        click.confirm(f"Delete item {item_id}?", abort=True)
    r = _api("DELETE", f"/api/items/{item_id}")
    click.echo(f"Deleted: {r}")


# ---------- hot ----------

@cli.group()
def hot():
    """Hot keyword tracking."""
    pass


@hot.command("keywords")
@click.option("--platform", default=None, help="Filter by platform")
@click.option("--limit", default=20, help="Max results")
def hot_keywords(platform, limit):
    """Show trending keywords."""
    params = {"limit": limit}
    if platform:
        params["platform"] = platform
    r = _api("GET", "/api/hot/keywords", params)
    if not r:
        click.echo("No keywords found.")
        return
    for kw in r:
        click.echo(f"  [{kw.get('platform', '?')}] #{kw.get('rank', '?')} "
                    f"{kw['keyword']} (score={kw.get('hot_score', 0):.0f})")


@hot.command("trigger")
@click.option("--platform", default=None, help="Specific platform")
def hot_trigger(platform):
    """Trigger hot keyword collection."""
    data = {}
    if platform:
        data["platforms"] = [platform]
    r = _api("POST", "/api/hot/trigger", data)
    click.echo(f"Triggered: platforms={r.get('platforms_fetched', [])} "
                f"new={r.get('keywords_new', 0)} total={r.get('keywords_total', 0)}")


@hot.command("fetch-content")
@click.option("--keyword-id", type=int, default=None, help="Fetch for specific keyword ID")
@click.option("--max-keywords", default=10, help="Batch: max keywords to process")
@click.option("--platform", default=None, help="Filter by platform")
def hot_fetch_content(keyword_id, max_keywords, platform):
    """Fetch related articles for hot keywords."""
    if keyword_id:
        r = _api("POST", f"/api/hot/{keyword_id}/fetch-content")
        click.echo(f"Keyword: {r.get('keyword', '?')} | "
                    f"found={r.get('items_found', 0)} new={r.get('items_new', 0)}")
        if r.get("message"):
            click.echo(f"  {r['message']}")
    else:
        params = {"max_keywords": max_keywords}
        if platform:
            params["platform"] = platform
        r = _api("POST", "/api/hot/fetch-content", params)
        click.echo(f"Processed: {r.get('keywords_processed', 0)}/{r.get('total_keywords', 0)} keywords | "
                    f"found={r.get('items_found', 0)} new={r.get('items_new', 0)}")


# ---------- rewrite ----------

@cli.group()
def rewrite():
    """LLM content rewriting."""
    pass


@rewrite.command("single")
@click.argument("item_id")
@click.option("--type", "rewrite_type", default="paraphrase", help="paraphrase/summarize/expand")
def rewrite_single(item_id: str, rewrite_type: str):
    """Rewrite a single item."""
    r = _api("POST", f"/api/rewrite/{item_id}", {"rewrite_type": rewrite_type})
    click.echo(f"Rewrite task: {r}")


@rewrite.command("batch")
@click.option("--source-type", default=None, help="Filter by source type")
@click.option("--limit", default=20, help="Max items to rewrite")
def rewrite_batch(source_type, limit):
    """Batch rewrite items."""
    data = {"limit": limit}
    if source_type:
        data["source_type"] = source_type
    r = _api("POST", "/api/rewrite/batch", data)
    click.echo(f"Batch rewrite: {r}")


# ---------- cleanup ----------

@cli.group()
def cleanup():
    """Content cleanup management."""
    pass


@cleanup.command("policies")
def cleanup_policies():
    """Show cleanup policies."""
    r = _api("GET", "/api/cleanup/policies")
    click.echo(json.dumps(r, indent=2, ensure_ascii=False))


@cleanup.command("trigger")
def cleanup_trigger():
    """Trigger cleanup scan (generates pending review)."""
    r = _api("POST", "/api/cleanup/trigger")
    click.echo(f"Scan result: {r}")


@cleanup.command("pending")
def cleanup_pending():
    """Show pending cleanup reviews."""
    r = _api("GET", "/api/cleanup/pending")
    if not r:
        click.echo("No pending reviews.")
        return
    for log in r:
        click.echo(f"  #{log['id']} | {log['source_type']} | "
                    f"to_delete={log.get('items_to_delete', 0)} | "
                    f"auto_confirm={log.get('auto_confirm_at', '?')}")


@cleanup.command("confirm")
@click.argument("log_id", type=int)
def cleanup_confirm(log_id: int):
    """Confirm and execute a cleanup."""
    r = _api("POST", f"/api/cleanup/{log_id}/confirm", {"reviewer": "cli"})
    click.echo(f"Cleanup #{log_id}: deleted {r.get('items_deleted', 0)} items")


@cleanup.command("reject")
@click.argument("log_id", type=int)
def cleanup_reject(log_id: int):
    """Reject a pending cleanup."""
    _api("POST", f"/api/cleanup/{log_id}/reject", {"reviewer": "cli"})
    click.echo(f"Cleanup #{log_id} rejected.")


@cleanup.command("logs")
@click.option("--limit", default=20, help="Max results")
def cleanup_logs(limit: int):
    """Show cleanup history."""
    r = _api("GET", "/api/cleanup/logs", {"limit": limit})
    if not r:
        click.echo("No cleanup logs.")
        return
    for log in r:
        click.echo(f"  #{log['id']} | {log['status']} | {log['policy']} | "
                    f"{log['source_type']} | deleted={log.get('items_deleted', 0)}")


# ---------- tasks ----------

@cli.group()
def tasks():
    """View crawl task history."""
    pass


@tasks.command("list")
@click.option("--task-type", default=None, help="Filter: rss/web/manual/hot_keyword")
@click.option("--status", default=None, help="Filter: pending/running/done/failed")
@click.option("--limit", default=20, help="Max results")
def tasks_list(task_type, status, limit):
    """List crawl tasks."""
    params = {"limit": limit}
    if task_type:
        params["task_type"] = task_type
    if status:
        params["status"] = status
    r = _api("GET", "/api/tasks", params)
    if not r:
        click.echo("No tasks found.")
        return
    for t in r:
        click.echo(f"  #{t['id']} | {t['task_type']} | {t['status']} | "
                    f"found={t.get('items_found', 0)} new={t.get('items_new', 0)} | "
                    f"{t.get('url', '')[:50]}")
        if t.get("error_message"):
            click.echo(f"         Error: {t['error_message'][:80]}")


if __name__ == "__main__":
    cli()
