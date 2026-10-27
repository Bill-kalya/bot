# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.468 [0.440, 0.496] | 0.00001 [-0.00011, 0.00014] | 0.009 |
| news | 0 | — | — | — |
| random | 1140 | 0.525 [0.495, 0.554] | 0.00002 [-0.00010, 0.00015] | 0.017 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.513 [0.486, 0.541] | -0.00001 [-0.00025, 0.00024] | -0.006 |
| news | 0 | — | — | — |
| random | 1140 | 0.507 [0.476, 0.534] | 0.00005 [-0.00019, 0.00028] | 0.018 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.491 [0.464, 0.519] | -0.00018 [-0.00047, 0.00012] | -0.045 |
| news | 0 | — | — | — |
| random | 1140 | 0.518 [0.488, 0.546] | 0.00017 [-0.00011, 0.00046] | 0.042 |

## Experiment 2 — Account sweep (single horizon)

| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| momentum | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| momentum | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $10 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $100 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| news | $1000 | 0 | 0 | 0 | 0.00000 | 0.00000 | 0.00% |
| random | $10 | 1 | 0 | 1 | -1.86412 | 0.08225 | 18.64% |
| random | $100 | 1 | 0 | 1 | -22.36945 | 0.98701 | 22.37% |
| random | $1000 | 1 | 0 | 1 | -227.42274 | 10.03465 | 22.74% |
