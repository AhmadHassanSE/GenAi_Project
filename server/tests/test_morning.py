"""The morning run prints the paper before seven, emails readers who asked once a day, and never twice."""
from datetime import datetime, timezone

import pytest

from server.subah import accounts, mailer, scheduler
from server.subah.edition import build_edition


def at(hh, mm, day=23):  # Lahore time is UTC+5
    return datetime(2026, 11, day, hh - 5, mm, tzinfo=timezone.utc)


@pytest.fixture()
def edition(collection):
    return build_edition({}, collection=collection, cache_path=None, pool=15)


def make(edition, store, mail_ok=True):
    sent, saved, builds = [], [], []

    def build():
        builds.append(1)
        return edition

    m = scheduler.Morning(build=build, save=saved.append, store=store, render=mailer.render_daily,
                          send=lambda to, subject, html, text, name: sent.append((to, subject, html)),
                          mail_ready=lambda: (mail_ok, "ok" if mail_ok else "GMAIL_USER is not set"))
    return m, sent, saved, builds


def reader(store, email, daily=True, **profile):
    u = store.insert_user({"name": "Test Reader", "email": email, "daily_email": daily, "profile": profile})
    return u["_id"]


def test_prints_at_half_past_six_and_sends_at_seven(edition):
    store = accounts.MemoryStore()
    reader(store, "a@example.com", city="lahore", topics=["prices"], lang="ro", large=True)
    reader(store, "b@example.com", daily=False)
    m, sent, saved, builds = make(edition, store)

    assert m.tick(at(6, 0)) == {} and not builds           # too early
    assert "printed" in m.tick(at(6, 31)) and saved        # printed, nothing sent yet
    assert sent == []
    done = m.tick(at(7, 0))
    assert done["sent"] == 1 and [s[0] for s in sent] == ["a@example.com"]
    assert "ki Subah" in sent[0][1]                        # their language: Roman Urdu
    assert m.tick(at(7, 30)) == {} and len(sent) == 1      # never twice the same day
    assert len(builds) == 1


def test_a_restart_does_not_send_twice(edition):
    store = accounts.MemoryStore()
    reader(store, "a@example.com")
    first, sent1, _, _ = make(edition, store)
    first.tick(at(6, 40)); first.tick(at(7, 1))
    second, sent2, _, _ = make(edition, store)             # a new server process the same morning
    second.tick(at(7, 5))
    assert len(sent1) == 1 and sent2 == []
    second.tick(at(6, 45, day=24)); second.tick(at(7, 0, day=24))
    assert len(sent2) == 1                                 # the next day it goes out again


def test_late_start_catches_up_then_gives_up(edition):
    store = accounts.MemoryStore()
    reader(store, "a@example.com")
    m, sent, _, _ = make(edition, store)
    m.tick(at(9, 15))
    assert len(sent) == 1                                  # printed and sent on catching up
    late, sent_late, _, builds = make(edition, accounts.MemoryStore())
    assert late.tick(at(13, 0)) == {} and not builds       # after 11:00 the day is skipped


def test_without_gmail_nothing_is_sent_and_it_says_why(edition):
    store = accounts.MemoryStore()
    reader(store, "a@example.com")
    m, sent, _, _ = make(edition, store, mail_ok=False)
    m.tick(at(6, 35))
    done = m.tick(at(7, 0))
    assert sent == [] and done["not_sent"] == 1 and "GMAIL" in done["reason"]


def test_a_failed_print_waits_before_trying_again(edition):
    calls = []

    def broken():
        calls.append(1)
        raise RuntimeError("feeds down")

    m = scheduler.Morning(build=broken, save=lambda e: None, store=accounts.MemoryStore(), render=mailer.render_daily,
                          send=lambda *a: None, mail_ready=lambda: (True, "ok"))
    with pytest.raises(RuntimeError):
        m.tick(at(6, 30))
    m.tick(at(6, 31))
    assert len(calls) == 1                                 # backs off for ten minutes
    with pytest.raises(RuntimeError):
        m.tick(at(6, 41))
    assert len(calls) == 2


def test_daily_email_switch_needs_an_account():
    from fastapi.testclient import TestClient

    from server import app as app_module

    accounts.set_store(accounts.MemoryStore())
    try:
        c = TestClient(app_module.app, base_url="https://testserver")
        H = {"X-Subah": "1"}
        assert c.post("/api/daily", json={"on": True}, headers=H).status_code == 401
        c.post("/api/auth/signup", json={"name": "Test A", "email": "test.a@example.com", "password": "test-pass-1"}, headers=H)
        assert c.post("/api/daily", json={"on": True}, headers=H).json()["user"]["daily_email"] is True
        assert [u["email"] for u in accounts.get_store().daily_readers()] == ["test.a@example.com"]
        assert c.post("/api/daily", json={"on": True}).status_code == 403  # header check
        assert "morning_run" in c.get("/api/health").json()
    finally:
        accounts.set_store(None)
