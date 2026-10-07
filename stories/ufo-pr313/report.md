# Report · A base of "/admin" no longer claims "/admin-dashboard" · reader: reviewer

Change 5fb179d → cb6af4e · model: claude-cli (claude-opus-5-5)

| # | chapter | kind | words | citations | proof on head | proof on base | repairs | errors | time | cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [01-removing-the-base-no-longer-cuts-admin-out-of-admi.md](01-removing-the-base-no-longer-cuts-admin-out-of-admi.md) | changed | 464 | 6 | pass | fail: AssertionError("expected '/-dashboard' to be '/admin-dashboard' // Object. | 0 | 0 | 22s | $0.34 |
| 2 | [02-adding-the-base-now-prefixes-admin-dashboard-inste.md](02-adding-the-base-now-prefixes-admin-dashboard-inste.md) | changed | 447 | 7 | pass | fail: AssertionError("expected '/admin-dashboard' to be '/admin/admin-dashboard' | 0 | 0 | 23s | $0.34 |
| 3 | [03-genuine-base-matches-including-a-query-right-after.md](03-genuine-base-matches-including-a-query-right-after.md) | preserved | 457 | 6 | pass | pass | 0 | 0 | 35s | $0.35 |
| 4 | [04-inputs-that-already-carry-the-base-are-still-left-.md](04-inputs-that-already-carry-the-base-are-still-left-.md) | preserved | 485 | 6 | pass | pass | 0 | 0 | 31s | $0.35 |

**Total:** $1.39, 111s, 0 repairs

