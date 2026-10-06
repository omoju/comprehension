# Results · 9 out-of-sample repositories

| | Story | DeepWiki |
|---|---|---|
| contradicted claims / 1k words | 0.71 | 0.54 |
| path questions | 97.9% | 62.7% |
| general questions | 76.2% | 55.7% |

95% CI (repos resampled): density ratio [0.5547368151826412, 4.85729012555935], path diff [22.91666666666667, 47.18309859154929], general diff [5.0, 33.06451612903226]

**Decision by §8: KILL**

- ✗ H1: story density <= 1/2 DeepWiki
- ✓ general: story >= DeepWiki - 5
- ✓ path: story >= DeepWiki + 10

## Per repository

| repo | arm | words | claims | sampled | contradicted | unverifiable | density | path | general | Jev agrees |
|---|---|---|---|---|---|---|---|---|---|---|
| attrs | story | 9,375 | 237 | 40 | 2 | 0 | 1.26 | 100.0% | 71.4% | 38/40 |
| attrs | deepwiki | 14,140 | 363 | 40 | 0 | 8 | 0.00 | 56.2% | 35.7% | 39/40 |
| click | story | 8,601 | 248 | 40 | 1 | 1 | 0.72 | 93.8% | 71.4% | 39/40 |
| click | deepwiki | 33,482 | 558 | 40 | 1 | 8 | 0.42 | 75.0% | 35.7% | 37/40 |
| flask | story | 7,261 | 192 | 40 | 0 | 2 | 0.00 | 93.8% | 41.7% | 40/40 |
| flask | deepwiki | 28,535 | 687 | 40 | 0 | 7 | 0.00 | 75.0% | 58.3% | 39/40 |
| httpx | story | 8,108 | 227 | 40 | 1 | 0 | 0.70 | 93.8% | 78.6% | 40/40 |
| httpx | deepwiki | 27,567 | 725 | 40 | 0 | 5 | 0.00 | 68.8% | 50.0% | 40/40 |
| itsdangerous* | story | 7,707 | 123 | 40 | 0 | 0 | 0.00 | 93.8% | 91.7% | 39/40 |
| itsdangerous* | deepwiki | 12,089 | 291 | 40 | 2 | 0 | 1.20 | 93.8% | 100.0% | 37/40 |
| jinja | story | 8,842 | 210 | 40 | 0 | 0 | 0.00 | 100.0% | 57.1% | 40/40 |
| jinja | deepwiki | 15,506 | 473 | 40 | 1 | 5 | 0.76 | 50.0% | 78.6% | 40/40 |
| markupsafe | story | 5,961 | 97 | 40 | 2 | 1 | 0.81 | 100.0% | 91.7% | 38/40 |
| markupsafe | deepwiki | 31,855 | 312 | 40 | 3 | 1 | 0.73 | 93.8% | 75.0% | 40/40 |
| requests | story | 10,347 | 277 | 40 | 0 | 0 | 0.00 | 100.0% | 100.0% | 39/40 |
| requests | deepwiki | 22,131 | 489 | 40 | 2 | 6 | 1.10 | 64.3% | 71.4% | 38/40 |
| rich | story | 9,560 | 300 | 40 | 3 | 6 | 2.35 | 100.0% | 92.9% | 37/40 |
| rich | deepwiki | 25,426 | 1876 | 40 | 0 | 7 | 0.00 | 37.5% | 64.3% | 40/40 |
| tqdm | story | 8,751 | 177 | 40 | 1 | 0 | 0.51 | 100.0% | 78.6% | 40/40 |
| tqdm | deepwiki | 17,075 | 455 | 40 | 0 | 2 | 0.00 | 43.8% | 35.7% | 39/40 |

\* in-sample, excluded from the decision
