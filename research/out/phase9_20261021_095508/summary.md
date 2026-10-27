# Phase 9 — A/B Experiments

Symbol: `BTC/USDT:USDT`
Candles: `1440`
Windows: `1`
Horizons (min): 15, 60, 240

## Experiment 1 — Signal quality, horizon 15m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.445 [0.415, 0.473] | -0.00006 [-0.00019, 0.00006] | -0.049 |
| news | 0 | — | — | — |
| random | 1140 | 0.519 [0.491, 0.549] | 0.00003 [-0.00009, 0.00016] | 0.022 |

## Experiment 1 — Signal quality, horizon 60m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.471 [0.439, 0.499] | -0.00019 [-0.00047, 0.00007] | -0.068 |
| news | 0 | — | — | — |
| random | 1140 | 0.506 [0.478, 0.534] | -0.00006 [-0.00035, 0.00022] | -0.021 |

## Experiment 1 — Signal quality, horizon 240m

| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |
|---|---:|---:|---:|---:|
| momentum | 1139 | 0.479 [0.450, 0.508] | -0.00020 [-0.00063, 0.00019] | -0.040 |
| news | 0 | — | — | — |
| random | 1140 | 0.513 [0.485, 0.542] | 0.00007 [-0.00030, 0.00043] | 0.014 |

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
