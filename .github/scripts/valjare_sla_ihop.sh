#!/usr/bin/env bash
# Slår ihop väljardatabasens arbetsgren med main efter varje körning på grenen.
# Koden och den nybyggda datan från grenen vinner vid konflikt, utom nyhetsartiklarna:
# de samlas in på båda grenarna och slås ihop (union), så att ingen historik går förlorad.
set -euo pipefail
GREN="claude/voter-database-demographics-r9y5la"
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
for forsok in 1 2 3; do
  git fetch -q origin main "$GREN"
  git checkout -q -B sla-ihop origin/main
  git merge -q --no-ff -X theirs "origin/$GREN" -m "Auto: slå ihop väljardatabasen med main"
  if git cat-file -e origin/main:valjare/data/media/artiklar.csv.gz 2>/dev/null; then
    git show origin/main:valjare/data/media/artiklar.csv.gz > /tmp/artiklar_main.csv.gz
    python - <<'PY'
import pandas as pd
from pathlib import Path
f = Path("valjare/data/media/artiklar.csv.gz")
delar = [pd.read_csv("/tmp/artiklar_main.csv.gz", dtype=str)]
if f.exists():
    delar.append(pd.read_csv(f, dtype=str))
d = pd.concat(delar, ignore_index=True).sort_values("hamtad", na_position="last")
d = d.drop_duplicates(["flode", "sokt_parti", "lank"], keep="first")
f.parent.mkdir(parents=True, exist_ok=True)
d.to_csv(f, index=False, compression={"method": "gzip", "mtime": 0})
print(f"artiklar efter sammanslagning: {len(d)}")
PY
    git add valjare/data/media/artiklar.csv.gz
    if ! git diff --cached --quiet; then
      # Lägg unionen i sammanslagningscommiten; finns ingen (main var redan à jour), gör en ny commit
      if [ "$(git rev-list --parents -n 1 HEAD | wc -w)" -gt 2 ]; then git commit -q --amend --no-edit
      else git commit -q -m "Auto: slå ihop nyhetsartiklar från väljardatabasens gren"; fi
    fi
  fi
  if git push -q origin HEAD:main; then
    echo "Grenen är ihopslagen med main"
    exit 0
  fi
  echo "Main har ändrats under tiden, försöker igen ($forsok)"
  sleep $((forsok * 5))
done
exit 1
