"""CLI entry point using Click."""

import click


@click.group()
def cli():
    """Content Supply Platform CLI."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8010, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the API server + scheduler."""
    import uvicorn
    uvicorn.run(
        "content_supply.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.group()
def feed():
    """Manage RSS/Atom feeds."""
    pass


@feed.command("add")
@click.argument("name")
@click.argument("url")
@click.option("--category", default="", help="Feed category")
@click.option("--interval", default=1800, help="Poll interval in seconds")
def feed_add(name: str, url: str, category: str, interval: int):
    """Add a new feed source."""
    click.echo(f"Adding feed: {name} ({url})")


@feed.command("list")
def feed_list():
    """List all feeds."""
    click.echo("Listing feeds...")


@feed.command("remove")
@click.argument("feed_id")
def feed_remove(feed_id: int):
    """Remove a feed."""
    click.echo(f"Removing feed {feed_id}")


@cli.group("crawl")
def crawl():
    """Trigger content crawling."""
    pass


@crawl.command("now")
@click.option("--feed-id", default=None, help="Crawl specific feed")
@click.option("--url", default=None, help="Crawl specific URL")
def crawl_now(feed_id, url):
    """Trigger a crawl job."""
    if url:
        click.echo(f"Crawling URL: {url}")
    elif feed_id:
        click.echo(f"Crawling feed {feed_id}")
    else:
        click.echo("Crawling all active feeds...")


@cli.group("items")
def items():
    """Manage content items."""
    pass


@items.command("list")
@click.option("--status", default="published", help="Filter by status")
@click.option("--source-type", default=None, help="Filter by source type")
@click.option("--limit", default=20, help="Max items to show")
def items_list(status: str, source_type, limit: int):
    """List content items."""
    click.echo(f"Listing items (status={status}, limit={limit})")


if __name__ == "__main__":
    cli()
