#!/bin/sh
# Rebuild demo-repos/ from demo-repos.lock: each repo at the exact commit its story cites.
# Repos that already exist are left alone. Run from the project root.
set -e
mkdir -p demo-repos
grep -v '^#' demo-repos.lock | while read -r name url commit; do
  [ -z "$name" ] && continue
  if [ -d "demo-repos/$name/.git" ]; then echo "ok    $name (already present)"; continue; fi
  git init -q "demo-repos/$name"
  git -C "demo-repos/$name" remote add origin "$url"
  git -C "demo-repos/$name" fetch -q --depth 1 origin "$commit"
  git -C "demo-repos/$name" checkout -q FETCH_HEAD
  echo "fetched $name @ $(echo "$commit" | cut -c1-7)"
done
