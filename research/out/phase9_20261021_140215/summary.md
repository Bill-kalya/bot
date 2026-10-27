# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.464 [0.435, 0.492] | -0.00014 [-0.00023, -0.00005] | -0.130 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.527 [0.497, 0.554] | 0.00003 [-0.00006, 0.00012] | 0.032 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.503 [0.472, 0.535] | -0.00017 [-0.00030, -0.00003] | -0.089 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.507 [0.479, 0.535] | 0.00001 [-0.00012, 0.00014] | 0.006 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.493 [0.464, 0.522] | -0.00022 [-0.00046, 0.00003] | -0.060 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.512 [0.484, 0.541] | 0.00009 [-0.00015, 0.00034] | 0.026 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 10 | 3 | 7 | -1.92096 | 0.82928 | 21.61% |
| momentum | $100 | 10 | 3 | 7 | -20.50259 | 8.78819 | 23.31% |
| momentum | $1000 | 10 | 3 | 7 | -212.09794 | 90.78587 | 24.00% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 8 | 1 | 7 | -1.74590 | 0.66205 | 17.46% |
| random | $100 | 21 | 4 | 17 | -34.10665 | 16.16987 | 34.11% |
| random | $1000 | 21 | 4 | 17 | -350.45220 | 168.58170 | 35.05% |
