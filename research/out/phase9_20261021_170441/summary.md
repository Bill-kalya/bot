# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `43200`
Windows: `5`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.478 [0.473, 0.482] | -0.00003 [-0.00005, -0.00002] | -0.027 |
| news | 163 | 0.411 [0.337, 0.485] | -0.00010 [-0.00037, 0.00019] | -0.072 |
| news_filtered | 0 | — | — | — |
| random | 41700 | 0.500 [0.495, 0.505] | 0.00000 [-0.00001, 0.00002] | 0.004 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.486 [0.482, 0.491] | -0.00009 [-0.00012, -0.00005] | -0.038 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00003 [-0.00034, 0.00031] | -0.016 |
| news_filtered | 0 | — | — | — |
| random | 41700 | 0.502 [0.497, 0.506] | -0.00000 [-0.00003, 0.00003] | -0.000 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41668 | 0.491 [0.486, 0.495] | -0.00016 [-0.00022, -0.00011] | -0.035 |
| news | 163 | 0.534 [0.460, 0.607] | -0.00315 [-0.00433, -0.00194] | -0.464 |
| news_filtered | 0 | — | — | — |
| random | 41700 | 0.503 [0.498, 0.508] | 0.00004 [-0.00002, 0.00010] | 0.009 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 13 | 4 | 9 | -2.47237 | 1.10328 | 27.43% |
| momentum | $100 | 134 | 37 | 97 | -92.36925 | 39.32008 | 92.67% |
| momentum | $1000 | 237 | 67 | 170 | -992.43239 | 422.51346 | 99.27% |
| news | $10 | 7 | 1 | 6 | -1.65024 | 0.59022 | 17.54% |
| news | $100 | 10 | 2 | 8 | -19.46324 | 8.63002 | 21.14% |
| news | $1000 | 10 | 2 | 8 | -201.69153 | 90.61727 | 21.91% |
| news_filtered | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news_filtered | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 30 | 7 | 23 | -2.83979 | 2.56180 | 30.98% |
| random | $100 | 180 | 43 | 137 | -92.55652 | 65.62521 | 92.85% |
| random | $1000 | 258 | 47 | 211 | -992.23102 | 631.48083 | 99.25% |
