# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.487 [0.458, 0.516] | 0.00001 [-0.00003, 0.00005] | 0.020 |
| news | 0 | — | — | — |
| random | 1140 | 0.515 [0.486, 0.544] | 0.00003 [-0.00000, 0.00007] | 0.066 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.461 [0.431, 0.490] | -0.00020 [-0.00027, -0.00014] | -0.216 |
| news | 0 | — | — | — |
| random | 1140 | 0.502 [0.474, 0.530] | 0.00002 [-0.00005, 0.00008] | 0.018 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1138 | 0.492 [0.462, 0.520] | -0.00016 [-0.00025, -0.00007] | -0.121 |
| news | 0 | — | — | — |
| random | 1140 | 0.512 [0.484, 0.540] | 0.00002 [-0.00007, 0.00010] | 0.011 |

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
