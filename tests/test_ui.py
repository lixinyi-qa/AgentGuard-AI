from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


@pytest.fixture(scope="session", autouse=True)
def live_server(tmp_path_factory):
    database = (tmp_path_factory.mktemp("ui") / "ui.db").as_posix()
    env = {**os.environ, "AGENTGUARD_DATABASE_URL": f"sqlite:///{database}"}
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if httpx.get(f"{BASE_URL}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(.2)
    else:
        process.terminate()
        pytest.fail("Uvicorn did not start for UI tests")
    yield
    process.terminate()
    process.wait(timeout=10)


@pytest.fixture()
def browser():
    with sync_playwright() as playwright:
        executable = str(CHROME) if CHROME.exists() else None
        instance = playwright.chromium.launch(headless=True, executable_path=executable)
        yield instance
        instance.close()


@pytest.fixture()
def page(browser):
    page = browser.new_page()
    page.goto(BASE_URL)
    yield page
    page.close()


@pytest.mark.ui
def test_dashboard_loads_and_has_accessible_landmarks(page: Page):
    expect(page).to_have_title("AgentGuard AI · Quality Console")
    expect(page.get_by_text("虚构沙箱", exact=False)).to_be_visible()
    expect(page.get_by_role("heading", name="智能体调试台")).to_be_visible()
    expect(page.get_by_role("button", name="运行评测")).to_be_visible()


@pytest.mark.ui
def test_normal_request_trace_and_offline_replay(page: Page):
    page.get_by_role("button", name="执行并记录 Trace").click()
    expect(page.locator("#agent-result")).to_contain_text("完成")
    expect(page.locator("#tool-timeline")).to_contain_text("query_account")
    expect(page.locator("#policy-log")).to_contain_text("POL-008")
    page.get_by_role("button", name="离线重放当前 Trace").click()
    expect(page.locator("#global-message")).to_contain_text("未重复执行写操作")


@pytest.mark.ui
def test_unauthorized_request_is_visibly_blocked(page: Page):
    page.get_by_role("button", name="填入越权示例").click()
    page.get_by_role("button", name="执行并记录 Trace").click()
    expect(page.locator("#agent-result")).to_contain_text("安全停止")
    expect(page.locator("#policy-log")).to_contain_text("DENY")
    expect(page.locator("#tool-timeline")).to_contain_text("blocked")


@pytest.mark.ui
def test_fault_injection_recovers_and_is_visible(page: Page):
    page.locator("#fault-type").select_option("timeout")
    page.get_by_role("button", name="启用故障").click()
    expect(page.locator("#fault-list")).to_contain_text("timeout")
    page.get_by_role("button", name="执行并记录 Trace").click()
    expect(page.locator("#tool-timeline")).to_contain_text("attempt 2")
    expect(page.locator("#agent-result")).to_contain_text("完成")


@pytest.mark.ui
def test_full_evaluation_failure_list_compare_and_download(page: Page):
    page.get_by_role("button", name="运行评测").click()
    expect(page.locator("#gate-status")).to_have_text("PASS", timeout=30_000)
    expect(page.locator("#evaluation-progress")).to_contain_text("40/40")
    page.get_by_role("button", name="运行评测").click()
    expect(page.locator("#evaluation-progress")).to_contain_text("40/40", timeout=30_000)
    page.get_by_role("button", name="比较最近两次").click()
    expect(page.locator("#comparison-result")).to_contain_text("新增失败：0")
    with page.expect_download() as download_info:
        page.get_by_role("link", name="导出 JSON").click()
    assert download_info.value.suggested_filename.endswith(".json")
    expect(page.locator("#run-history")).not_to_contain_text("暂无评测运行")


@pytest.mark.ui
def test_keyboard_focus_and_mobile_layout(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(BASE_URL)
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip-link"
    assert page.locator(".workspace").evaluate("el => getComputedStyle(el).gridTemplateColumns").count("px") == 1
    expect(page.get_by_role("button", name="执行并记录 Trace")).to_be_visible()
    page.close()
