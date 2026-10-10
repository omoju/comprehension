# Report · Guarding withBase and withoutBase against false prefix matches · reader: reviewer

Change 5fb179d → cb6af4e · model: claude-cli (its default model)

| # | chapter | kind | words | citations | proof on head | proof on base | repairs | errors | time | cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [01-withbase-where-nothing-should-change.md](01-withbase-where-nothing-should-change.md) | preserved | 516 | 5 | pass | pass | 0 | 0 | 36s | $0.45 |
| 2 | [02-withbase-stops-dropping-the-base-on-a-false-prefix.md](02-withbase-stops-dropping-the-base-on-a-false-prefix.md) | changed | 468 | 3 | pass | fail: AssertionError("expected '/admin-dashboard' to be '/admin/admin-dashboard' | 0 | 0 | 34s | $0.45 |
| 3 | [03-withoutbase-where-nothing-should-change.md](03-withoutbase-where-nothing-should-change.md) | preserved | 594 | 4 | pass | pass | 0 | 0 | 48s | $0.49 |
| 4 | [04-withoutbase-stops-mangling-a-false-prefix.md](04-withoutbase-stops-mangling-a-false-prefix.md) | changed | 568 | 3 | pass | fail: AssertionError("expected '/-dashboard' to be '/admin-dashboard' // Object. | 0 | 0 | 31s | $0.45 |

**Total:** $1.85, 149s, 0 repairs

