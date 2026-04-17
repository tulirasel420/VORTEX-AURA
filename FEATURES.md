# 🔮 QUANTEX-BOT — Complete Feature Documentation

> **Official Telegram Bot**: [@QuantexBinaryTools_bot](https://t.me/QuantexBinaryTools_bot)  
> **Developer**: [@X_Akash_Owner](https://t.me/X_Akash_Owner)

---

## 📋 Feature Index

1. [Live Signal Engine](#1-live-signal-engine)
2. [Signal Checker Tool](#2-signal-checker-tool)
3. [Future Signal Engine](#3-future-signal-engine)
4. [MTG (Martingale) System](#4-mtg-martingale-system)
5. [Chart Generation](#5-chart-generation)
6. [Session Management](#6-session-management)
7. [Sleep Mode System](#7-sleep-mode-system)
8. [Scheduled Sessions](#8-scheduled-sessions)
9. [Partial Report System](#9-partial-report-system)
10. [License & Access System](#10-license--access-system)
11. [Admin Control Panel](#11-admin-control-panel)
12. [Points System](#12-points-system)
13. [Supported Markets & Pairs](#13-supported-markets--pairs)
14. [Multi-Platform Support](#14-multi-platform-support)

---

## 1. Live Signal Engine

The core of QUANTEX-BOT — a fully automated signal generation system using a **proprietary multi-indicator engine**.

### How Signals Are Generated

**Step 1 — Clock Sync**  
The bot synchronizes to the **5-minute candle clock**. Signals are only generated at exact 5-minute boundaries to ensure perfect M1 trade timing.

**Step 2 — Data Fetch**  
Latest candle data is fetched from the live market API for the selected pair.

**Step 3 — Proprietary Analysis Engine**  
QUANTEX-BOT runs its internal multi-factor analysis pipeline. The specific logic, parameters, and methods are proprietary and not disclosed.

**Step 4 — Confidence Scoring**  
Each signal is scored based on how many internal factors confirm the direction. Only signals reaching a high-confidence threshold are sent.

**Step 5 — Signal Sent**  
High-confidence signal delivered to Telegram with pair name, direction (BUY/CALL or SELL/PUT), entry time, confidence indicator, and candlestick chart.

**Step 6 — Result Check**  
After the candle closes, the bot automatically checks the result and sends a WIN or LOSS notification.

---

## 2. Signal Checker Tool

Verify the accuracy of signals from **any source** — QUANTEX-BOT, other bots, or any signal channel.

### Supported Input Formats

The universal parser handles virtually any signal format:

```
Format 1:  M1 EUR/USD 14:35 BUY
Format 2:  EURUSD_OTC | 14:35 | CALL
Format 3:  Pair: EURUSD | Time: 2:35 PM | Direction: UP
Format 4:  🔥 EUR/USD OTC ⬆️ 14:35
Format 5:  eurusd 14:35 buy  (case-insensitive)
```

### Pair Name Normalization

Automatically recognizes 100+ pair name variations and maps them to the correct canonical pair name.

### Result Modes

- **TODAY** — Check signals from today
- **YESTERDAY** — Check signals from yesterday

### Output Report

```
📊 SIGNAL CHECK RESULTS
━━━━━━━━━━━━━━━━━━━━━━
Total Signals  : 12
✅ WIN          : 8  (66.7%)
❌ LOSS         : 3  (25.0%)
🔄 MTG WIN      : 1  ( 8.3%)
━━━━━━━━━━━━━━━━━━━━━━
Win Rate       : 75.0%
```

---

## 3. Future Signal Engine

Generate predictive signals **before the market opens** or for upcoming time slots.

### Features
- Pre-market analysis across 100+ pairs
- OTC and Live market coverage
- Multi-broker output (Quotex, IQ Option)
- 3 different output formats

### Output Formats

**Format 1** — Minimal clean list  
**Format 2** — Detailed with timestamps and confidence  
**Format 3** — Full broadcast-ready formatted signals

---

## 4. MTG (Martingale) System

If the first signal results in a LOSS, QUANTEX-BOT can automatically activate a **Martingale recovery trade**.

### Logic
1. First signal sent → LOSS detected
2. MTG mode activates for that pair
3. At the next 5-min slot, a recovery signal is analyzed
4. Recovery signal sent with `[MTG]` tag
5. Result tracked as `MTG WIN` or `MTG LOSS`

> ⚠️ MTG doubles the stake — use with proper money management.

---

## 5. Chart Generation

Every signal comes with a professional candlestick chart.

### Signal Chart
- Recent candles displayed with entry point clearly marked
- Direction color coding (green = BUY, red = SELL)
- Proprietary indicator overlays
- Historical win-rate statistics
- Pair name, timeframe, and timestamp

### Result Chart
- Same chart with WIN/LOSS result overlay
- MTG entries annotated

---

## 6. Session Management

QUANTEX-BOT handles multiple concurrent users, each with their own independent session.

### Session States
| State | Description |
|---|---|
| `IDLE` | User is at main menu |
| `RUNNING` | Active signal session in progress |
| `SETUP` | In configuration wizard |
| `PAUSED` | Session paused (sleep mode) |

### Configuration Options
1. **Chat** — Which chat to send signals to (DM or group)
2. **Username** — Broker username for tracking
3. **Mode** — Single pair or Auto (best signal from all pairs)
4. **Market Type** — OTC or Live
5. **Trading Pairs** — Select specific pairs or "All"
6. **Charts** — Enable/disable signal and result charts
7. **Partial Reports** — Auto-report interval (5/10/15/30/60 min or OFF)

---

## 7. Sleep Mode System

QUANTEX-BOT automatically **pauses** during high-volatility market hours.

### Default Sleep Window
- **7:00 PM → 10:00 PM** daily
- During this period, market conditions cause signal accuracy to drop significantly

### Behavior During Sleep
- All active sessions are stopped
- All licensed users are notified
- New session attempts are blocked with explanation
- Bot resumes automatically at 10:00 PM with notifications

### Admin Controls
- Exempt specific users from sleep mode
- Disable sleep mode entirely
- Configure custom sleep windows

---

## 8. Scheduled Sessions

Users can schedule QUANTEX-BOT to **automatically start sessions** at specific times.

### How to Set a Schedule
1. Go to **Schedule** menu
2. Select days of week (Mon–Sun, any combination)
3. Set start time and optional stop time
4. Save — bot fires sessions automatically each week

---

## 9. Partial Report System

Track your session performance in real-time with automatic reports.

### Report Intervals
Every 5 / 10 / 15 / 30 / 60 minutes, or manual only.

### Report Content
```
📊 PARTIAL REPORT — 15:30
━━━━━━━━━━━━━━━━━━━━━━
Session: @username
Signals Sent : 6
✅ WIN        : 4
❌ LOSS       : 1
🔄 MTG WIN    : 1
━━━━━━━━━━━━━━━━━━━━━━
Win Rate     : 83.3%
```

---

## 10. License & Access System

### License Types
| Type | Duration | Access |
|---|---|---|
| Monthly | 30 days | Full access |
| Quarterly | 90 days | Full access |
| Semi-Annual | 180 days | Full access |
| Lifetime | Permanent | Full access + VIP |

Encrypted license keys are tied to Telegram user ID. Keys cannot be shared or transferred.

### Promo Codes
Admin can issue promo codes for free trials, discounts, or special event access.

---

## 11. Admin Control Panel

| Action | Function |
|---|---|
| Broadcast | Send message to all or licensed users |
| Grant / Revoke License | Manage user access |
| Add Points | Grant feature-use points |
| Pair On/Off | Enable/disable trading pairs globally |
| Maintenance Mode | Enable maintenance with custom message |
| Sleep Exempt | Exempt users from sleep mode |
| User Management | View all registered users and status |

---

## 12. Points System

Free users access specific features using **points**.

- Admin grants points
- Each Future Signal or Signal Check costs 1 point
- Licensed users have unlimited access
- Point balance visible in bot menu

---

## 13. Supported Markets & Pairs

- **OTC Forex** — 40+ major, minor, and exotic pairs (Quotex)
- **OTC Stocks** — Popular global stocks as binary options
- **OTC Crypto** — Bitcoin, Ethereum, and 50+ crypto assets
- **OTC Indices** — US, European, and Asian market indices
- **Live Forex** — All major and minor Forex pairs

---

## 14. Multi-Platform Support

| Platform | Support |
|---|---|
| **Windows** | ✅ Full |
| **Linux** | ✅ Full |
| **macOS** | ✅ Full |
| **Android (Termux)** | ✅ Full |

Auto dependency installer handles all required packages on first run — zero manual setup needed.

---

## 📞 Support

- **Telegram**: [@X_Akash_Owner](https://t.me/X_Akash_Owner)
- **Email**: [quantexbotsupport@gmail.com](mailto:quantexbotsupport@gmail.com)
- **Channel**: [@Quantexbot1](https://t.me/Quantexbot1)
- **Bot**: [@QuantexBinaryTools_bot](https://t.me/QuantexBinaryTools_bot)
