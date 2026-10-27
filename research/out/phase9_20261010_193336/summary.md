# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.470 [0.442, 0.500] | -0.00001 [-0.00005, 0.00002] | -0.032 |
| news | 0 | — | — | — |
| random | 1140 | 0.518 [0.489, 0.546] | 0.00004 [0.00000, 0.00007] | 0.081 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.433 [0.406, 0.462] | -0.00022 [-0.00027, -0.00016] | -0.266 |
| news | 0 | — | — | — |
| random | 1140 | 0.511 [0.482, 0.540] | 0.00002 [-0.00003, 0.00009] | 0.027 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.481 [0.453, 0.508] | -0.00017 [-0.00026, -0.00008] | -0.127 |
| news | 0 | — | — | — |
| random | 1140 | 0.510 [0.482, 0.541] | 0.00000 [-0.00009, 0.00010] | 0.001 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
