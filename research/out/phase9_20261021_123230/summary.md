# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `43200`
Windows: `5`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.477 [0.471, 0.481] | -0.00004 [-0.00006, -0.00002] | -0.033 |
| news | 163 | 0.411 [0.337, 0.485] | -0.00010 [-0.00037, 0.00019] | -0.072 |
| random | 41700 | 0.500 [0.495, 0.505] | 0.00001 [-0.00001, 0.00002] | 0.006 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.486 [0.481, 0.491] | -0.00009 [-0.00012, -0.00005] | -0.038 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00003 [-0.00034, 0.00031] | -0.016 |
| random | 41700 | 0.502 [0.497, 0.506] | 0.00000 [-0.00003, 0.00004] | 0.002 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.489 [0.484, 0.493] | -0.00017 [-0.00023, -0.00011] | -0.037 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00315 [-0.00433, -0.00194] | -0.464 |
| random | 41700 | 0.503 [0.498, 0.508] | 0.00004 [-0.00002, 0.00011] | 0.010 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 2 | 0 | 2 | -3.84768 | 0.16770 | 38.48% |
| momentum | $100 | 9 | 1 | 8 | -83.08685 | 4.06317 | 83.09% |
| momentum | $1000 | 8 | 1 | 7 | -807.83756 | 41.14219 | 80.78% |
| news | $10 | 1 | 0 | 1 | -1.93385 | 0.08451 | 19.34% |
| news | $100 | 2 | 0 | 2 | -38.60282 | 1.69943 | 38.60% |
| news | $1000 | 2 | 0 | 2 | -401.50725 | 17.66934 | 40.15% |
| random | $10 | 1 | 0 | 1 | -2.02673 | 0.08412 | 20.27% |
| random | $100 | 6 | 2 | 4 | -29.78895 | 4.50090 | 50.43% |
| random | $1000 | 6 | 2 | 4 | -346.74694 | 46.46663 | 53.42% |
