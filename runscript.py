import os
import sys
import re
import posixpath
import tracemalloc
from pathlib import Path
from time import perf_counter
from urllib.parse import unquote

import psutil
import sqlalchemy as sa
from bs4 import BeautifulSoup as bs
from libzim.reader import Archive
from sqlalchemy.dialects.sqlite import insert

from database import engine, articles, edges, seeds, seed_nodes

projects = Path(__file__).resolve().parent.parent
zim_path = projects / 'data' / 'wiki' / 'wikipedia_en_all_nopic_2026-06.zim'

drops = '.hatnote, .sidebar, .navbox, .mw-references-wrap, .mw-cite-backlink, .mw-editsection, .navbox-styles'
drops += ', .reference, .cite-bracket, .Z3988, .refbegin, .toclimit-3, style, .mw-empty-elt, .reflist'
drops += ', .references, .mw-references, .external-links, .authority-control, .sistersitebox, .metadata'
drops += ', .ambox, .ombox, .vertical-navbox, .infobox'


def resolve_path(zim, entry):
    if entry.is_redirect:
        return resolve_path(zim, entry.get_redirect_entry())

    content = entry.get_item().content
    if b'http-equiv="refresh"' in bytes(content[:256]):
        print(f'Raw HTML: {bytes(content)!r}', flush=True)
        soup = bs(bytes(content), 'html.parser')
        refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})

        if refresh:
            print(f'Source: {entry.path}')
            print(f'Raw refresh: {refresh["content"]!r}', flush=True)
            target = re.search(rb"""URL='(.*?)'" />""", bytes(content)).group(1).decode('utf-8')
            target = unquote(target.split('#', 1)[0])
            trailing_slash = target.endswith('/')
            target = posixpath.normpath(posixpath.join(posixpath.dirname(entry.path), target)).lstrip('/')
            target += '/' if trailing_slash and not target.endswith('/') else ''
            print(f'Resolved target: {target!r}', flush=True)
            return resolve_path(zim, zim.get_entry_by_path(target))

    return entry.path


def batches(items, size=1000):
    items = list(items)

    for i in range(0, len(items), size):
        yield items[i:i+size]


def get_children(zim, path):
    path = resolve_path(zim, zim.get_entry_by_path(path))
    entry = zim.get_entry_by_path(path)

    html = bytes(entry.get_item().content).decode('utf-8')
    soup = bs(html, 'html.parser')
    article = soup.select_one('#mw-content-text .mw-parser-output')

    if article is None:
        print(f'\nExtraction Failed: {path}')
        print(f'MIME type: {entry.get_item().mimetype}')
        print(f'HTML length: {len(html)}')
        print(f'Page title: {soup.title}')
        print(f'Head: {soup.head}')
        print(f'Body: {soup.body}')
        raise RuntimeError(f'Article container missing: {path}')

    for element in article.select(drops):
        element.decompose()

    links = [
        link for link in article.find_all('a', href=True)
        if not link['href'].startswith(('#', 'http:', 'https:', '//'))
        and 'external' not in link.get('class', [])
    ]
    paths = {unquote(link['href'].split('#', 1)[0]) for link in links}

    resolved_paths = {resolve_path(zim, zim.get_entry_by_path(path)) for path in paths if zim.has_entry_by_path(path)}
    resolved_paths.discard(path)

    return resolved_paths


def get_stored_children(parent_id):
    with engine.connect() as conn:
        scanned = conn.execute(
            sa.select(articles.c.scanned)
            .where(articles.c.id == parent_id)
        ).scalar_one()

        if not scanned:
            return None

        rows = conn.execute(
            sa.select(articles.c.path).select_from(
                edges.join(
                    articles, edges.c.child_id == articles.c.id
                )
            ).where(edges.c.parent_id == parent_id)
        )
        children = set(rows.scalars())

        return children


def store_children(parent_id, children, seed_id, depth):

    with engine.begin() as conn:
        if children:
            for batch in batches(children, 15000):
                conn.execute(
                    insert(articles)
                    .values([
                        {'path': path, 'scanned': False}
                        for path in batch
                    ])
                    .on_conflict_do_nothing(index_elements=['path'])
                )

            child_ids = {}
            for batch in batches(children, 30000):
                rows = conn.execute(
                    sa.select(articles.c.path, articles.c.id)
                    .where(articles.c.path.in_(batch))
                )

                child_ids.update(rows.tuples().all())

            for batch in batches(child_ids.values(), 15000):
                conn.execute(
                    insert(edges)
                    .values([
                        {'parent_id': parent_id, 'child_id': child_id}
                        for child_id in batch
                    ])
                    .on_conflict_do_nothing(
                        index_elements=['parent_id', 'child_id']
                    )
                )

            for batch in batches(child_ids.values(), 7500):
                conn.execute(
                    insert(seed_nodes)
                    .values([
                        {
                            'seed_id': seed_id,
                            'article_id': child_id,
                            'depth': depth,
                            'expanded': False
                        }
                        for child_id in batch
                    ])
                    .on_conflict_do_update(
                        index_elements=['seed_id', 'article_id'],
                        set_={'depth': depth},
                        where=seed_nodes.c.depth > depth
                    )
                )

        conn.execute(
            sa.update(articles)
            .where(articles.c.id == parent_id)
            .values(scanned=True)
        )

        conn.execute(
            sa.update(seed_nodes)
            .where(
                seed_nodes.c.seed_id == seed_id,
                seed_nodes.c.article_id == parent_id
            )
            .values(expanded=True)
        )


def crawl(zim, seed_entry, seed_id, max_depth):
    depth = 1
    frontier = {seed_entry}
    visited = {seed_entry}
    article_ids = {}

    while frontier and depth < max_depth:
        next_frontier = set()
        uncached = frontier - article_ids.keys()

        if uncached:
            with engine.connect() as conn:
                for batch in batches(uncached, 30000):
                    rows = conn.execute(
                        sa.select(articles.c.path, articles.c.id)
                        .where(articles.c.path.in_(batch))
                    )
                    article_ids.update(rows.tuples().all())

        for path in frontier:
            parent_id = article_ids[path]
            children = get_stored_children(parent_id)

            if children is None:
                children = get_children(zim, path)

            store_children(parent_id, children, seed_id, depth + 1)
            new_children = children - visited
            next_frontier.update(new_children)
            visited.update(new_children)

        frontier = next_frontier
        depth += 1


def main():
    process = psutil.Process(os.getpid())
    start = perf_counter()
    tracemalloc.start()

    current, peak = tracemalloc.get_traced_memory()
    print(f"Current: {current / 1024 ** 2:.2f} MiB")
    print(f"Peak: {peak / 1024 ** 2:.2f} MiB")
    print(f"RSS: {process.memory_info().rss / 1024 ** 2:.2f} MiB")

    zim = Archive(zim_path)
    seed = sys.argv[1] if len(sys.argv) > 1 else input('Seed article: ').strip()
    max_depth = int(sys.argv[2] if len(sys.argv) > 2 else input('Maximum depth: ').strip())

    try:
        seed_entry = resolve_path(zim, zim.get_entry_by_path(seed))
    except KeyError:
        seed_entry = resolve_path(zim, zim.get_entry_by_path(
            input('That was not a valid seed. Try something useful (e.g. Mathematics): ').strip()))

    with engine.begin() as conn:
        conn.execute(
            insert(articles).values(
                path=seed_entry, scanned=False
            ).on_conflict_do_nothing(index_elements=['path'])
        )

    with engine.begin() as conn:
        article_id = conn.execute(
            articles.select().with_only_columns(articles.c.id).where(articles.c.path == seed_entry)
        ).scalar_one()

        conn.execute(
            insert(seeds).values(article_id=article_id, max_depth=max_depth).on_conflict_do_update(
                index_elements=['article_id'],
                set_={'max_depth': max_depth},
                where=seeds.c.max_depth < max_depth
            )
        )

        seed_id = conn.execute(
            sa.select(seeds.c.id).where(seeds.c.article_id == article_id)
        ).scalar_one()

        conn.execute(
            insert(seed_nodes).values(
                seed_id=seed_id,
                article_id=article_id,
                depth=1,
                expanded=False
            ).on_conflict_do_nothing(
                index_elements=['seed_id', 'article_id']
            )
        )

    crawl(zim, seed_entry, seed_id, max_depth)

    current, peak = tracemalloc.get_traced_memory()
    print(f"Current: {current / 1024 ** 2:.2f} MiB")
    print(f"Peak: {peak / 1024 ** 2:.2f} MiB")
    print(f"RSS: {process.memory_info().rss / 1024 ** 2:.2f} MiB")
    print(f'Elapsed: {perf_counter() - start:.3f} seconds')


if __name__ == '__main__':
    main()
