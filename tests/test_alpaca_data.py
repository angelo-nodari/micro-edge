import unittest

import pandas as pd
import requests

from alpaca_data import AlpacaDataError, fetch_historical_bars, normalize_alpaca_bars


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def bar(timestamp, price=100.0, volume=1_000):
    return {
        "t": timestamp,
        "o": price,
        "h": price + 0.2,
        "l": price - 0.2,
        "c": price + 0.1,
        "v": volume,
    }


class AlpacaClientTests(unittest.TestCase):
    def test_downloads_all_pages_and_sends_authentication_headers(self):
        fake = FakeSession(
            [
                FakeResponse(
                    {
                        "bars": [bar("2026-01-05T14:35:00Z")],
                        "next_page_token": "next-page",
                    }
                ),
                FakeResponse(
                    {"bars": [bar("2026-01-05T14:36:00Z")], "next_page_token": None}
                ),
            ]
        )

        data = fetch_historical_bars(
            api_key="test-key",
            secret_key="test-secret",
            symbol="nvda",
            start="2026-01-05",
            end="2026-01-05",
            session=fake,
        )

        self.assertEqual(len(data), 2)
        self.assertEqual(len(fake.calls), 2)
        first_url, first_request = fake.calls[0]
        _, second_request = fake.calls[1]
        self.assertTrue(first_url.endswith("/NVDA/bars"))
        self.assertEqual(first_request["headers"]["APCA-API-KEY-ID"], "test-key")
        self.assertEqual(first_request["headers"]["APCA-API-SECRET-KEY"], "test-secret")
        self.assertNotIn("page_token", first_request["params"])
        self.assertEqual(second_request["params"]["page_token"], "next-page")
        self.assertEqual(first_request["params"]["timeframe"], "1Min")
        self.assertEqual(first_request["params"]["feed"], "iex")

    def test_normalization_filters_outside_the_configured_session(self):
        raw = [
            bar("2026-01-05T14:29:00Z"),
            bar("2026-01-05T14:30:00Z"),
            bar("2026-01-05T14:34:00Z"),
            bar("2026-01-05T14:35:00Z"),
            bar("2026-01-05T20:55:00Z"),
            bar("2026-01-05T20:56:00Z"),
        ]

        data = normalize_alpaca_bars(raw)

        self.assertEqual(len(data), 4)
        self.assertEqual(data.iloc[0]["timestamp"].strftime("%H:%M"), "09:30")
        self.assertEqual(data.iloc[-1]["timestamp"].strftime("%H:%M"), "15:55")
        self.assertEqual(str(data["timestamp"].dt.tz), "America/New_York")

    def test_duplicate_timestamps_keep_the_last_bar(self):
        first = bar("2026-01-05T14:35:00Z", price=100.0)
        second = bar("2026-01-05T14:35:00Z", price=101.0)

        data = normalize_alpaca_bars([first, second])

        self.assertEqual(len(data), 1)
        self.assertEqual(data.iloc[0]["open"], 101.0)

    def test_http_error_is_reported_without_credentials(self):
        fake = FakeSession([FakeResponse({"message": "subscription denied"}, 403)])

        with self.assertRaisesRegex(AlpacaDataError, "subscription denied") as raised:
            fetch_historical_bars(
                api_key="private-key",
                secret_key="private-secret",
                symbol="NVDA",
                start="2026-01-05",
                end="2026-01-06",
                session=fake,
            )

        self.assertNotIn("private-key", str(raised.exception))
        self.assertNotIn("private-secret", str(raised.exception))

    def test_network_error_is_wrapped(self):
        fake = FakeSession([requests.ConnectionError("offline")])

        with self.assertRaisesRegex(AlpacaDataError, "Unable to reach"):
            fetch_historical_bars(
                api_key="key",
                secret_key="secret",
                symbol="NVDA",
                start="2026-01-05",
                end="2026-01-06",
                session=fake,
            )

    def test_empty_response_returns_expected_schema(self):
        data = normalize_alpaca_bars([])

        self.assertTrue(data.empty)
        self.assertEqual(
            list(data.columns),
            ["timestamp", "session", "open", "high", "low", "close", "volume"],
        )

    def test_invalid_ohlc_is_rejected(self):
        invalid = bar("2026-01-05T14:35:00Z")
        invalid["h"] = 90.0

        with self.assertRaisesRegex(AlpacaDataError, "consistency"):
            normalize_alpaca_bars([invalid])


if __name__ == "__main__":
    unittest.main()
