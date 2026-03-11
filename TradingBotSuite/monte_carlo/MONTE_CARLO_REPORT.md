# Monte Carlo Simulation Report - High Frequency Quant V3
## Date: March 9, 2026
## Strategy: Mean Reversion Scalping on QQQ

---

## 📊 SIMULATION PARAMETERS

| Parameter | Value |
|-----------|-------|
| Strategy | High Frequency Quant V3 |
| Timeframe | 15-minute candles |
| Win Rate | 55% |
| Risk/Reward | 1:2 |
| Simulations | 1,000 months |
| Days per Month | 30 |

---

## 💰 SCENARIO 1: £30/DAY RISK (£900/MONTH CAP)

### Monthly Profit Distribution
| Metric | Value |
|--------|-------|
| **Expected Monthly Profit** | **£471.06** |
| Median | £462.90 |
| Standard Deviation | £200.16 |
| **Best Case (95th percentile)** | **£806.25** |
| **Worst Case (5th percentile)** | **£155.94** |
| Absolute Best Month | £1,141.51 |
| Absolute Worst Month | **-£202.67** |

### Probability Analysis
| Outcome | Probability |
|---------|-------------|
| P(Monthly Profit > £0) | **99.2%** ✅ |
| **P(Monthly Profit ≥ £500)** | **43.6%** ⚠️ |
| P(Monthly Profit ≥ £1000) | 0.6% |
| P(Monthly Loss) | 0.8% |
| P(Loss > £450) | 0.0% |

### Risk Metrics
| Metric | Value |
|--------|-------|
| Monthly Risk Cap | £900.00 |
| Risk of Ruin (>£900 loss) | **0.0%** ✅ |
| Max Drawdown (Observed) | £202.67 |

---

## 💰 SCENARIO 2: £40/DAY RISK (£1,200/MONTH CAP) ⭐ RECOMMENDED

### Monthly Profit Distribution
| Metric | Value |
|--------|-------|
| **Expected Monthly Profit** | **£628.05** |
| Median | £617.20 |
| Standard Deviation | £266.85 |
| **Best Case (95th percentile)** | **£1,075.01** |
| **Worst Case (5th percentile)** | **£207.92** |
| Absolute Best Month | £1,522.01 |
| Absolute Worst Month | **-£270.23** |

### Probability Analysis
| Outcome | Probability |
|---------|-------------|
| P(Monthly Profit > £0) | **99.2%** ✅ |
| **P(Monthly Profit ≥ £500)** | **67.3%** ✅ |
| P(Monthly Profit ≥ £1000) | 8.1% |
| P(Monthly Loss) | 0.8% |
| P(Loss > £600) | 0.0% |

### Risk Metrics
| Metric | Value |
|--------|-------|
| Monthly Risk Cap | £1,200.00 |
| Risk of Ruin (>£1,200 loss) | **0.0%** ✅ |
| Max Drawdown (Observed) | £270.23 |

---

## 🎯 HEAD-TO-HEAD COMPARISON

| Metric | £30/day | £40/day |
|--------|---------|---------|
| Monthly Risk Cap | £900 | £1,200 |
| Expected Monthly Profit | £471 | £628 |
| **P(£500+/month)** | **44%** | **67%** ⭐ |
| P(£1000+/month) | 0.6% | 8.1% |
| P(Loss) | 0.8% | 0.8% |
| Worst Month | -£203 | -£270 |
| Risk of Ruin | 0% | 0% |

---

## ✅ FINAL RECOMMENDATION

### **RISK £40 PER DAY**

**Why £40/day is optimal:**
- **67% chance** of making £500+/month (YOUR TARGET) ✅
- Expected profit of **£628/month**
- **2 out of 3 months** you'll hit £500
- Worst loss observed: **-£270** (well under £1,200 cap)
- **99.2% chance** of ANY profit
- **0% risk of ruin**

### Risk Management Rules
1. **Daily Limit**: £40 max risk per day
2. **Monthly Limit**: £1,200 max risk per month (30 days)
3. **Stop Trading**: If down £600 in a month (50% of cap)
4. **Take Profits**: Lock in gains if up £1,000+

---

## 📁 FILES IN THIS FOLDER

- `MONTE_CARLO_REPORT.md` - This report
- `run_mc_fixed.py` - Simulation script (in parent directory)

---

**Note**: Past performance does not guarantee future results. Trade at your own risk.
Generated: March 9, 2026
