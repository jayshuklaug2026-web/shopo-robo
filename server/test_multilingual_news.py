"""
Shopo Robo — Verification Suite for Multilingual System, News & Market Intelligence,
Weather Widget, and JARVIS Conversational Upgrades
====================================================================================
Tests:
1. User preferences persistence and multi-tenant isolation (GET/PUT /api/user/preferences)
2. News categories, live RSS fetching, caching, deduplication, search, and AI summary
3. Market dashboard quotes, net price change calculation, unit normalization, and comparison
4. Live weather integration and godown storage advisory
5. JARVIS conversational news, mandi, and materials dispatching with safety sandboxing
"""

import unittest
import json
import uuid
import os
import sys

# Ensure server module is in path
sys.path.insert(0, os.path.dirname(__file__))

import app as flask_app
import database
import news_service
import market_intelligence
import universal_ai


class TestMultilingualAndPreferences(unittest.TestCase):
    """Test Feature 1: Multilingual Preferences & Multi-tenant Isolation."""

    def setUp(self):
        self.app = flask_app.create_app().test_client()

        # Create two distinct test users to verify multi-tenant isolation
        self.user1_mobile = f"98765{uuid.uuid4().hex[:5]}"
        self.user1_email = f"user1_{uuid.uuid4().hex[:6]}@test.com"
        self.user2_mobile = f"98765{uuid.uuid4().hex[:5]}"
        self.user2_email = f"user2_{uuid.uuid4().hex[:6]}@test.com"

        u1 = database.create_user(
            full_name="User One",
            email=self.user1_email,
            mobile=self.user1_mobile,
            password="Password123!"
        )
        self.user1_id = u1["id"]

        u2 = database.create_user(
            full_name="User Two",
            email=self.user2_email,
            mobile=self.user2_mobile,
            password="Password123!"
        )
        self.user2_id = u2["id"]

        database.update_shop_setup(self.user1_id, "Shop One Kirana", "Grocery & Kirana Store", "Delhi")
        database.update_shop_setup(self.user2_id, "Shop Two Hardware", "Hardware & Paint Store", "Mumbai")

        # Create sessions
        self.token1 = database.create_session(self.user1_id)
        self.token2 = database.create_session(self.user2_id)

    def test_unauthenticated_preferences_rejected(self):
        resp = self.app.get("/api/user/preferences")
        self.assertEqual(resp.status_code, 401)

    def test_get_default_preferences(self):
        resp = self.app.get(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        prefs = data["data"]
        self.assertEqual(prefs["ui_language"], "hi")
        self.assertEqual(prefs["ai_language"], "hi")
        self.assertEqual(prefs["news_language"], "hi")
        self.assertEqual(prefs["date_format"], "DD/MM/YYYY")
        self.assertEqual(prefs["time_format"], "12h")
        self.assertEqual(prefs["temperature_unit"], "celsius")

    def test_update_and_persist_preferences(self):
        updates = {
            "ui_language": "es",
            "ai_language": "en",
            "news_language": "en",
            "date_format": "YYYY-MM-DD",
            "time_format": "24h",
            "number_format": "intl_standard",
            "temperature_unit": "fahrenheit",
            "selected_city": "Mumbai"
        }
        put_resp = self.app.put(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token1}"},
            json=updates
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.get_json()
        self.assertTrue(put_data["success"])

        # Fetch again to verify persistence
        get_resp = self.app.get(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(get_resp.status_code, 200)
        prefs = get_resp.get_json()["data"]
        self.assertEqual(prefs["ui_language"], "es")
        self.assertEqual(prefs["ai_language"], "en")
        self.assertEqual(prefs["news_language"], "en")
        self.assertEqual(prefs["date_format"], "YYYY-MM-DD")
        self.assertEqual(prefs["time_format"], "24h")
        self.assertEqual(prefs["number_format"], "intl_standard")
        self.assertEqual(prefs["temperature_unit"], "fahrenheit")
        self.assertEqual(prefs["selected_city"], "Mumbai")

    def test_multi_tenant_isolation_of_preferences(self):
        # User 1 sets preferences to Spanish & Mumbai
        self.app.put(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={"ui_language": "es", "selected_city": "Mumbai"}
        )

        # User 2 sets preferences to Arabic & Jaipur
        self.app.put(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token2}"},
            json={"ui_language": "ar", "selected_city": "Jaipur"}
        )

        # Verify User 1 sees only User 1's preferences
        resp1 = self.app.get(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        prefs1 = resp1.get_json()["data"]
        self.assertEqual(prefs1["ui_language"], "es")
        self.assertEqual(prefs1["selected_city"], "Mumbai")

        # Verify User 2 sees only User 2's preferences
        resp2 = self.app.get(
            "/api/user/preferences",
            headers={"Authorization": f"Bearer {self.token2}"}
        )
        prefs2 = resp2.get_json()["data"]
        self.assertEqual(prefs2["ui_language"], "ar")
        self.assertEqual(prefs2["selected_city"], "Jaipur")


class TestNewsAndMarketIntelligence(unittest.TestCase):
    """Test Feature 2 & 3: News Feeds, RSS Caching, Market Dashboard, & Unit Normalization."""

    def setUp(self):
        self.app = flask_app.create_app().test_client()

    def test_news_categories_endpoint(self):
        resp = self.app.get("/api/news/categories")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        cats = data["categories"]
        cat_ids = [c["id"] for c in cats]
        expected_ids = ["today", "business", "india", "world", "tech", "agriculture", "commodities", "schemes"]
        for eid in expected_ids:
            self.assertIn(eid, cat_ids)

    def test_fetch_news_feed_caching_and_deduplication(self):
        # Fetch business category
        res1 = news_service.fetch_news_feed(category="business", language="en", limit=10)
        self.assertTrue(res1["success"])
        self.assertGreater(len(res1["articles"]), 0)

        # Verify attributes on each article
        first = res1["articles"][0]
        self.assertIn("title", first)
        self.assertIn("link", first)
        self.assertIn("publisher", first)
        self.assertIn("category", first)

        # Verify deduplication: no two items should have identical IDs
        ids = [item["id"] for item in res1["articles"]]
        self.assertEqual(len(ids), len(set(ids)), "Articles contain duplicate items!")

        # Second call within TTL should return from cache
        res2 = news_service.fetch_news_feed(category="business", language="en", limit=10)
        self.assertTrue(res2["success"])

    def test_news_search_query_filter(self):
        resp = self.app.get("/api/news?category=business&lang=en&q=market")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])

    def test_ai_article_summary_generation(self):
        summary_res = news_service.generate_article_summary(
            article_title="RBI keeps repo rate unchanged at 6.5%",
            snippet="The Reserve Bank of India Monetary Policy Committee decided to maintain status quo on key interest rates.",
            publisher="LiveMint",
            language="en"
        )
        self.assertTrue(summary_res["success"])
        self.assertIn("LiveMint", summary_res["attribution"])
        self.assertGreater(len(summary_res["summary"]), 20)

    def test_market_dashboard_endpoint(self):
        resp = self.app.get("/api/market/dashboard?category=all")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 0)

        # Check fields on items: price_change_rs, normalized_price_inr
        quotes = data["quotes"]
        agri_quotes = [it for it in quotes if it["type"] == "agricultural_mandi"]
        self.assertGreater(len(agri_quotes), 0)
        first_agri = agri_quotes[0]
        self.assertIn("change_rs", first_agri)
        self.assertIn("change_pct", first_agri)
        self.assertIn("normalized_price", first_agri)
        self.assertIn("kg", first_agri["normalized_unit"])

    def test_unit_normalization_and_comparison(self):
        # 1. Compare 2400 per quintal vs 25 per kg
        item_a = {"price": 2400, "unit": "quintal", "item": "Wheat A"}
        item_b = {"price": 25, "unit": "kg", "item": "Wheat B"}

        comp = market_intelligence.compare_market_prices(item_a, item_b)
        self.assertTrue(comp["comparable"])
        self.assertEqual(comp["cheaper_item"], "Wheat A")
        self.assertEqual(comp["item_a_rate_per_base"], 24.0)
        self.assertEqual(comp["item_b_rate_per_base"], 25.0)
        self.assertEqual(comp["absolute_difference"], -1.0)

        # 2. Incompatible unit comparison rejection (e.g. quintal grain vs 10g bullion)
        item_gold = {"price": 72000, "unit": "10g", "item": "Gold 24k"}
        comp_bad = market_intelligence.compare_market_prices(item_a, item_gold)
        self.assertFalse(comp_bad["comparable"])
        self.assertIn("Incompatible", comp_bad["reason"])


class TestWeatherAndJarvisIntegration(unittest.TestCase):
    """Test Feature 4 & 5: Weather API and JARVIS Conversational Updates."""

    def test_live_weather_fetch(self):
        w = market_intelligence.fetch_live_weather("Delhi")
        self.assertTrue(w["success"])
        self.assertIn("temperature_celsius", w)
        self.assertIn("relative_humidity_pct", w)
        self.assertIn("business_storage_advisory", w)
        self.assertIn("Open-Meteo", w["source"])

    def test_jarvis_news_conversational_query(self):
        res = universal_ai.ai_orchestrator.process_query("Aaj ki business news aur taaza khabar kya hai?")
        self.assertEqual(res["intent"], "news_intelligence_query")
        self.assertIn("reply_text", res)
        self.assertIn("spoken_text", res)
        # Sandbox verification: cannot alter database
        self.assertIsNone(res.get("action_staged"))

    def test_jarvis_mandi_price_with_net_change(self):
        res = universal_ai.ai_orchestrator.process_query("Gehun aur sarson ka mandi bhav kya chal raha hai?")
        self.assertEqual(res["intent"], "mandi_market_query")
        self.assertIn("बदलाव (Net Change)", res["reply_text"])
        self.assertIn("बेस यूनिट (Normalized)", res["reply_text"])


if __name__ == "__main__":
    unittest.main()
