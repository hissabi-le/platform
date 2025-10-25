#!/usr/bin/env python3
"""
Print a directory tree (default: current dir) with useful defaults for Next.js apps.
Skips: node_modules, .next, .git, .turbo, .vercel by default.
Usage:
  python tree.py web-app
  python tree.py web-app -d 2                 # limit depth
  python tree.py web-app -a                   # include hidden files
  python tree.py web-app -x dist build        # add more excludes
"""
import argparse, os, sys

DEFAULT_EXCLUDES = {"node_modules", ".next", ".git", ".turbo", ".vercel"}

def print_tree(root: str, max_depth: int | None, show_hidden: bool, extra_excludes: set[str]):
    root = os.path.abspath(root)
    excludes = DEFAULT_EXCLUDES | extra_excludes

    def is_excluded(name: str) -> bool:
        return name in excludes

    def walk(dir_path: str, prefix: str = "", depth: int = 0):
        if max_depth is not None and depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            print(prefix + "└── [permission denied]")
            return

        # filter
        filtered = []
        for name in entries:
            if not show_hidden and name.startswith(".") and name not in {".next", ".git"}:
                continue
            if is_excluded(name):
                continue
            filtered.append(name)

        for i, name in enumerate(filtered):
            path = os.path.join(dir_path, name)
            connector = "└── " if i == len(filtered) - 1 else "├── "
            print(prefix + connector + name)
            if os.path.isdir(path):
                extension = "    " if i == len(filtered) - 1 else "│   "
                walk(path, prefix + extension, depth + 1)

    print(os.path.basename(root) or root)
    walk(root, "", 1)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default=".", help="Root path to print")
    p.add_argument("-d", "--depth", type=int, default=None, help="Max depth (e.g. 2)")
    p.add_argument("-a", "--all", action="store_true", help="Show hidden files/dirs")
    p.add_argument("-x", "--exclude", nargs="*", default=[], help="Additional names to exclude")
    args = p.parse_args()

    if not os.path.exists(args.path):
        print(f"Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    print_tree(args.path, args.depth, args.all, set(args.exclude))

if __name__ == "__main__":
    main()

