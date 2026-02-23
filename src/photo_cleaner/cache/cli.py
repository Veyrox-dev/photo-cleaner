"""
Cache Management CLI and utilities for PhotoCleaner.

Provides command-line interface for:
- Viewing cache statistics
- Clearing cache (all or by age)
- Force re-analysis
- Cache health checks
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import sqlite3

from photo_cleaner.cache.image_cache_manager import ImageCacheManager, CacheQueryBuilder
from photo_cleaner.db.schema import Database


def format_cache_stats(cache_manager: ImageCacheManager) -> str:
    """Format cache statistics for display."""
    size_info = cache_manager.get_cache_size()
    stats = cache_manager.get_cache_stats()
    
    lines = [
        "=" * 60,
        "IMAGE CACHE STATISTICS",
        "=" * 60,
        f"Total entries:        {size_info['entries']}",
        f"Average quality:      {size_info['avg_quality_score']:.2f}",
        f"Top-N entries:        {size_info['top_n_entries']}",
        f"Oldest entry:         {size_info['oldest_entry'] or 'N/A'}",
        f"Newest entry:         {size_info['newest_entry'] or 'N/A'}",
        "",
        "SESSION STATISTICS",
        "-" * 60,
        f"Cache hits:           {stats.cache_hits}",
        f"Cache misses:         {stats.cache_misses}",
        f"Cache updates:        {stats.cache_updates}",
        f"Cache clears:         {stats.cache_clears}",
    ]
    
    if stats.cache_hits + stats.cache_misses > 0:
        hit_rate = stats.cache_hits / (stats.cache_hits + stats.cache_misses) * 100
        lines.append(f"Hit rate:             {hit_rate:.1f}%")
    
    if stats.total_time_saved_seconds > 0:
        lines.append(f"Time saved:           {stats.total_time_saved_seconds:.1f}s")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def cmd_show_stats(db_path: Path) -> int:
    """Show cache statistics."""
    try:
        conn = sqlite3.connect(str(db_path))
        cache = ImageCacheManager(conn)
        
        print(format_cache_stats(cache))
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_clear_all(db_path: Path, confirm: bool = False) -> int:
    """Clear entire cache."""
    try:
        if not confirm:
            print("Cache will be cleared completely.")
            print("This will require re-analysis of all images on next scan.")
            response = input("Continue? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("Cancelled.")
                return 0
        
        conn = sqlite3.connect(str(db_path))
        cache = ImageCacheManager(conn)
        
        cleared = cache.clear_cache(older_than_days=None)
        print(f"✓ Cleared {cleared} cache entries")
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_clear_old(db_path: Path, days: int = 30, confirm: bool = False) -> int:
    """Clear cache entries older than N days."""
    try:
        if not confirm:
            print(f"Cache entries older than {days} days will be cleared.")
            response = input("Continue? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("Cancelled.")
                return 0
        
        conn = sqlite3.connect(str(db_path))
        cache = ImageCacheManager(conn)
        
        cleared = cache.clear_cache(older_than_days=days)
        print(f"✓ Cleared {cleared} cache entries older than {days} days")
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_query_quality_range(
    db_path: Path,
    min_score: float,
    max_score: float,
) -> int:
    """Query cache entries by quality score range."""
    try:
        conn = sqlite3.connect(str(db_path))
        query_builder = CacheQueryBuilder(conn)
        
        entries = query_builder.get_entries_by_quality_range(min_score, max_score)
        
        print(f"Entries with quality score {min_score}-{max_score}:")
        print("-" * 60)
        
        if not entries:
            print("No entries found")
        else:
            for entry in entries[:20]:  # Show first 20
                print(f"  Hash:      {entry['hash'][:16]}...")
                print(f"  Quality:   {entry['quality_score']:.2f}")
                print(f"  Top-N:     {entry['top_n_flag']}")
                print()
        
        if len(entries) > 20:
            print(f"... and {len(entries) - 20} more entries")
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_query_top_n(db_path: Path, limit: int = 10) -> int:
    """Query top-N flagged entries."""
    try:
        conn = sqlite3.connect(str(db_path))
        query_builder = CacheQueryBuilder(conn)
        
        entries = query_builder.get_top_n_entries(limit=limit)
        
        print(f"Top-N flagged entries (limit {limit}):")
        print("-" * 60)
        
        if not entries:
            print("No top-N entries found")
        else:
            for i, entry in enumerate(entries, 1):
                print(f"{i}. Hash:      {entry['hash'][:16]}...")
                print(f"   Quality:   {entry['quality_score']:.2f}")
                print()
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PhotoCleaner Image Cache Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show cache statistics
  python -m photo_cleaner.cache.cli --db db.sqlite show-stats
  
  # Clear entire cache
  python -m photo_cleaner.cache.cli --db db.sqlite clear-all --yes
  
  # Clear entries older than 30 days
  python -m photo_cleaner.cache.cli --db db.sqlite clear-old --days 30
  
  # Query entries by quality score
  python -m photo_cleaner.cache.cli --db db.sqlite query-quality --min 80 --max 95
  
  # Show top-N entries
  python -m photo_cleaner.cache.cli --db db.sqlite query-top-n --limit 5
        """,
    )
    
    parser.add_argument(
        "--db",
        type=Path,
        required=True,
        help="Path to PhotoCleaner database",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # show-stats command
    show_stats_parser = subparsers.add_parser(
        "show-stats",
        help="Show cache statistics",
    )
    
    # clear-all command
    clear_all_parser = subparsers.add_parser(
        "clear-all",
        help="Clear entire cache",
    )
    clear_all_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation",
    )
    
    # clear-old command
    clear_old_parser = subparsers.add_parser(
        "clear-old",
        help="Clear entries older than N days",
    )
    clear_old_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Age threshold in days (default: 30)",
    )
    clear_old_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation",
    )
    
    # query-quality command
    query_quality_parser = subparsers.add_parser(
        "query-quality",
        help="Query entries by quality score range",
    )
    query_quality_parser.add_argument(
        "--min",
        type=float,
        default=0.0,
        help="Minimum quality score (default: 0.0)",
    )
    query_quality_parser.add_argument(
        "--max",
        type=float,
        default=100.0,
        help="Maximum quality score (default: 100.0)",
    )
    
    # query-top-n command
    query_top_n_parser = subparsers.add_parser(
        "query-top-n",
        help="Query top-N flagged entries",
    )
    query_top_n_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of entries to show (default: 10)",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if not args.db.exists():
        print(f"Error: Database not found: {args.db}", file=sys.stderr)
        return 1
    
    # Execute command
    if args.command == "show-stats":
        return cmd_show_stats(args.db)
    elif args.command == "clear-all":
        return cmd_clear_all(args.db, confirm=args.yes)
    elif args.command == "clear-old":
        return cmd_clear_old(args.db, days=args.days, confirm=args.yes)
    elif args.command == "query-quality":
        return cmd_query_quality_range(args.db, args.min, args.max)
    elif args.command == "query-top-n":
        return cmd_query_top_n(args.db, limit=args.limit)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
