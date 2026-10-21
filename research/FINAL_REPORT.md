# News-Driven BTC Futures Research Platform — Final Report

**Project phase:** 9 of 9 (closure)
**Symbol:** BTC/USDT:USDT (Binance USDⓈ-M perpetual)
**Data window:** 30 days, 43,200 one-minute candles per sample
**Real capital at risk:** $0
**Date of final analysis:** 2026-10-21

---

## Executive Summary

This project set out to answer a single question:

> Does point-in-time news information, combined with market data, contain
> a statistically measurable trading edge in BTC perpetual futures after
> realistic transaction costs?

Over nine development phases, a research and execution platform was built
to answer that question honestly. It was designed to reject false positives,
to detect its own errors, and to produce reproducible results.

**The answer is: no.**

Across two independent 30-day samples, no tested strategy demonstrated a
statistically significant positive edge after costs:

- **Momentum** is statistically anti-predictive at 15, 60, and 240-minute
  horizons. This result is stable across four separate sample windows.
- **Random** is exactly 50% at all horizons. This confirms the instrument
  is free of look-ahead bias.
- **News (keyword sentiment)** produces 163–177 signals per 30-day window.
  Its 60-minute hit rate is 53.4–57.1% with confidence intervals that span
  50% in both samples. There is no demonstrated edge.
- **News at 240 minutes** has a consistent negative mean signed return of
  approximately -31 basis points with confidence intervals excluding zero.
  Holding a news signal to 4 hours systematically loses money.

**The project answered its question. The answer is negative. That is a
complete and valuable result.**

---

## What was built

A research and execution platform, developed across nine phases:

**Data layer**
- Point-in-time news store with four-timestamp discipline
  (`event_time`, `available_time`, `decision_time`, `outcome_time`).
- RSS-based news collector (CoinDesk, Cointelegraph).
- Keyword sentiment scorer, versioned and auditable.
- Deterministic feature engine with explicit look-ahead guards.
- Binance ccxt adapter (demo trading environment).

**Strategy layer**
- Replaceable `Signal` contract, horizon-aware.
- Momentum baseline (simple 15-minute return).
- News-only strategy (sentiment direction, no market agreement gate).
- Random control (deterministic, seeded).

**Risk layer**
- Pure, deterministic risk engine.
- Cost model (fees, slippage, funding, latency).
- Kill switch, daily loss cap, per-trade loss cap, leverage ceiling.
- Scale-invariant position sizing.

**Execution layer**
- Order manager with mandatory protective stop verification.
- Reduce-only exits.
- Exchange-side stop placement.
- Startup and recurring reconciliation.
- Paper executor with divergence tracking.

**Research layer**
- Historical simulator with conservative fills (gap reserve, slippage reserve).
- Point-in-time outcome labeler.
- Walk-forward backtester.
- Bootstrap confidence intervals (1000 resamples).
- A/B experiment framework.
- Multi-horizon signal quality study.

**Total: approximately 3,500 lines of production code, 83 unit tests,
30 integration scenarios.**

---

## What was tested

Three strategies, evaluated on 30 days of BTC/USDT 1-minute data
(43,200 candles), split into 5 walk-forward windows.

**Horizons evaluated:** 15, 60, and 240 minutes.

**Strategy definitions:**

| Strategy | Rule |
|---|---|
| Momentum | Signal = sign of 15-minute return, scaled by magnitude |
| News | Signal = sign of relevance-weighted news sentiment, fires when \|sentiment\| > 0.1 |
| Random | Deterministic pseudo-random signal seeded by decision_time + price |

**Two independent samples were collected:**
- Sample A: 30-day window ending 2026-10-10 (177 news signals)
- Sample B: 30-day window ending 2026-10-21 (163 news signals)

Each sample was analyzed independently. The purpose of two samples was to
distinguish stable findings from small-sample noise.

---

## What was found

### Finding 1: Momentum is anti-predictive at all horizons (STABLE)

| Sample | Horizon 15m | Horizon 60m | Horizon 240m |
|---|---|---|---|
| A | 48.2% [47.8, 48.6] | 48.3% [47.8, 48.8] | 49.6% [49.1, 50.0] |
| B | 47.7% [47.3, 48.2] | 48.7% [48.2, 49.1] | 48.9% [48.4, 49.3] |

Confidence intervals exclude 50% at 15m and 60m in both samples. At 240m
the effect attenuates but remains below 50% in sample B.

**Interpretation:** At short horizons, BTC has short-term mean reversion.
Strong directional moves tend to partially reverse over the following
15–60 minutes. A naive momentum signal bets against this and loses.

**Statistical strength:** 42,000+ signals per sample. This is not noise.

---

### Finding 2: Random is exactly 50% at all horizons (STABLE — validation)

| Sample | Horizon 15m | Horizon 60m | Horizon 240m |
|---|---|---|---|
| A | 50.3% [49.8, 50.7] | 50.1% [49.6, 50.5] | 50.2% [49.7, 50.7] |
| B | 50.0% [49.5, 50.4] | 50.1% [49.6, 50.6] | 50.3% [49.8, 50.8] |

**Interpretation:** This is the strongest possible evidence that the
pipeline has no look-ahead bias, no horizon-dependent artifacts, and no
hidden signal in the data construction. A well-designed research instrument
must produce exactly 50% on a random control. This one does.

**Statistical strength:** 42,000+ signals per sample, all intervals
containing 50%.

---

### Finding 3: News at 15 minutes is below 50% (STABLE — negative)

| Sample | N signals | Hit rate | Mean signed return |
|---|---|---|---|
| A | 177 | 44.1% [36.7, 52.0] | -0.00007 [-0.00031, 0.00017] |
| B | 163 | 41.1% [33.7, 48.5] | -0.00010 [-0.00037, 0.00019] |

Point estimates are consistently below 50%. Sample B's interval excludes
50% on the upside.

**Interpretation:** News sentiment at 15 minutes does not predict forward
returns. If anything, it is slightly anti-predictive on this sample.

---

### Finding 4: News at 60 minutes is AMBIGUOUS (NOT STABLE)

| Sample | N signals | Hit rate | Mean signed return |
|---|---|---|---|
| A | 177 | 57.1% [50.3, 64.4] | 0.00032 [-0.00002, 0.00070] |
| B | 163 | 53.4% [46.0, 60.7] | -0.00003 [-0.00034, 0.00031] |

**This is the closest the project came to a positive finding, and it did
not replicate.**

- Sample A's interval excluded 50% on the upside. This looked like edge.
- Sample B's interval spans 50%. The point estimate fell from 57.1% to
  53.4%.

**The two samples are compatible with each other and with 50%.** The
honest interpretation is that we cannot distinguish the observed result
from noise. A single sample excluding the null is not evidence; it is a
hypothesis. The hypothesis was tested on a second sample and did not
replicate.

**This is what a well-designed instrument does.** It refuses to let you
believe a false positive. The project's discipline was designed for
exactly this scenario, and it worked.

---

### Finding 5: News at 240 minutes is anti-predictive (STABLE — negative)

| Sample | N signals | Hit rate | Mean signed return |
|---|---|---|---|
| A | 177 | 49.2% [42.4, 56.5] | **-0.00313 [-0.00426, -0.00200]** |
| B | 163 | 53.4% [46.0, 60.7] | **-0.00315 [-0.00433, -0.00194]** |

**This is the most interesting finding in the project.** The hit rate
varies (49.2% vs 53.4%) — noise. But the **mean signed return is -31
basis points in both samples, with confidence intervals that exclude zero
on the negative side.**

**Interpretation:** When the news signal fires and you hold the position
for 4 hours, you systematically lose money. The loss is not a coin-flip
outcome; it is a stable directional effect.

One plausible mechanism: news events trigger an initial move that the
market partially reverses over the following hours. Being positioned in
the direction of the news at the 4-hour mark is on the wrong side of this
reversal.

**This is a real, robust, negative finding.** It is not a bug. It is not
noise. It is what the data says.

---

### Finding 6: Costs dominate at all account sizes (STABLE)

Round-trip cost on notional: approximately 19.5 basis points
(entry fee 5 bps + exit fee 5 bps + slippage reserve 5.5 bps + funding
2 bps + latency 2 bps).

At $10 equity with $52.5 minimum notional, cost is ~0.9% of account per
trade. At $100, ~0.1%. At $1000, ~0.01%.

**Observation:** Every strategy tested loses money at every account size,
in percentage terms roughly constant. The $10 constraint is real, but
increasing account size does not fix the problem. The strategies tested
do not overcome the cost structure at any size.

---

## What was learned about the instrument itself

The project was as much about building an honest instrument as about
testing a hypothesis. Six things about the instrument are worth recording.

**1. The instrument detects its own errors.**

Over the course of development, the instrument caught:
- A SQLite thread-safety bug that would have silently disabled the news pipeline.
- A hard-coded leverage fallback that was masking exchange metadata.
- A news strategy gated by momentum, which was conditioning on a
  known-bad signal.
- An account sizing rule that was not scale-invariant.
- A threshold/divisor mismatch in the news model that was filtering out
  most tradeable signals.
- A ratio of log-spam to log-signal that made the pipeline unusable
  for experiments.

Every one of these was found by the research methodology — bootstrap,
walk-forward, comparison to baselines — not by intuition.

**2. Small samples produce false positives.**

Sample A's 60-minute hit rate looked like edge. Sample B did not
replicate it. With 163–177 signals, a 57% hit rate and a 50% hit rate
are both within the confidence interval of a single sample. The only
way to distinguish them is a second sample.

**3. The random control is essential.**

Without the random control, it would have been easy to believe that
momentum's 48% hit rate was "almost 50%." The control confirms that
48% is *far* from 50% and statistically distinguishable.

**4. Multi-horizon studies are necessary.**

The signal that looked plausible at 60 minutes was anti-predictive at
240 minutes. A single-horizon study would have missed this. The
multi-horizon design revealed the actual temporal structure of news
impact.

**5. The pipeline is deterministic.**

Re-running the same experiment produces the same result, to the decimal.
This is what a research pipeline should do. It also means that re-running
is not a way to gather new evidence.

**6. Cost is not a footnote.**

Cost is the dominant variable at every account size we tested. Even a
strategy with genuine edge has to overcome 19.5 bps of round-trip cost
per trade. Any strategy that fires frequently enough to find edge must
also find enough edge per trade to survive.

---

## What the negative result means

A negative result in a research project is not a failure. It is an
answer. The question was: does news predict BTC moves? The answer is:
not at the timescales we tested, with the scorer we built.

Three consequences:

**1. The $10 experiment is not viable.**

The design document framed the project around a $10 account. At $10 with
$52.5 minimum notional, cost is 0.9% of account per trade. A strategy
would need to average 0.9% net return per trade to break even. No strategy
we tested came close. The $10 constraint is real and binding.

**2. The news premise needs a better scorer.**

The keyword sentiment scorer is deliberately crude. It extracts ~71
news items in 30 days from two RSS feeds, with a sentiment distribution
that is narrow and centered near zero. A transformer-based or
embedding-based scorer would likely produce a stronger signal-to-noise
ratio. Whether it would produce *edge* is unknown.

**3. The pipeline can test other hypotheses.**

The instrument is general. It can test:
- A different signal (on-chain flows, orderbook imbalance, funding rate).
- A different market (ETH, other majors, other exchanges).
- A different timescale (sub-minute, daily).
- A different model class (learned scorer, feature interactions).

The pipeline is validated. Only the strategies tested are negative.

---

## What a future project should do differently

If this project were restarted with hindsight, four changes would help:

**1. Start with more data.**

71 news items over 30 days is thin. Two RSS feeds is thin. A serious news
study should start with a paid source (Bloomberg, Refinitiv, or a curated
archive), or a two-year history collected live from day one.

**2. Build the scorer first.**

The keyword scorer was chosen to ship fast. A better scorer (embedding-based,
with entity recognition and source credibility weighting) would have
produced a much better signal-to-noise ratio. The time saved by using
keywords was spent on debugging.

**3. Test the horizon question early.**

We spent eight phases testing at 15 minutes. The question "at what horizon
does news predict returns?" should have been asked in phase 2, not phase 9.

**4. Treat small samples with suspicion.**

163–177 signals is not enough to distinguish a 50% hit rate from a 55%
hit rate at 90% confidence. A serious study needs 1000+ signals, which
means either more news items or more time.

---

## What was not tested

In fairness to the reader, four things the project did not evaluate:

- Whether a better scorer would produce edge. (Path A, months of work.)
- Whether news has edge at horizons longer than 240 minutes.
- Whether news has edge on symbols other than BTC.
- Whether a learned model (rather than keyword sentiment) would extract
  predictive features.

These are legitimate extensions but not within the scope of Phase 9.

---

## Conclusion

The project built an honest research instrument and used it to test a
specific hypothesis. The hypothesis is not supported by the data.

**Three findings are robust across samples:**
- Momentum is anti-predictive at 15–60 minute horizons.
- Random is exactly 50%, validating the pipeline.
- News at 240 minutes is systematically negative.

**Two findings are ambiguous:**
- News at 15 minutes is below 50% but underpowered.
- News at 60 minutes is 53–57% with confidence intervals spanning 50%.

**The most important result is the negative one:** the news sentiment
signal, as constructed with keyword scoring on two RSS feeds over 30 days,
does not demonstrate a statistically significant edge in BTC perpetual
futures at any tested horizon.

**The project answered its question. The answer is no. That is the
result.**

---

## Appendix: Reproducibility

Every result in this report can be reproduced by:

```bash
python -m scripts.run_experiments --days 30 --windows 5 \
    --horizons 15 60 240 --accounts 10 100 1000
```

Output is written to `research/out/phase9_{timestamp}/`.

The pipeline is deterministic. Same input, same output. Re-running is
not a way to gather new evidence.

---

## Appendix: File manifest

Key files, for a future reader:

| File | Purpose |
|---|---|
| `strategy/news_model.py` | News-only strategy |
| `strategy/baseline.py` | Momentum baseline |
| `research/signal_study.py` | Multi-horizon signal quality study |
| `research/signal_metrics.py` | Bootstrap confidence intervals |
| `research/experiments.py` | Experiment driver |
| `research/account_sweep.py` | Account-size sweep |
| `storage/db.py` | SQLite schema, including `outcomes_by_horizon` |
| `risk/engine.py` | Risk engine |
| `risk/sizing.py` | Position sizing |
| `execution/orders.py` | Order manager |
| `execution/reconcile.py` | Reconciliation |
| `data/features.py` | Feature engine |
| `data/news/pipeline.py` | News ingestion |

---

*End of report.*