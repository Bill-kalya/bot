# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.470 [0.442, 0.500] | 0.00002 [-0.00010, 0.00015] | 0.015 |
| news | 0 | — | — | — |
| random | 1140 | 0.525 [0.498, 0.554] | 0.00003 [-0.00010, 0.00016] | 0.023 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.517 [0.488, 0.548] | 0.00011 [-0.00013, 0.00035] | 0.040 |
| news | 0 | — | — | — |
| random | 1140 | 0.509 [0.476, 0.538] | 0.00007 [-0.00018, 0.00032] | 0.027 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.495 [0.465, 0.525] | -0.00007 [-0.00037, 0.00022] | -0.018 |
| news | 0 | — | — | — |
| random | 1140 | 0.519 [0.490, 0.551] | 0.00020 [-0.00012, 0.00052] | 0.048 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 1 | 0 | 1 | -1.83632 | 0.08230 | 18.36% |
| random | $100 | 1 | 0 | 1 | -22.03588 | 0.98766 | 22.04% |
| random | $1000 | 1 | 0 | 1 | -224.03149 | 10.04118 | 22.40% |
