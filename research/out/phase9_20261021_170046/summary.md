# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.469 [0.442, 0.500] | -0.00012 [-0.00019, -0.00005] | -0.125 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.525 [0.497, 0.553] | 0.00002 [-0.00006, 0.00009] | 0.018 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.494 [0.467, 0.524] | -0.00016 [-0.00027, -0.00003] | -0.087 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.508 [0.478, 0.539] | 0.00001 [-0.00012, 0.00014] | 0.008 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.507 [0.479, 0.537] | 0.00006 [-0.00030, 0.00045] | 0.012 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.495 [0.467, 0.523] | -0.00025 [-0.00060, 0.00012] | -0.047 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 8 | 2 | 6 | -1.67667 | 0.66404 | 16.94% |
| momentum | $100 | 11 | 3 | 8 | -18.98536 | 9.40913 | 21.22% |
| momentum | $1000 | 11 | 3 | 8 | -198.38137 | 97.09759 | 22.09% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 13 | 3 | 10 | -1.83028 | 1.07674 | 18.30% |
| random | $100 | 21 | 4 | 17 | -27.34488 | 16.78469 | 30.23% |
| random | $1000 | 21 | 4 | 17 | -285.20423 | 176.15731 | 31.40% |
