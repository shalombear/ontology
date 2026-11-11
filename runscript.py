import sys
import re
import posixpath
import tracemalloc
from pathlib import Path
from time import perf_counter
from urllib.parse import unquote

import sqlalchemy as sa
from bs4 import BeautifulSoup
from libzim.reader import Archive
from sqlalchemy.dialects.sqlite import insert

from database import engine, articles, edges, seeds, seed_nodes, db_path

projects = Path(__file__).resolve().parent.parent
zim_path = projects / 'data' / 'wiki' / 'wikipedia_en_all_nopic_2026-06.zim'

benchmark = {
    'zim_operations': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'articles_visited': 0,
    'edges_processed': 0,
    'sql_reads': 0,
    'sql_writes': 0,
    'zim_time': 0.0,
    'parse_time': 0.0,
    'sql_read_time': 0.0,
    'sql_write_time': 0.0,
    'sql_transaction_time': 0.0,
    'link_processing_time': 0.0,
    'frontier_sizes': {}
}

drops = '.hatnote, .sidebar, .navbox, .mw-references-wrap, .mw-cite-backlink, .mw-editsection, .navbox-styles'
drops += ', .reference, .cite-bracket, .Z3988, .refbegin, .toclimit-3, style, .mw-empty-elt, .reflist'
drops += ', .references, .mw-references, .external-links, .authority-control, .sistersitebox, .metadata'
drops += ', .ambox, .ombox, .vertical-navbox, .infobox'


def resolve_path(zim, entry):
    if entry.is_redirect:
        start = perf_counter()
        target_entry = entry.get_redirect_entry()
        benchmark['zim_operations'] += 1
        benchmark['zim_time'] += perf_counter() - start
        return resolve_path(zim, target_entry)

    start = perf_counter()
    content = entry.get_item().content
    benchmark['zim_operations'] += 1
    benchmark['zim_time'] += perf_counter() - start
    if b'http-equiv="refresh"' in bytes(content[:512]):
        start_parse = perf_counter()
        soup = BeautifulSoup(bytes(content), 'html.parser')
        refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        benchmark['parse_time'] += perf_counter() - start_parse

        if refresh:
            target = re.search(rb"""URL='(.*?)'" />""", bytes(content)).group(1).decode('utf-8')
            target = unquote(target.split('#', 1)[0])
            trailing_slash = target.endswith('/')
            target = posixpath.normpath(posixpath.join(posixpath.dirname(entry.path), target)).lstrip('/')
            target += '/' if trailing_slash and not target.endswith('/') else ''

            start = perf_counter()
            target_entry = zim.get_entry_by_path(target)
            benchmark['zim_operations'] += 1
            benchmark['zim_time'] += perf_counter() - start
            return resolve_path(zim, target_entry)

    return entry.path


def batches(items, size=1000):
    items = list(items)

    for i in range(0, len(items), size):
        yield items[i:i+size]


def get_children(zim, path):
    zim_start = perf_counter()
    entry = zim.get_entry_by_path(path)
    benchmark['zim_operations'] += 1
    benchmark['zim_time'] += perf_counter() - zim_start

    path = resolve_path(zim, entry)

    start = perf_counter()
    entry = zim.get_entry_by_path(path)
    benchmark['zim_operations'] += 1
    benchmark['zim_time'] += perf_counter() - start

    start = perf_counter()
    html = bytes(entry.get_item().content).decode('utf-8')
    benchmark['zim_operations'] += 1
    benchmark['zim_time'] += perf_counter() - start
    start = perf_counter()
    soup = BeautifulSoup(html, 'html.parser')
    article = soup.select_one('#mw-content-text .mw-parser-output')
    benchmark['parse_time'] += perf_counter() - start

    if article is None:
        if soup.select_one('link[href$="download_error_placeholder.css"]'):
            print(f'ZIM article unavailable: {path}', flush=True)
            return set()

        print(f'\nExtraction Failed: {path}')
        print(f'MIME type: {entry.get_item().mimetype}')
        print(f'HTML length: {len(html)}')
        print(f'Page title: {soup.title}')
        print(f'Head: {soup.head}')
        print(f'Body: {soup.body}')
        raise RuntimeError(f'Article container missing: {path}')

    start = perf_counter()
    for element in article.select(drops):
        element.decompose()

    links = [
        link for link in article.find_all('a', href=True)
        if not link['href'].startswith(('#', 'http:', 'https:', '//'))
        and 'external' not in link.get('class', [])
    ]
    paths = {unquote(link['href'].split('#', 1)[0]) for link in links}

    resolved_paths = set()

    for child_path in paths:
        zim_start = perf_counter()
        exists = zim.has_entry_by_path(child_path)
        benchmark['zim_operations'] += 1
        benchmark['zim_time'] += perf_counter() - zim_start

        if exists:
            zim_start = perf_counter()
            child_entry = zim.get_entry_by_path(child_path)
            benchmark['zim_operations'] += 1
            benchmark['zim_time'] += perf_counter() - zim_start

            resolved_paths.add(resolve_path(zim, child_entry))

    resolved_paths.discard(path)
    benchmark['link_processing_time'] += perf_counter() - start

    return resolved_paths


def get_stored_children(parent_id):
    with engine.connect() as conn:
        start = perf_counter()
        scanned = conn.execute(
            sa.select(articles.c.scanned)
            .where(articles.c.id == parent_id)
        ).scalar_one()

        if not scanned:
            benchmark['cache_misses'] += 1
            benchmark['sql_reads'] += 1
            benchmark['sql_read_time'] += perf_counter() - start
            return None
        else:
            benchmark['cache_hits'] += 1

        rows = conn.execute(
            sa.select(articles.c.path).select_from(
                edges.join(
                    articles, edges.c.child_id == articles.c.id
                )
            ).where(edges.c.parent_id == parent_id)
        )
        children = set(rows.scalars())
        benchmark['sql_reads'] += 2
        benchmark['sql_read_time'] += perf_counter() - start

        return children


def store_children(parent_id, children, seed_id, depth):
    start = perf_counter()
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
                benchmark['sql_writes'] += 1

            child_ids = {}
            for batch in batches(children, 30000):
                start_read = perf_counter()
                rows = conn.execute(
                    sa.select(articles.c.path, articles.c.id)
                    .where(articles.c.path.in_(batch))
                )
                benchmark['sql_reads'] += 1

                child_ids.update(rows.tuples().all())
                benchmark['sql_read_time'] += perf_counter() - start_read

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
                benchmark['sql_writes'] += 1

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
                benchmark['sql_writes'] += 1

        conn.execute(
            sa.update(articles)
            .where(articles.c.id == parent_id)
            .values(scanned=True)
        )
        benchmark['sql_writes'] += 1

        conn.execute(
            sa.update(seed_nodes)
            .where(
                seed_nodes.c.seed_id == seed_id,
                seed_nodes.c.article_id == parent_id
            )
            .values(expanded=True)
        )
        benchmark['sql_writes'] += 1

    benchmark['sql_transaction_time'] += perf_counter() - start


def crawl(zim, seed_entry, seed_id, max_depth):
    depth = 1
    frontier = {seed_entry}
    visited = {seed_entry}
    article_ids = {}

    while frontier and depth < max_depth:
        benchmark['frontier_sizes'][depth] = len(frontier)
        next_frontier = set()
        uncached = frontier - article_ids.keys()

        if uncached:
            start = perf_counter()
            with engine.connect() as conn:
                for batch in batches(uncached, 30000):
                    rows = conn.execute(
                        sa.select(articles.c.path, articles.c.id)
                        .where(articles.c.path.in_(batch))
                    )
                    article_ids.update(rows.tuples().all())
                    benchmark['sql_reads'] += 1
            benchmark['sql_read_time'] += perf_counter() - start

        for path in frontier:
            benchmark['articles_visited'] += 1
            parent_id = article_ids[path]
            children = get_stored_children(parent_id)

            if children is None:
                children = get_children(zim, path)

            store_children(parent_id, children, seed_id, depth + 1)
            benchmark['edges_processed'] += len(children)
            new_children = children - visited
            next_frontier.update(new_children)
            visited.update(new_children)

        frontier = next_frontier
        depth += 1


def main():
    start = perf_counter()
    tracemalloc.start()

    zim = Archive(zim_path)
    seed = sys.argv[1] if len(sys.argv) > 1 else input('Seed article: ').strip()
    max_depth = int(sys.argv[2] if len(sys.argv) > 2 else input('Maximum depth: ').strip())

    try:
        start_zim = perf_counter()
        entry = zim.get_entry_by_path(seed)
        benchmark['zim_operations'] += 1
        benchmark['zim_time'] += perf_counter() - start_zim
        seed_entry = resolve_path(zim, entry)
    except KeyError:
        seed = input('That was not a valid seed. Try something useful (e.g. Mathematics): ').strip()
        start_zim = perf_counter()
        entry = zim.get_entry_by_path(seed)
        benchmark['zim_operations'] += 1
        benchmark['zim_time'] += perf_counter() - start_zim
        seed_entry = resolve_path(zim, entry)

    start_sql = perf_counter()
    with engine.begin() as conn:
        conn.execute(
            insert(articles).values(
                path=seed_entry, scanned=False
            ).on_conflict_do_nothing(index_elements=['path'])
        )
        benchmark['sql_writes'] += 1
    benchmark['sql_transaction_time'] += perf_counter() - start_sql

    start_sql = perf_counter()
    with engine.begin() as conn:
        start_read = perf_counter()
        article_id = conn.execute(
            articles.select().with_only_columns(articles.c.id).where(articles.c.path == seed_entry)
        ).scalar_one()
        benchmark['sql_reads'] += 1
        benchmark['sql_read_time'] += perf_counter() - start_read

        start_write = perf_counter()
        conn.execute(
            insert(seeds).values(article_id=article_id, max_depth=max_depth).on_conflict_do_update(
                index_elements=['article_id'],
                set_={'max_depth': max_depth},
                where=seeds.c.max_depth < max_depth
            )
        )
        benchmark['sql_writes'] += 1
        benchmark['sql_write_time'] += perf_counter() - start_write

        start_read = perf_counter()
        seed_id = conn.execute(
            sa.select(seeds.c.id).where(seeds.c.article_id == article_id)
        ).scalar_one()
        benchmark['sql_reads'] += 1
        benchmark['sql_read_time'] += perf_counter() - start_read

        start_write = perf_counter()
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
        benchmark['sql_writes'] += 1
        benchmark['sql_write_time'] += perf_counter() - start_write
    benchmark['sql_transaction_time'] += perf_counter() - start_sql

    crawl(zim, seed_entry, seed_id, max_depth)

    _, peak = tracemalloc.get_traced_memory()

    benchmark['peak_python_mib'] = peak / 1024 ** 2
    benchmark['elapsed_seconds'] = perf_counter() - start
    benchmark['database_bytes'] = db_path.stat().st_size


if __name__ == '__main__':
    main()
