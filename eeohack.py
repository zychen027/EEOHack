#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEO 直播刷赞脚本 v4 - GUI版
- 移除总数限制，永远请求
- 详细请求日志（只保留account）
- 精美GUI（日志框 / 开始暂停按钮 / lessonKey输入框开始后彻底隐藏）
- 暂停/停止按钮在开始后才出现
"""

import json
import base64
import random
import time
import uuid
import threading
import tkinter as tk
from tkinter import font as tkfont
from urllib.parse import quote
from datetime import datetime

import requests

# ==================== 配置 ====================
LIKE_API = "https://wsk-live.eeo.cn/webcast/like"
DELAY = 0.3

# ==================== 颜色主题 ====================
C = {
    "bg_dark":      "#1a1b2e",
    "bg_medium":    "#242640",
    "bg_light":     "#2e3050",
    "bg_input":     "#3a3c5c",
    "accent":       "#6c5ce7",
    "accent_hover": "#7f70f0",
    "pause_clr":    "#e17055",
    "pause_hover":  "#f08370",
    "stop_clr":     "#636e72",
    "stop_hover":   "#7f8c8d",
    "success":      "#00b894",
    "error":        "#d63031",
    "warning":      "#fdcb6e",
    "text_pri":     "#f5f5f5",
    "text_sec":     "#b2b2d0",
    "text_dim":     "#6c6c8a",
    "border":       "#3a3c5c",
    "log_bg":       "#12131f",
    "sb":           "#4a4c6c",
    "sb_hover":     "#5a5c7c",
}


# ==================== Account 生成 ====================
def gen_account():
    return uuid.uuid4().hex


# ==================== Cookie 伪造 ====================
def gen_sensors_id():
    t = hex(int(time.time() * 1000) + random.randint(0, 9999))[2:]
    seg0 = (t[:8] + ''.join(random.choices('0123456789abcdef', k=6)))[:14]
    seg1 = ''.join(random.choices('0123456789abcdef', k=14))
    seg2 = ''.join(random.choices('0123456789abcdef', k=8))
    seg3 = ''.join(random.choices('0123456789abcdef', k=7))
    t2 = hex(int(time.time() * 1000) + random.randint(1, 10000))[2:]
    seg4 = (t2[:8] + ''.join(random.choices('0123456789abcdef', k=6)))[:14]
    return seg0 + "-" + seg1 + "-" + seg2 + "-" + seg3 + "-" + seg4


def build_cookies(account):
    did = gen_sensors_id()
    id_obj = {"$identity_cookie_id": did, "$identity_login_id": account}
    id_b64 = base64.b64encode(json.dumps(id_obj, separators=(",", ":")).encode()).decode()
    payload = {
        "distinct_id": did,
        "first_id": "",
        "props": {
            "$latest_traffic_source_type": "直接流量",
            "$latest_search_keyword": "未取到值_直接打开",
            "$latest_referrer": "",
        },
        "identities": id_b64,
        "history_login_id": {"name": "", "value": account},
        "$device_id": did,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    sensors = quote(raw, safe="")
    return {
        "sajssdk_2015_cross_new_user": "1",
        "sensorsdata2015jssdkcross": sensors,
        "tgw_l7_route": uuid.uuid4().hex,
        "cookiefedc9b7ec05f50f0aEAddZJXsyk_aEAddZJXs": "e",
    }


# ==================== 请求头 ====================
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://live.eeo.cn",
    "referer": "https://live.eeo.cn/",
    "sec-ch-ua": '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
}


# ==================== GUI 应用 ====================
class EEOApp:

    def __init__(self, root):
        self.root = root
        self.root.title("EEO 直播刷赞 v4")
        self.root.geometry("780x660")
        self.root.minsize(640, 520)
        self.root.configure(bg=C["bg_dark"])

        self.running = False
        self.paused = False
        self.ok_count = 0
        self.fail_count = 0
        self.req_idx = 0
        self.lesson_key = ""

        self._stats_dirty = False
        self._log_queue = []
        self._log_scheduled = False

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self._build_ui()
        self._center_window()

    # ==================== 窗口居中 ====================
    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

    # ==================== 构建界面 ====================
    def _build_ui(self):
        f_title = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        f_sub = tkfont.Font(family="Segoe UI", size=10)
        f_btn = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        f_input = tkfont.Font(family="Consolas", size=12)
        f_stat = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        f_key = tkfont.Font(family="Consolas", size=9)
        f_log = tkfont.Font(family="Consolas", size=9)
        f_log_h = tkfont.Font(family="Consolas", size=9, weight="bold")

        # ---- 顶部标题 ----
        hdr = tk.Frame(self.root, bg=C["bg_medium"])
        hdr.pack(fill=tk.X, ipady=16)

        hdr_top = tk.Frame(hdr, bg=C["bg_medium"])
        hdr_top.pack(fill=tk.X, padx=28)

        tk.Label(hdr_top, text="⚡  EEO 直播刷赞", font=f_title,
                 fg=C["text_pri"], bg=C["bg_medium"]).pack(side=tk.LEFT)

        self.lbl_key = tk.Label(
            hdr_top, text="", font=f_key,
            fg=C["accent"], bg=C["bg_medium"],
        )
        self.lbl_key.pack(side=tk.RIGHT, pady=(6, 0))

        tk.Label(hdr, text="无限请求  ·  详细日志  ·  一键控制",
                 font=f_sub, fg=C["text_dim"], bg=C["bg_medium"]).pack(pady=(2, 0))

        # ---- 输入区（开始后彻底隐藏销毁）----
        self.input_frame = tk.Frame(self.root, bg=C["bg_dark"])
        self.input_frame.pack(fill=tk.X, padx=28, pady=(12, 12))

        tk.Label(self.input_frame, text="Lesson Key", font=f_stat,
                 fg=C["text_sec"], bg=C["bg_dark"]).pack(anchor=tk.W)

        wrap = tk.Frame(self.input_frame, bg=C["border"], bd=1)
        wrap.pack(fill=tk.X, pady=(6, 0), ipady=1)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            wrap, textvariable=self.entry_var, font=f_input,
            fg=C["text_pri"], bg=C["bg_input"],
            insertbackground=C["accent"], relief=tk.FLAT, bd=8,
        )
        self.entry.pack(fill=tk.X)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._start())

        # ---- 统计栏 ----
        sbar = tk.Frame(self.root, bg=C["bg_medium"])
        sbar.pack(fill=tk.X, padx=28, ipady=8)

        self.lbl_total = self._mk_stat(sbar, "请求: 0", C["text_pri"])
        self.lbl_ok = self._mk_stat(sbar, "成功: 0", C["success"])
        self.lbl_fail = self._mk_stat(sbar, "失败: 0", C["error"])
        self.lbl_rate = self._mk_stat(sbar, "成功率: --", C["warning"])

        # ---- 按钮栏 ----
        bbar = tk.Frame(self.root, bg=C["bg_dark"])
        bbar.pack(fill=tk.X, padx=28, pady=(10, 10))

        self.btn_start = tk.Button(
            bbar, text="▶  开 始", font=f_btn,
            fg=C["text_pri"], bg=C["accent"],
            activeforeground=C["text_pri"], activebackground=C["accent_hover"],
            relief=tk.FLAT, bd=0, padx=28, pady=8, cursor="hand2",
            command=self._on_start_click,
        )
        self.btn_start.pack(side=tk.LEFT, ipadx=16)

        self.btn_pause = tk.Button(
            bbar, text="⏸  暂 停", font=f_btn,
            fg=C["text_pri"], bg=C["pause_clr"],
            activeforeground=C["text_pri"], activebackground=C["pause_hover"],
            relief=tk.FLAT, bd=0, padx=28, pady=8, cursor="hand2",
            command=self._toggle_pause,
        )

        self.btn_stop = tk.Button(
            bbar, text="■  停 止", font=f_btn,
            fg=C["text_pri"], bg=C["stop_clr"],
            activeforeground=C["text_pri"], activebackground=C["stop_hover"],
            relief=tk.FLAT, bd=0, padx=28, pady=8, cursor="hand2",
            command=self._stop,
        )

        self.status_var = tk.StringVar(value="● 就绪")
        self.lbl_status = tk.Label(
            bbar, textvariable=self.status_var, font=f_sub,
            fg=C["text_dim"], bg=C["bg_dark"],
        )
        self.lbl_status.pack(side=tk.RIGHT)

        # ---- 日志区 ----
        lout = tk.Frame(self.root, bg=C["bg_dark"])
        lout.pack(fill=tk.BOTH, expand=True, padx=18, pady=(4, 14))

        tk.Label(lout, text="📋  请求日志", font=f_stat,
                 fg=C["text_sec"], bg=C["bg_dark"]).pack(anchor=tk.W, pady=(0, 4))

        lbox = tk.Frame(lout, bg=C["border"], bd=1)
        lbox.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            lbox, font=f_log, bg=C["log_bg"], fg=C["text_sec"],
            insertbackground=C["accent"], relief=tk.FLAT, bd=8,
            wrap=tk.NONE, state=tk.DISABLED,
            selectbackground=C["accent"], selectforeground=C["text_pri"],
        )
        sb_h = tk.Scrollbar(
            lbox, orient=tk.HORIZONTAL, command=self.log_text.xview,
            bg=C["sb"], troughcolor=C["log_bg"],
            activebackground=C["sb_hover"], relief=tk.FLAT, bd=0,
        )
        sb_v = tk.Scrollbar(
            lbox, orient=tk.VERTICAL, command=self.log_text.yview,
            bg=C["sb"], troughcolor=C["log_bg"],
            activebackground=C["sb_hover"], relief=tk.FLAT, bd=0, width=10,
        )
        self.log_text.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side=tk.RIGHT, fill=tk.Y)
        sb_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for tag, color in [
            ("ts", C["text_dim"]),
            ("info", C["text_sec"]),
            ("ok", C["success"]),
            ("err", C["error"]),
            ("warn", C["warning"]),
            ("hdr", C["accent"]),
        ]:
            kw = {"foreground": color}
            if tag == "hdr":
                kw["font"] = f_log_h
            self.log_text.tag_configure(tag, **kw)

    def _mk_stat(self, parent, text, color):
        f_stat = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        lbl = tk.Label(parent, text=text, font=f_stat, fg=color, bg=C["bg_medium"])
        lbl.pack(side=tk.LEFT, padx=(0, 22))
        return lbl

    # ==================== 日志（批量写入优化）====================
    def _log(self, msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_queue.append((ts, msg, tag))
        if not self._log_scheduled:
            self._log_scheduled = True
            self.root.after(50, self._flush_logs)

    def _flush_logs(self):
        self._log_scheduled = False
        if not self._log_queue:
            return
        self.log_text.configure(state=tk.NORMAL)
        for ts, msg, tag in self._log_queue:
            self.log_text.insert(tk.END, f"[{ts}] ", "ts")
            self.log_text.insert(tk.END, f"{msg}\n", tag)
        self._log_queue.clear()
        self.log_text.see(tk.END)
        n = int(self.log_text.index("end-1c").split(".")[0])
        if n > 3000:
            self.log_text.delete("1.0", "1000.0")
        self.log_text.configure(state=tk.DISABLED)

    # ==================== 统计（节流优化）====================
    def _mark_stats_dirty(self):
        if not self._stats_dirty:
            self._stats_dirty = True
            self.root.after(200, self._flush_stats)

    def _flush_stats(self):
        self._stats_dirty = False
        t = self.ok_count + self.fail_count
        r = f"{self.ok_count / t * 100:.1f}%" if t else "--"
        self.lbl_total.configure(text=f"请求: {t}")
        self.lbl_ok.configure(text=f"成功: {self.ok_count}")
        self.lbl_fail.configure(text=f"失败: {self.fail_count}")
        self.lbl_rate.configure(text=f"成功率: {r}")

    # ==================== 控制逻辑 ====================
    def _on_start_click(self):
        if not self.running:
            self._start()

    def _start(self):
        key = self.entry_var.get().strip()
        if not key:
            self._log("⚠  请先输入 lessonKey！", "err")
            self.entry.focus_set()
            return
        self.lesson_key = key
        self.running = True
        self.paused = False
        self.ok_count = 0
        self.fail_count = 0
        self.req_idx = 0

        # ★ 输入框彻底销毁
        self.input_frame.pack_forget()
        self.input_frame.destroy()
        self.input_frame = None

        # ★ 开始按钮隐藏，暂停/停止按钮出现
        self.btn_start.pack_forget()
        self.btn_pause.pack(side=tk.LEFT, ipadx=16, padx=(0, 10))
        self.btn_pause.configure(text="⏸  暂 停", bg=C["pause_clr"])
        self.btn_stop.pack(side=tk.LEFT, ipadx=16)

        # 标题栏右侧显示当前 key
        self.lbl_key.configure(text=f"🔑 {key}")

        self.lbl_status.configure(text="● 运行中", fg=C["success"])

        self._log("=" * 50, "hdr")
        self._log(f"🚀  开始刷赞  lessonKey = {self.lesson_key}", "hdr")
        self._log(f"    延迟 {DELAY}s  |  无限模式", "hdr")
        self._log("=" * 50, "hdr")
        self._mark_stats_dirty()

        threading.Thread(target=self._worker, daemon=True).start()

    def _toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.configure(text="▶  继 续", bg=C["accent"])
            self.lbl_status.configure(text="● 已暂停", fg=C["warning"])
            self._log("⏸  已暂停", "warn")
        else:
            self.btn_pause.configure(text="⏸  暂 停", bg=C["pause_clr"])
            self.lbl_status.configure(text="● 运行中", fg=C["success"])
            self._log("▶  已恢复", "ok")

    def _stop(self):
        self.running = False
        self.paused = False

        self.btn_pause.pack_forget()
        self.btn_stop.pack_forget()
        self.btn_start.pack(side=tk.LEFT, ipadx=16)
        self.btn_start.configure(state=tk.DISABLED, text="✓  已结束")

        self.lbl_status.configure(text="● 已停止", fg=C["text_dim"])

        self._log("=" * 50, "hdr")
        self._log(f"⏹  已停止  成功={self.ok_count}  失败={self.fail_count}", "hdr")
        self._log("💡  如需更换 lessonKey，请重新启动程序", "warn")
        self._log("", "info")

        self._flush_logs()
        self._flush_stats()

    # ==================== 工作线程 ====================
    def _worker(self):
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
            self.req_idx += 1
            self._send_like(self.req_idx)
            self._mark_stats_dirty()
            end = time.time() + DELAY
            while self.running and time.time() < end:
                time.sleep(0.05)

    def _send_like(self, idx):
        account = gen_account()
        cookies = build_cookies(account)
        data = {"account": account, "lessonKey": self.lesson_key}

        # ★ 只保留 account
        self._log(f"#{idx} →  account={account}", "info")

        try:
            t0 = time.time()
            r = requests.post(
                LIKE_API, data=data, headers=HEADERS,
                cookies=cookies, timeout=10,
            )
            ms = (time.time() - t0) * 1000
            sc = r.status_code
            body = r.json()
            code = body.get("code", -1)
            msg = body.get("msg", "")
            resp_text = r.text

            if "Error" in msg and "required" in msg:
                self.fail_count += 1
                self._log(
                    f"#{idx} ✗  缺字段  |  HTTP {sc}  code={code}  "
                    f"msg={msg}  |  {ms:.0f}ms  |  resp={resp_text}",
                    "err",
                )
                return False

            if code == 1 and "Error" not in msg:
                self.ok_count += 1
                self._log(
                    f"#{idx} ✓  成功  |  HTTP {sc}  code={code}  "
                    f"msg={msg}  |  {ms:.0f}ms",
                    "ok",
                )
                return True

            self.fail_count += 1
            self._log(
                f"#{idx} ✗  异常  |  HTTP {sc}  code={code}  "
                f"msg={msg}  |  {ms:.0f}ms  |  resp={resp_text}",
                "err",
            )
            return False

        except requests.Timeout:
            self.fail_count += 1
            self._log(f"#{idx} ✗  超时 (>10s)  |  account={account}", "err")
            return False
        except requests.ConnectionError as e:
            self.fail_count += 1
            self._log(f"#{idx} ✗  连接失败  |  account={account}  |  {e}", "err")
            return False
        except Exception as e:
            self.fail_count += 1
            self._log(f"#{idx} ✗  {type(e).__name__}: {e}  |  account={account}", "err")
            return False


# ==================== 入口 ====================
def main():
    root = tk.Tk()
    EEOApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
