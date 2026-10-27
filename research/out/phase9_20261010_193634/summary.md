# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `43200`
Windows: `5`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.482 [0.478, 0.487] | -0.00001 [-0.00002, 0.00001] | -0.006 |
| news | 177 | 0.441 [0.367, 0.520] | -0.00007 [-0.00031, 0.00017] | -0.057 |
| random | 41700 | 0.503 [0.498, 0.507] | 0.00002 [-0.00000, 0.00003] | 0.013 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.483 [0.478, 0.488] | -0.00006 [-0.00009, -0.00002] | -0.025 |
| news | 177 | 0.571 [0.503, 0.644] | 0.00032 [-0.00002, 0.00070] | 0.163 |
| random | 41700 | 0.501 [0.496, 0.505] | 0.00002 [-0.00002, 0.00005] | 0.006 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 41665 | 0.496 [0.491, 0.500] | -0.00005 [-0.00012, 0.00002] | -0.010 |
| news | 177 | 0.492 [0.424, 0.565] | -0.00313 [-0.00426, -0.00200] | -0.484 |
| random | 41700 | 0.502 [0.497, 0.507] | 0.00005 [-0.00002, 0.00012] | 0.010 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 2 | 0 | 2 | -3.64187 | 0.15543 | 36.42% |
| momentum | $100 | 12 | 2 | 10 | -84.44267 | 5.12884 | 84.44% |
| momentum | $1000 | 12 | 2 | 10 | -863.49159 | 54.44768 | 86.35% |
| news | $10 | 1 | 0 | 1 | -1.88015 | 0.08479 | 18.80% |
| news | $100 | 1 | 0 | 1 | -20.68163 | 0.93269 | 20.68% |
| news | $1000 | 1 | 0 | 1 | -223.73758 | 10.09004 | 22.37% |
| random | $10 | 2 | 0 | 2 | -3.43793 | 0.15587 | 34.38% |
| random | $100 | 16 | 4 | 12 | -82.84069 | 5.86643 | 86.02% |
| random | $1000 | 16 | 4 | 12 | -829.03640 | 62.77711 | 87.36% |
