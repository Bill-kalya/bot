# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.471 [0.442, 0.500] | 0.00002 [-0.00010, 0.00015] | 0.017 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.525 [0.496, 0.553] | 0.00003 [-0.00009, 0.00015] | 0.022 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.514 [0.486, 0.543] | 0.00005 [-0.00018, 0.00030] | 0.018 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.509 [0.479, 0.539] | 0.00009 [-0.00016, 0.00033] | 0.032 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.493 [0.463, 0.522] | -0.00013 [-0.00043, 0.00015] | -0.031 |
| news | 0 | — | — | — |
| news_filtered | 0 | — | — | — |
| random | 1140 | 0.519 [0.490, 0.549] | 0.00021 [-0.00009, 0.00050] | 0.051 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 11 | 3 | 8 | -1.26454 | 0.91202 | 22.91% |
| momentum | $100 | 11 | 3 | 8 | -14.60128 | 10.36209 | 26.36% |
| momentum | $1000 | 11 | 3 | 8 | -157.55962 | 107.68460 | 27.52% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 19 | 4 | 15 | -1.78786 | 1.57273 | 28.17% |
| random | $100 | 21 | 5 | 16 | -21.23525 | 20.20457 | 32.93% |
| random | $1000 | 21 | 5 | 16 | -221.76565 | 210.57965 | 33.97% |
