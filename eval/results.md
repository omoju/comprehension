# Results · 9 out-of-sample repositories

| | Story | DeepWiki |
|---|---|---|
| contradicted claims / 1k words | 0.07 | 0.69 |
| path questions | 97.9% | 62.7% |
| general questions | 76.2% | 55.7% |

95% CI (repos resampled): density ratio [0.0, 0.30613736634220484], path diff [22.91666666666667, 47.18309859154929], general diff [5.0, 33.06451612903226]

**Decision by §8: SHIP**

- ✓ H1: story density <= 1/2 DeepWiki
- ✓ general: story >= DeepWiki - 5
- ✓ path: story >= DeepWiki + 10

## Per repository

| repo | arm | words | claims | sampled | contradicted | unverifiable | density | path | general | Jev agrees |
|---|---|---|---|---|---|---|---|---|---|---|
| attrs | story | 9,375 | 237 | 40 | 0 | 32 | 0.00 | 100.0% | 71.4% | 40/40 |
| attrs | deepwiki | 14,140 | 363 | 40 | 0 | 6 | 0.00 | 56.2% | 35.7% | 39/40 |
| click | story | 8,601 | 248 | 40 | 0 | 35 | 0.00 | 93.8% | 71.4% | 40/40 |
| click | deepwiki | 33,482 | 558 | 40 | 2 | 20 | 0.83 | 75.0% | 35.7% | 39/40 |
| flask | story | 7,261 | 192 | 40 | 0 | 35 | 0.00 | 93.8% | 41.7% | 39/40 |
| flask | deepwiki | 28,535 | 687 | 40 | 0 | 19 | 0.00 | 75.0% | 58.3% | 40/40 |
| httpx | story | 8,108 | 227 | 40 | 0 | 18 | 0.00 | 93.8% | 78.6% | 31/31 |
| httpx | deepwiki | 27,567 | 725 | 40 | 3 | 13 | 1.97 | 68.8% | 50.0% | 38/40 |
| itsdangerous* | story | 7,707 | 123 | 40 | 0 | 0 | 0.00 | 93.8% | 91.7% | 39/40 |
| itsdangerous* | deepwiki | 12,089 | 291 | 40 | 2 | 0 | 1.20 | 93.8% | 100.0% | 37/40 |
| jinja | story | 8,842 | 210 | 40 | 0 | 25 | 0.00 | 100.0% | 57.1% | 40/40 |
| jinja | deepwiki | 15,506 | 473 | 40 | 1 | 8 | 0.76 | 50.0% | 78.6% | 39/40 |
| markupsafe | story | 5,961 | 97 | 40 | 1 | 2 | 0.41 | 100.0% | 91.7% | 39/40 |
| markupsafe | deepwiki | 31,855 | 312 | 40 | 3 | 1 | 0.73 | 93.8% | 75.0% | 40/40 |
| requests | story | 10,347 | 277 | 40 | 0 | 34 | 0.00 | 100.0% | 100.0% | 21/21 |
| requests | deepwiki | 22,131 | 489 | 40 | 0 | 11 | 0.00 | 64.3% | 71.4% | 40/40 |
| rich | story | 9,560 | 300 | 40 | 0 | 39 | 0.00 | 100.0% | 92.9% | 15/15 |
| rich | deepwiki | 25,426 | 1876 | 40 | 0 | 40 | 0.00 | 37.5% | 64.3% | 0/0 |
| tqdm | story | 8,751 | 177 | 40 | 0 | 23 | 0.00 | 100.0% | 78.6% | 31/32 |
| tqdm | deepwiki | 17,075 | 455 | 40 | 0 | 19 | 0.00 | 43.8% | 35.7% | 39/40 |

\* in-sample, excluded from the decision
