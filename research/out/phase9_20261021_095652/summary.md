# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `43200`
Windows: `5`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41669 | 0.478 [0.473, 0.483] | -0.00003 [-0.00005, -0.00002] | -0.029 |
| news | 163 | 0.411 [0.337, 0.485] | -0.00010 [-0.00037, 0.00019] | -0.072 |
| random | 41700 | 0.500 [0.495, 0.505] | 0.00001 [-0.00001, 0.00002] | 0.005 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41669 | 0.487 [0.482, 0.492] | -0.00009 [-0.00012, -0.00005] | -0.037 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00003 [-0.00034, 0.00031] | -0.016 |
| random | 41700 | 0.501 [0.496, 0.506] | -0.00000 [-0.00004, 0.00003] | -0.001 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41669 | 0.489 [0.484, 0.493] | -0.00017 [-0.00022, -0.00010] | -0.036 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00315 [-0.00433, -0.00194] | -0.464 |
| random | 41700 | 0.503 [0.498, 0.508] | 0.00005 [-0.00002, 0.00011] | 0.010 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 1 | 0 | 1 | -2.26213 | 0.08358 | 22.62% |
| momentum | $100 | 6 | 0 | 6 | -78.49189 | 3.17055 | 78.49% |
| momentum | $1000 | 6 | 0 | 6 | -810.54697 | 32.54290 | 81.05% |
| news | $10 | 1 | 0 | 1 | -1.93385 | 0.08451 | 19.34% |
| news | $100 | 2 | 0 | 2 | -38.60282 | 1.69943 | 38.60% |
| news | $1000 | 2 | 0 | 2 | -401.50725 | 17.66934 | 40.15% |
| random | $10 | 1 | 0 | 1 | -2.31848 | 0.08349 | 23.18% |
| random | $100 | 6 | 2 | 4 | -35.70642 | 4.40064 | 52.35% |
| random | $1000 | 6 | 2 | 4 | -380.34667 | 44.92423 | 54.89% |
