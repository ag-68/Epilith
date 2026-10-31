from data.xbrl import pick_concept


def test_prefers_concept_with_newer_end_date():
    companyfacts = {
        "facts": {
            "us-gaap": {
                "OldTag": {
                    "units": {
                        "USD": [
                            {
                                "start": "2019-01-28",
                                "end": "2019-04-28",
                                "val": 1,
                                "form": "10-Q",
                                "filed": "2019-05-16",
                                "accn": "old",
                            }
                        ]
                    }
                },
                "NewTag": {
                    "units": {
                        "USD": [
                            {
                                "start": "2026-01-26",
                                "end": "2026-04-26",
                                "val": 2,
                                "form": "10-Q",
                                "filed": "2026-05-20",
                                "accn": "new",
                            }
                        ]
                    }
                },
            }
        }
    }
    picked = pick_concept(
        companyfacts,
        [
            {"taxonomy": "us-gaap", "concept": "OldTag"},
            {"taxonomy": "us-gaap", "concept": "NewTag"},
        ],
        ["10-Q"],
        "money",
        "USD",
    )
    assert picked is not None
    taxonomy, concept, obs = picked
    assert concept == "NewTag"
    assert obs[0].value == 2


def test_money_facts_keep_reporting_currency_only():
    companyfacts = {
        "facts": {
            "ifrs-full": {
                "Revenue": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "val": 1,
                                "form": "20-F",
                                "filed": "2025-04-01",
                                "accn": "usd",
                            }
                        ],
                        "TWD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "val": 32,
                                "form": "20-F",
                                "filed": "2025-04-01",
                                "accn": "twd",
                            }
                        ],
                    }
                }
            }
        }
    }
    picked = pick_concept(
        companyfacts,
        [{"taxonomy": "ifrs-full", "concept": "Revenue"}],
        ["20-F"],
        "money",
        "TWD",
    )
    assert picked is not None
    _, _, obs = picked
    assert all(item.unit == "TWD" for item in obs)
    assert obs[0].value == 32
