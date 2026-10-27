from data.news import scorer


def test_bullish_text_scores_positive():
    s = scorer.score("Bitcoin ETF approved by SEC",
                     "Institutional inflow surged as ETF approval was granted.")
    assert s.sentiment > 0


def test_bearish_text_scores_negative():
    s = scorer.score("Exchange hacked, funds stolen",
                     "A major exploit drained funds; withdrawals halted.")
    assert s.sentiment < 0


def test_irrelevant_text_has_low_relevance():
    s = scorer.score("Weather forecast for Tuesday", "Sunny with a chance of rain.")
    assert s.relevance < 0.5


def test_relevant_text_has_higher_relevance():
    s = scorer.score("Bitcoin ETF sees record inflows",
                     "Spot Bitcoin ETF and crypto markets rallied.")
    assert s.relevance >= 0.5


def test_scorer_is_versioned():
    s = scorer.score("Bitcoin", "Bitcoin")
    assert s.scorer_version == scorer.SCORER_VERSION