#!/usr/bin/env python3
# A tiny macOS overlay window that sits top-right, shows an animated voice ring and text.
# Launch this as a separate process; it reads JSON state from a temp file and updates ~30 FPS.
# Dependencies: PyObjC (already included in requirements via pyobjc meta-packages).

import AppKit
import Quartz
import Foundation
import math
import json
import os
import time
import threading

STATE_PATH = os.getenv("JARVIS_OVERLAY_STATE", "/tmp/jarvis_overlay_state.json")
FPS = 30.0


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


class OverlayView(AppKit.NSView):
    def init(self):
        self = AppKit.NSView.init(self)
        if self is None:
            return None
        self.backgroundColor = AppKit.NSColor.clearColor()
        self.state = {
            "status": "idle",  # idle|listening|speaking|thinking
            "text": "",
            "level": 0.0,       # 0..1 voice level
            "visible": False,
        }
        self.displayLevel = 0.0   # smoothed level for animation
        self.phase = 0.0          # time phase for breathing
        self.lastTick = time.time()
        return self

    def updateFromState(self, data: dict):
        # Keep text/status; level is a target we approach smoothly
        if not isinstance(data, dict):
            return
        status = (data.get("status") or self.state.get("status") or "idle").lower()
        text = data.get("text") if isinstance(data.get("text"), str) else self.state.get("text")
        lvl = float(data.get("level") or 0.0)
        vis = bool(data.get("visible")) if "visible" in data else self.state.get("visible", False)
        self.state = {"status": status, "text": text or "", "level": clamp01(lvl), "visible": vis}
        # No immediate display change; drawRect_ uses smoothed displayLevel

    def drawRect_(self, rect):
        bounds = self.bounds()
        w = bounds.size.width
        h = bounds.size.height
        # Clear
        AppKit.NSColor.clearColor().set()
        AppKit.NSBezierPath.fillRect_(bounds)

        # Breathing and smoothing
        now = time.time()
        dt = max(0.0, min(0.1, now - self.lastTick))
        self.lastTick = now
        self.phase = (self.phase + dt) % 1000.0
        target = clamp01(float(self.state.get("level", 0.0)))
        # Approach target smoothly
        self.displayLevel += (target - self.displayLevel) * 0.18

        status = (self.state.get("status") or "idle").lower()
        # Base breathing depending on status
        base = 0.12
        if status == "listening":
            base = 0.18
        elif status == "thinking":
            base = 0.15
        elif status == "speaking":
            base = 0.08
        breath = (0.5 + 0.5 * math.sin(self.phase * 2.0)) * base
        lvl = clamp01(self.displayLevel + breath)

        # Visuals: glowing orb + text
        margin = 12.0
        orb_cx = 28 + margin
        orb_cy = h - 28
        base_r = 14.0
        r = base_r + 10.0 * lvl

        # Determine colors by status
        if status == "speaking":
            core = AppKit.NSColor.systemBlueColor()
            glow = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 0.6, 1.0, 0.7)
        elif status == "listening":
            core = AppKit.NSColor.systemGreenColor()
            glow = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 1.0, 0.5, 0.7)
        elif status == "thinking":
            core = AppKit.NSColor.systemPurpleColor()
            glow = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.7, 0.3, 1.0, 0.7)
        else:
            core = AppKit.NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.8)
            glow = AppKit.NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.35)

        # Orb glow (multiple concentric circles)
        for i in range(4, 0, -1):
            rr = r + i * 6
            alpha = 0.04 * i
            AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
                glow.redComponent(), glow.greenComponent(), glow.blueComponent(), alpha
            ).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSRect((orb_cx - rr, orb_cy - rr), (2*rr, 2*rr))).fill()

        # Orb core
        core_rect = AppKit.NSRect((orb_cx - r, orb_cy - r), (2*r, 2*r))
        core_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(core_rect)
        core.set()
        core_path.fill()

        # White rim
        AppKit.NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.9).set()
        core_path.setLineWidth_(2.0)
        core_path.stroke()

        # Project name
        title_attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.boldSystemFontOfSize_(13),
            AppKit.NSForegroundColorAttributeName: AppKit.NSColor.whiteColor(),
        }
        title = Foundation.NSString.stringWithString_("JarvisAI")
        title.drawAtPoint_withAttributes_((margin + 56, h - 36), title_attrs)

        # Text (wrap to two lines max)
        text = (self.state.get("text") or "").strip()
        if text:
            para = AppKit.NSMutableParagraphStyle.alloc().init()
            para.setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)
            body_attrs = {
                AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_(12),
                AppKit.NSForegroundColorAttributeName: AppKit.NSColor.whiteColor(),
                AppKit.NSParagraphStyleAttributeName: para,
            }
            body = Foundation.NSString.stringWithString_(text)
            body.drawInRect_withAttributes_(AppKit.NSRect((margin + 16, 12), (w - (margin + 32), h - 56)), body_attrs)


class OverlayWindow(AppKit.NSWindow):
    def canBecomeKeyWindow(self):
        return False
    def canBecomeMainWindow(self):
        return False


def read_state_periodically(view: OverlayView, stop_event: threading.Event):
    last_mtime = 0
    while not stop_event.is_set():
        try:
            st = os.stat(STATE_PATH)
            if st.st_mtime != last_mtime:
                last_mtime = st.st_mtime
                with open(STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Update on main thread
                    def _apply():
                        view.updateFromState(data)
                        view.setNeedsDisplay_(True)
                    AppKit.NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(
                        _apply, None, False
                    )
        except FileNotFoundError:
            pass
        except Exception:
            pass
        time.sleep(1.0 / FPS)


def position_top_right(width=400, height=110, margin=12):
    screen = AppKit.NSScreen.mainScreen()
    frame = screen.frame()
    x = frame.origin.x + frame.size.width - width - margin
    y = frame.origin.y + frame.size.height - height - margin
    return AppKit.NSRect((x, y), (width, height))


def run():
    app = AppKit.NSApplication.sharedApplication()
    rect = position_top_right()
    window = OverlayWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect,
        AppKit.NSWindowStyleMaskBorderless,
        AppKit.NSBackingStoreBuffered,
        False,
    )
    window.setOpaque_(False)
    window.setBackgroundColor_(AppKit.NSColor.clearColor())
    window.setLevel_(Quartz.kCGStatusWindowLevel)
    window.setIgnoresMouseEvents_(True)

    # Add a blurred background card using NSVisualEffectView
    effect = AppKit.NSVisualEffectView.alloc().initWithFrame_(AppKit.NSRect((0, 0), (rect.size.width, rect.size.height)))
    effect.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
    effect.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
    effect.setState_(AppKit.NSVisualEffectStateActive)
    window.setContentView_(effect)

    view = OverlayView.alloc().init()
    view.setFrame_(AppKit.NSRect((0, 0), (rect.size.width, rect.size.height)))
    effect.addSubview_(view)
    # Window starts hidden; visible toggled by state updates
    # Bring front only when visible flag is set
    # We'll manage visibility in the state reader
    # window.makeKeyAndOrderFront_(None)

    stop_event = threading.Event()
    def _reader():
        last_visible = False
        last_mtime = 0
        while not stop_event.is_set():
            try:
                st = os.stat(STATE_PATH)
                if st.st_mtime != last_mtime:
                    last_mtime = st.st_mtime
                    with open(STATE_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        def _apply():
                            view.updateFromState(data)
                            now_vis = bool(view.state.get("visible"))
                            if now_vis and not last_visible:
                                window.makeKeyAndOrderFront_(None)
                            if (not now_vis) and last_visible:
                                window.orderOut_(None)
                            return now_vis
                        # Perform on main thread and capture visibility
                        res = [last_visible]
                        def _apply_and_store():
                            res[0] = _apply()
                        AppKit.NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(_apply_and_store, None, True)
                        last_visible = bool(res[0])
            except FileNotFoundError:
                pass
            except Exception:
                pass
            time.sleep(1.0 / FPS)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    # Background ticker thread to request redraws at FPS
    def _ticker():
        while not stop_event.is_set():
            try:
                def _apply():
                    view.setNeedsDisplay_(True)
                AppKit.NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(
                    _apply, None, False
                )
            except Exception:
                pass
            time.sleep(1.0 / FPS)
    threading.Thread(target=_ticker, daemon=True).start()

    AppKit.NSApp.activateIgnoringOtherApps_(True)
    AppKit.NSApp.run()
    stop_event.set()


if __name__ == "__main__":
    run()
