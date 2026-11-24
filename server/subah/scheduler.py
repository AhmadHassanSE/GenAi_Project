"""The morning run: print the day's paper before 7 am and email it to readers who asked for it.

At PRINT_AT (default 06:30, Lahore time) the server builds the day's shared paper from live feeds (15 stories,
no reader settings) and saves it as the latest paper. At SEND_AT (default 07:00) it emails every account that
turned on "Email me my paper" its own paper: today's stories re-scored for that reader's saved city and topics
by the published formula, in their language and print size. Nothing new is written for the email.

Each account records the day it was last sent (daily_sent_on), so a restart never sends twice. A server that
starts late catches up until CATCH_UP_UNTIL (default 11:00); after that the day is skipped. Sending stops at
DAILY_MAX emails a day (Gmail allows one account about 500).

Runs inside the web server as a background thread. Turn it off with SUBAH_SCHEDULE=off. It only works while the
server is awake: a free Hugging Face Space sleeps after a long idle, and a sleeping Space prints nothing.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, time, timedelta, timezone

log = logging.getLogger("subah.scheduler")

PKT = timezone(timedelta(hours=5))


def _at(name: str, default: str) -> time:
    h, m = (os.environ.get(name) or default).split(":")
    return time(int(h), int(m))


PRINT_AT = _at("SUBAH_PRINT_AT", "06:30")
SEND_AT = _at("SUBAH_SEND_AT", "07:00")
CATCH_UP_UNTIL = _at("SUBAH_CATCH_UP_UNTIL", "11:00")
DAILY_MAX = int(os.environ.get("SUBAH_DAILY_MAX", "400"))
CHECK_EVERY = 30  # seconds


def in_window(now: datetime, start: time, end: time = CATCH_UP_UNTIL) -> bool:
    t = now.astimezone(PKT).time()
    return start <= t < end


def today(now: datetime) -> str:
    return now.astimezone(PKT).date().isoformat()


class Morning:
    """One server's morning run. build() returns a fresh shared edition; store, render and send are the account
    store, mailer.render_daily and mailer.send (tests pass fakes)."""

    def __init__(self, build, save, store, render, send, mail_ready, lock: threading.Lock | None = None):
        self.build, self.save, self.store = build, save, store
        self.render, self.send, self.mail_ready = render, send, mail_ready
        self.lock = lock or threading.Lock()
        self.printed_on: str | None = None
        self.edition: dict | None = None
        self.last: dict = {}
        self.retry_at: datetime | None = None  # after a failed print, wait before trying again

    def tick(self, now: datetime | None = None) -> dict:
        """Do whatever is due now. Returns what happened, for the log and for tests."""
        now = now or datetime.now(timezone.utc)
        day = today(now)
        done: dict = {}
        if self.printed_on != day and in_window(now, PRINT_AT) and not (self.retry_at and now < self.retry_at):
            try:
                with self.lock:
                    self.edition = self.build()
                self.save(self.edition)
            except Exception as exc:
                self.retry_at = now + timedelta(minutes=10)
                self.last = {"at": now.isoformat(), "print_failed": type(exc).__name__}
                raise
            self.printed_on, self.retry_at = day, None
            done["printed"] = self.edition.get("edition_id")
        if self.printed_on == day and in_window(now, SEND_AT):
            done.update(self.send_all(day))
        if done:
            self.last = {"at": now.isoformat(), **done}
        return done

    def send_all(self, day: str) -> dict:
        ok, why = self.mail_ready()
        readers = [u for u in self.store.daily_readers() if u.get("daily_sent_on") != day]
        if not readers:
            return {}
        if not ok:
            return {"not_sent": len(readers), "reason": why}
        sent = failed = 0
        for user in readers[:DAILY_MAX]:
            try:
                subject, html, text = self.render(self.edition, user)
                self.send(user["email"], subject, html, text, "Subah")
            except Exception as exc:  # one bad address must not stop the others
                failed += 1
                log.warning("daily paper not sent to an account: %s", type(exc).__name__)
                continue
            self.store.update_user(user["_id"], {"daily_sent_on": day})
            sent += 1
        return {"sent": sent, "failed": failed, "over_limit": max(0, len(readers) - DAILY_MAX)}

    def status(self) -> dict:
        return {"print_at": PRINT_AT.strftime("%H:%M"), "send_at": SEND_AT.strftime("%H:%M"),
                "timezone": "Asia/Karachi", "printed_on": self.printed_on, "last": self.last}

    def run_forever(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                done = self.tick()
                if done:
                    log.info("morning run: %s", done)
            except Exception as exc:  # keep the thread alive; try again on the next check
                log.warning("morning run failed: %s", type(exc).__name__)
            stop.wait(CHECK_EVERY)


def enabled() -> bool:
    return os.environ.get("SUBAH_SCHEDULE", "on").lower() not in ("off", "0", "false")
