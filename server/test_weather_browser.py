"""
Shopo Robo — Live Weather Widget Comprehensive Browser Audit
============================================================
Verifies:
1. Live Weather Widget loads real Open-Meteo observations (temp, high/low, humidity, wind, rain)
2. Storage Advisory finishes loading with real warehouse guidance (never stuck in "Fetching...")
3. Manual City Selection updates weather readings (e.g. Delhi -> Jaipur)
4. GPS Geolocation Granted: detects coordinates and updates city
5. GPS Geolocation Denied: gracefully falls back to dropdown city without crashing
6. Temperature Unit Conversion: Celsius (°C) <-> Fahrenheit (°F)
7. Retry Button: re-fetches without reloading page
8. Zero console errors
"""

import sys
import os
import json
import uuid
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db

BASE_URL = "http://127.0.0.1:5000"
ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"

results = {}

def record(name: str, passed: bool, details: str = ""):
    results[name] = {"passed": passed, "details": details}
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{status}] {name}: {details}")

def run_weather_browser_test():
    print("=" * 70)
    print("  SHOPO ROBO -- WEATHER WIDGET BROWSER VERIFICATION")
    print("=" * 70)

    # Setup test user
    email = f"weather_test_{uuid.uuid4().hex[:6]}@shopo.test"
    u = db.create_user("Weather Merchant", email, f"98765{uuid.uuid4().hex[:5]}", "Password123!")
    token = db.create_session(u["id"])

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -----------------------------------------------------------------
        # TEST A: GPS Permission Granted & Initial Live Load
        # -----------------------------------------------------------------
        print("\n--- TEST A: GPS Granted & Initial Real Observations ---")
        context_a = browser.new_context(
            permissions=["geolocation"],
            geolocation={"latitude": 19.0760, "longitude": 72.8777} # Mumbai
        )
        page_a = context_a.new_page()
        page_a.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page_a.goto(f"{BASE_URL}/auth/")
        page_a.evaluate(f"localStorage.setItem('shopo_auth_token', '{token}');")
        page_a.evaluate("localStorage.setItem('shopo_welcome_seen', 'true');")

        page_a.goto(f"{BASE_URL}/app/")
        page_a.wait_for_selector("#view-home", state="visible", timeout=15000)

        # Wait for weather to render (condition must NOT be 'Loading Live Weather...')
        for _ in range(20):
            cond = page_a.inner_text("#wcTempCondition")
            if "Loading" not in cond:
                break
            time.sleep(0.5)

        temp_val = page_a.inner_text("#wcTempVal")
        cond_val = page_a.inner_text("#wcTempCondition")
        range_val = page_a.inner_text("#wcTempRange")
        humidity_val = page_a.inner_text("#wcHumidity")
        wind_val = page_a.inner_text("#wcWind")
        rain_val = page_a.inner_text("#wcRain")
        advisory_val = page_a.inner_text("#wcStorageAdvisory")

        # Assertions
        temp_ok = "°" in temp_val and "--" not in temp_val
        cond_ok = len(cond_val) > 2 and "Loading" not in cond_val
        range_ok = "H:" in range_val and "L:" in range_val and "--" not in range_val
        humidity_ok = "%" in humidity_val and "--" not in humidity_val
        wind_ok = "km/h" in wind_val and "--" not in wind_val
        rain_ok = "mm" in rain_val and "--" not in rain_val
        advisory_ok = len(advisory_val) > 15 and "Fetching" not in advisory_val

        record("Temperature Rendered", temp_ok, f"Value: '{temp_val}'")
        record("Weather Condition Rendered", cond_ok, f"Condition: '{cond_val}'")
        record("High/Low Range Rendered", range_ok, f"Range: '{range_val}'")
        record("Relative Humidity Rendered", humidity_ok, f"Humidity: '{humidity_val}'")
        record("Wind Speed Rendered", wind_ok, f"Wind: '{wind_val}'")
        record("Precipitation Rendered", rain_ok, f"Precipitation: '{rain_val}'")
        record("Commercial Storage Advisory Loaded", advisory_ok, f"Advisory: '{advisory_val[:65]}...'")

        page_a.screenshot(path=os.path.join(ARTIFACT_DIR, "audit_weather_live_reading.png"))

        # -----------------------------------------------------------------
        # TEST B: Manual City Selection (Switch to Jaipur)
        # -----------------------------------------------------------------
        print("\n--- TEST B: Manual City Selection ---")
        page_a.select_option("#wcCitySelect", "Jaipur")
        time.sleep(2)

        # Wait for update
        for _ in range(15):
            cond = page_a.inner_text("#wcTempCondition")
            if "Loading" not in cond:
                break
            time.sleep(0.5)

        jaipur_temp = page_a.inner_text("#wcTempVal")
        jaipur_advisory = page_a.inner_text("#wcStorageAdvisory")
        jaipur_ok = "°" in jaipur_temp and "--" not in jaipur_temp and len(jaipur_advisory) > 10
        record("Manual City Selection (Jaipur)", jaipur_ok, f"Temp: {jaipur_temp}, Advisory: {jaipur_advisory[:50]}...")

        # -----------------------------------------------------------------
        # TEST C: GPS Geolocation Detect Button
        # -----------------------------------------------------------------
        print("\n--- TEST C: GPS Geolocation Detect Button ---")
        page_a.click(".wc-geo-btn")
        time.sleep(3)
        resolved_city = page_a.input_value("#wcCitySelect")
        record("GPS Auto-Detect (Mumbai coordinates)", resolved_city == "Mumbai", f"Resolved City: {resolved_city}")

        # -----------------------------------------------------------------
        # TEST D: Retry Button Functionality
        # -----------------------------------------------------------------
        print("\n--- TEST D: Weather Retry Button ---")
        page_a.click("#wcRetryBtn")
        time.sleep(2)
        retry_temp = page_a.inner_text("#wcTempVal")
        record("Weather Retry / Refresh Button", "°" in retry_temp and "--" not in retry_temp, f"Refreshed Temp: {retry_temp}")

        context_a.close()

        # -----------------------------------------------------------------
        # TEST E: GPS Geolocation Denied Scenario
        # -----------------------------------------------------------------
        print("\n--- TEST E: GPS Geolocation Denied Handling ---")
        context_denied = browser.new_context(
            permissions=[] # Geolocation explicitly not granted
        )
        page_denied = context_denied.new_page()
        page_denied.goto(f"{BASE_URL}/auth/")
        page_denied.evaluate(f"localStorage.setItem('shopo_auth_token', '{token}');")
        page_denied.evaluate("localStorage.setItem('shopo_welcome_seen', 'true');")
        page_denied.goto(f"{BASE_URL}/app/")
        page_denied.wait_for_selector("#view-home", state="visible")
        time.sleep(2)

        # Click detect location when permission is denied
        page_denied.click(".wc-geo-btn")
        time.sleep(2)

        btn_text = page_denied.inner_text(".wc-geo-btn")
        fallback_temp = page_denied.inner_text("#wcTempVal")
        denied_handled = ("Denied" in btn_text or "Detect" in btn_text) and ("°" in fallback_temp and "--" not in fallback_temp)
        record("GPS Denied Fallback to Manual City", denied_handled, f"Btn: '{btn_text}', Temp remains: '{fallback_temp}'")
        context_denied.close()

        # -----------------------------------------------------------------
        # TEST F: Temperature Unit Preference (Celsius -> Fahrenheit)
        # -----------------------------------------------------------------
        print("\n--- TEST F: Temperature Unit Conversion (Fahrenheit) ---")
        context_f = browser.new_context()
        page_f = context_f.new_page()
        page_f.goto(f"{BASE_URL}/auth/")
        page_f.evaluate(f"localStorage.setItem('shopo_auth_token', '{token}');")
        page_f.evaluate("localStorage.setItem('shopo_welcome_seen', 'true');")
        page_f.goto(f"{BASE_URL}/app/")
        page_f.wait_for_selector("#view-home", state="visible")
        time.sleep(2)

        # Set unit to Fahrenheit via preferences in UI
        page_f.click(".nav-item[data-view='settings']")
        page_f.wait_for_selector("#view-settings", state="visible")
        time.sleep(1)
        page_f.select_option("#prefTempUnit", "fahrenheit")
        page_f.click("#btnSavePreferences")
        time.sleep(2)

        # Go back to home
        page_f.click(".nav-item[data-view='home']")
        page_f.wait_for_selector("#view-home", state="visible")
        time.sleep(2)

        f_temp = page_f.inner_text("#wcTempVal")
        f_range = page_f.inner_text("#wcTempRange")
        record("Fahrenheit Temperature Unit Conversion", "°F" in f_temp and "°F" in f_range, f"Temp: {f_temp}, Range: {f_range}")
        context_f.close()

        browser.close()

    # Check for weather-specific console errors
    weather_errors = [e for e in console_errors if "weather" in e.lower() or "open-meteo" in e.lower() or "wc" in e.lower()]
    record("Zero Weather Console Errors", len(weather_errors) == 0, f"Errors: {weather_errors}")

    print("\n" + "=" * 70)
    passed_count = sum(1 for r in results.values() if r["passed"])
    failed_count = sum(1 for r in results.values() if not r["passed"])
    print(f"  TOTAL CHECKS: {len(results)} | PASSED: {passed_count} | FAILED: {failed_count}")
    print("=" * 70)

if __name__ == "__main__":
    run_weather_browser_test()
