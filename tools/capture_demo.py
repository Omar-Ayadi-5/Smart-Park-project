"""Run actual browser flows against an isolated synthetic database.

Install dev tools, install frontend dependencies, then run with --capture for media.
No live backend, existing .env, real account, or external database is used.
"""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import create_app, db
from app.models import AdminUser
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="store_true", help="Write screenshots and a short demo recording")
    args = parser.parse_args()
    output = ROOT / "docs" / "images"
    if args.capture: output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="smartpark-demo-") as temp:
        app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(Path(temp) / "demo.db"),
            "SECRET_KEY": secrets.token_hex(32), "RATELIMIT_ENABLED": False,
            "CORS_ORIGINS": ["http://localhost:5173", "http://localhost:5174"]})
        password = secrets.token_urlsafe(9) + "!A7"
        with app.app_context():
            result = app.test_cli_runner().invoke(args=["db", "upgrade"])
            if result.exit_code: raise RuntimeError(result.output) from result.exception
            result = app.test_cli_runner().invoke(args=["seed-demo"])
            if result.exit_code: raise RuntimeError(result.output)
            db.session.add(AdminUser(username="Demo administrator", email="demo@example.com",
                password_hash=generate_password_hash(password), is_approved=True, role="super_admin"))
            db.session.commit()
        server = make_server("localhost", 5000, app, threaded=True)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        processes = []
        try:
            for name in ("admin", "public"):
                processes.append(subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "localhost"],
                    cwd=ROOT / "frontend" / name / "src", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env=dict(os.environ, VITE_API_BASE_URL="http://localhost:5000/api")))
            for port in (5173, 5174):
                for attempt in range(100):
                    try:
                        with urlopen(f"http://localhost:{port}", timeout=1): break
                    except OSError: time.sleep(0.1)
                else: raise RuntimeError(f"Frontend on port {port} did not start")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                options = {"viewport": {"width": 1440, "height": 1000}}
                if args.capture: options["record_video_dir"] = str(Path(temp) / "recordings")
                context = browser.new_context(**options)
                page = context.new_page()
                failures = []
                page.on("pageerror", lambda error: failures.append(str(error)))
                page.goto("http://localhost:5173")
                page.get_by_placeholder("Admin Email").fill("demo@example.com")
                page.get_by_placeholder("Password", exact=True).fill(password)
                page.get_by_role("button", name="Login", exact=True).click()
                expect(page).to_have_url("http://localhost:5173/admin/dashboard")
                expect(page.locator(".stat-value").first).to_have_text("24")
                page.locator(".global-api-loading-overlay").wait_for(state="hidden")
                page.wait_for_timeout(1500)
                if args.capture: page.screenshot(path=str(output / "admin-dashboard.png"), full_page=True)
                page.get_by_role("link", name="Parking zones").click()
                free = page.locator(".spot-free").first
                expect(free).to_be_visible()
                code = free.inner_text()
                free.click()
                expect(page.locator(".spot-oos").filter(has_text=code).first).to_be_visible()
                if args.capture: page.screenshot(path=str(output / "parking-controls.png"), full_page=True)
                page.get_by_role("link", name="Users & staff").click()
                expect(page.get_by_text("demo@example.com", exact=True)).to_be_visible()
                page.goto("http://localhost:5174")
                expect(page.get_by_role("heading", name="SmartPark Dashboard")).to_be_visible()
                expect(page.locator(".parking-lot .spot")).to_have_count(24)
                if args.capture:
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(output / "public-display.png"), full_page=True)
                    page.wait_for_timeout(1500)
                assert not failures, failures
                video = page.video
                context.close()
                if args.capture and video:
                    video.save_as(str(output / "walkthrough.webm"))
                browser.close()
                print("PASS: login, dashboard, parking mutation, user list, public display; no browser exceptions")
        finally:
            for process in processes:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill()
            server.shutdown(); worker.join(timeout=5)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    main()
