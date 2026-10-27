# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `10080`
Windows: `2`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 9462 | 0.487 [0.477, 0.497] | -0.00002 [-0.00005, 0.00001] | -0.016 |
| news | 0 | — | — | — |
| random | 9480 | 0.507 [0.498, 0.517] | 0.00003 [0.00000, 0.00006] | 0.030 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 9462 | 0.485 [0.476, 0.495] | -0.00011 [-0.00017, -0.00004] | -0.055 |
| news | 0 | — | — | — |
| random | 9480 | 0.493 [0.483, 0.502] | -0.00003 [-0.00009, 0.00003] | -0.014 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 9462 | 0.519 [0.509, 0.530] | -0.00001 [-0.00012, 0.00010] | -0.002 |
| news | 0 | — | — | — |
| random | 9480 | 0.501 [0.490, 0.510] | -0.00001 [-0.00013, 0.00012] | -0.003 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 1 | 0 | 1 | -2.02773 | 0.08442 | 20.28% |
| momentum | $100 | 1 | 0 | 1 | -22.30500 | 0.92864 | 22.31% |
| momentum | $1000 | 1 | 0 | 1 | -237.24414 | 9.87740 | 23.72% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 1 | 0 | 1 | -2.08176 | 0.08405 | 20.82% |
| random | $100 | 1 | 0 | 1 | -22.89932 | 0.92450 | 22.90% |
| random | $1000 | 1 | 0 | 1 | -243.56547 | 9.83335 | 24.36% |
