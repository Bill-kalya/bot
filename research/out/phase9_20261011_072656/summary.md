# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `43200`
Windows: `5`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.479 [0.475, 0.484] | -0.00002 [-0.00003, 0.00000] | -0.013 |
| news | 163 | 0.411 [0.337, 0.485] | -0.00010 [-0.00037, 0.00019] | -0.072 |
| random | 41700 | 0.501 [0.496, 0.506] | 0.00001 [-0.00001, 0.00003] | 0.009 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.479 [0.475, 0.484] | -0.00008 [-0.00012, -0.00005] | -0.035 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00003 [-0.00034, 0.00031] | -0.016 |
| random | 41700 | 0.500 [0.495, 0.505] | 0.00000 [-0.00003, 0.00004] | 0.002 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.495 [0.490, 0.500] | -0.00005 [-0.00012, 0.00001] | -0.011 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00315 [-0.00433, -0.00194] | -0.464 |
| random | 41700 | 0.502 [0.497, 0.507] | 0.00004 [-0.00003, 0.00011] | 0.007 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 2 | 0 | 2 | -3.59515 | 0.15308 | 35.95% |
| momentum | $100 | 9 | 3 | 6 | -46.81449 | 8.03939 | 64.63% |
| momentum | $1000 | 9 | 3 | 6 | -504.94045 | 84.00620 | 67.44% |
| news | $10 | 1 | 0 | 1 | -1.93385 | 0.08451 | 19.34% |
| news | $100 | 2 | 0 | 2 | -38.60282 | 1.69943 | 38.60% |
| news | $1000 | 2 | 0 | 2 | -401.50725 | 17.66934 | 40.15% |
| random | $10 | 2 | 0 | 2 | -3.62827 | 0.15654 | 36.28% |
| random | $100 | 16 | 4 | 12 | -82.87545 | 5.79487 | 86.06% |
| random | $1000 | 16 | 4 | 12 | -832.72982 | 61.53426 | 87.73% |
