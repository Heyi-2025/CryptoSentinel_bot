# CryptoSentinel 指标扩充指南

> 本文档介绍如何为 CryptoSentinel 添加新的技术指标

---

## 目录

1. [系统架构概览](#一系统架构概览)
2. [添加新指标完整步骤](#二添加新指标的完整步骤)
3. [常用指标计算公式](#三常用指标计算公式)
4. [信号检测模式](#四信号检测模式)
5. [可添加指标列表](#五可添加指标列表)
6. [高级功能建议](#六高级功能建议)

---

## 一、系统架构概览

### 1.1 数据流向

```
用户添加订阅 → bot.py
       ↓
存储到数据库 → db_manager.py
       ↓
行情引擎读取订阅 → market_engine.py
       ↓
计算指标写入缓存 → cryptosentinel_cache.json
       ↓
信号监控器读取缓存 → notifier.py
       ↓
检测信号发送通知 → 用户收到消息
```

### 1.2 核心文件职责

| 文件 | 职责 | 添加指标时需要修改 |
|------|------|-------------------|
| `market_engine.py` | 计算技术指标 | ✅ 添加计算函数 |
| `notifier.py` | 信号检测逻辑 | ✅ 添加检测函数 |
| `bot.py` | 用户交互界面 | ✅ 添加指标选项 |
| `locales/zh.py` | 中文消息模板 | ✅ 添加消息文本 |
| `locales/en.py` | 英文消息模板 | ✅ 添加消息文本 |
| `db_manager.py` | 数据库存储 | 可能需要修改参数存储 |

---

## 二、添加新指标的完整步骤

### 步骤 1：在 `market_engine.py` 添加计算函数

**位置**：文件开头，其他计算函数附近

```python
def calculate_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """
    计算 RSI 指标
    
    Args:
        series: 收盘价序列
        length: RSI 周期，默认 14
    
    Returns:
        RSI 值序列 (0-100)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

**位置**：`fetch_and_calc()` 函数中，找到 EMA_169 计算的位置，在其后添加

```python
# 计算 RSI
rsi_14 = calculate_rsi(df["close"], 14)
result["RSI_14"] = float(rsi_14.iloc[-1]) if not pd.isna(rsi_14.iloc[-1]) else None
```

---

### 步骤 2：在 `notifier.py` 添加信号检测

**位置**：`check_bb_signal_change` 函数附近

```python
def check_rsi_signal(
    market_data: Dict[str, Any],
    prev_state: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    检查 RSI 信号
    
    Args:
        market_data: 当前行情数据
        prev_state: 上一次的状态
    
    Returns:
        "oversold": 进入超卖区 (RSI < 30)
        "overbought": 进入超买区 (RSI > 70)
        "exit_oversold": 离开超卖区
        "exit_overbought": 离开超买区
        None: 无信号
    """
    rsi = market_data.get("RSI_14")
    if rsi is None:
        return None
    
    prev_rsi = prev_state.get("rsi") if prev_state else None
    
    # 超卖信号
    if rsi < 30 and (prev_rsi is None or prev_rsi >= 30):
        return "oversold"
    
    # 离开超卖
    if rsi >= 30 and prev_rsi is not None and prev_rsi < 30:
        return "exit_oversold"
    
    # 超买信号
    if rsi > 70 and (prev_rsi is None or prev_rsi <= 70):
        return "overbought"
    
    # 离开超买
    if rsi <= 70 and prev_rsi is not None and prev_rsi > 70:
        return "exit_overbought"
    
    return None
```

**位置**：`check_signal()` 函数中，在 `if indicator == "BB":` 后添加

```python
elif indicator == "RSI":
    signal_type = check_rsi_signal(market_data, prev_state)
    
    if signal_type is None:
        return None
    
    symbol = market_data.get("symbol")
    rsi = market_data.get("RSI_14")
    
    if signal_type == "oversold":
        return f"📉 RSI 超卖信号\n{symbol} RSI({rsi:.1f}) 进入超卖区 (<30)"
    elif signal_type == "overbought":
        return f"📈 RSI 超买信号\n{symbol} RSI({rsi:.1f}) 进入超买区 (>70)"
    elif signal_type == "exit_oversold":
        return f"✅ RSI 离开超卖\n{symbol} RSI({rsi:.1f}) 离开超卖区"
    elif signal_type == "exit_overbought":
        return f"✅ RSI 离开超买\n{symbol} RSI({rsi:.1f}) 离开超买区"
    
    return None
```

**位置**：`update_signal_state()` 函数中，添加状态更新

```python
# 在函数开头添加变量
rsi = market_data.get("RSI_14")

# 在 _signal_state 字典中添加
_signal_state[sub_id] = {
    "timestamp": timestamp,
    "bb_triggered": ...,
    "rsi": rsi if rsi is not None else 50,
    ...
}
```

---

### 步骤 3：在 `bot.py` 添加用户界面

**位置**：`add_flow_callback()` 函数中，找到指标选择按钮

```python
keyboard = [
    [
        InlineKeyboardButton("BB 布林带", callback_data="add_BB"),
        InlineKeyboardButton("VEGAS 通道", callback_data="add_VEGAS"),
    ],
    [
        InlineKeyboardButton("RSI", callback_data="add_RSI"),
        # InlineKeyboardButton("MACD", callback_data="add_MACD"),
    ],
    [InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="menu_add")]
]
```

**位置**：`add_flow_callback()` 函数中，处理指标确认

```python
elif data in ["add_BB", "add_VEGAS", "add_RSI"]:
    indicator = data.replace("add_", "")
    context.user_data["add_flow"]["step"] = "confirm"
    context.user_data["add_flow"]["indicator"] = indicator
    
    # 设置参数
    if indicator == "BB":
        params = {"period": 20, "std_dev": 2}
        indicator_name = "BB 布林带"
    elif indicator == "VEGAS":
        params = {"ema_fast": 144, "ema_slow": 169}
        indicator_name = "VEGAS 通道"
    elif indicator == "RSI":
        params = {"length": 14, "oversold": 30, "overbought": 70}
        indicator_name = "RSI 相对强弱"
```

---

### 步骤 4：在 `locales/zh.py` 添加消息文本

```python
# 在 MESSAGES 字典中添加
"indicator_rsi": "RSI 相对强弱",
"rsi_oversold": "📉 RSI 超卖信号\n{symbol} RSI({rsi:.1f}) 进入超卖区 (<30)",
"rsi_overbought": "📈 RSI 超买信号\n{symbol} RSI({rsi:.1f}) 进入超买区 (>70)",
"rsi_exit_oversold": "✅ RSI 离开超卖\n{symbol} RSI({rsi:.1f}) 离开超卖区",
"rsi_exit_overbought": "✅ RSI 离开超买\n{symbol} RSI({rsi:.1f}) 离开超买区",
```

---

## 三、常用指标计算公式

### 3.1 RSI (相对强弱指数)

```python
def calculate_rsi(series, length=14):
    """
    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

**信号**：
- RSI < 30：超卖（买入信号）
- RSI > 70：超买（卖出信号）

---

### 3.2 MACD (指数平滑异同移动平均线)

```python
def calculate_macd(series, fast=12, slow=26, signal=9):
    """
    MACD = EMA(12) - EMA(26)
    Signal = EMA(MACD, 9)
    Histogram = MACD - Signal
    """
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line.iloc[-1],
        "signal": signal_line.iloc[-1],
        "histogram": histogram.iloc[-1]
    }
```

**信号**：
- MACD 上穿 Signal：金叉（买入）
- MACD 下穿 Signal：死叉（卖出）
- Histogram 由负转正：趋势转强

---

### 3.3 KDJ (随机指标)

```python
def calculate_kdj(df, n=9, m1=3, m2=3):
    """
    RSV = (Close - MinN) / (MaxN - MinN) * 100
    K = SMA(RSV, m1)
    D = SMA(K, m2)
    J = 3K - 2D
    """
    low_min = df["low"].rolling(window=n).min()
    high_max = df["high"].rolling(window=n).max()
    rsv = (df["close"] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(alpha=1/m1).mean()
    d = k.ewm(alpha=1/m2).mean()
    j = 3 * k - 2 * d
    return {
        "k": k.iloc[-1],
        "d": d.iloc[-1],
        "j": j.iloc[-1]
    }
```

**信号**：
- K 上穿 D：金叉
- K 下穿 D：死叉
- J > 100：超买
- J < 0：超卖

---

### 3.4 MA 金叉死叉

```python
def calculate_ma(series, short=7, long=25):
    """
    MA短期上穿MA长期：金叉
    MA短期下穿MA长期：死叉
    """
    ma_short = series.rolling(window=short).mean()
    ma_long = series.rolling(window=long).mean()
    return {
        "ma_short": ma_short.iloc[-1],
        "ma_long": ma_long.iloc[-1]
    }
```

**信号**：
- 短期 MA 上穿长期 MA：金叉
- 短期 MA 下穿长期 MA：死叉

---

### 3.5 ATR (真实波幅)

```python
def calculate_atr(df, length=14):
    """
    TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = SMA(TR, length)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low - close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()
```

**用途**：
- 波动率监控
- 止损位设置
- 突破确认

---

### 3.6 Keltner Channel (肯特纳通道)

```python
def calculate_keltner(df, length=20, mult=2):
    """
    中轨 = EMA(Close, 20)
    上轨 = 中轨 + ATR * 2
    下轨 = 中轨 - ATR * 2
    """
    ema = df["close"].ewm(span=length).mean()
    atr = calculate_atr(df, length)
    upper = ema + atr * mult
    lower = ema - atr * mult
    return {
        "upper": upper.iloc[-1],
        "middle": ema.iloc[-1],
        "lower": lower.iloc[-1]
    }
```

**信号**：
- 价格突破上轨：强势
- 价格突破下轨：弱势

---

### 3.7 CCI (顺势指标)

```python
def calculate_cci(df, length=20):
    """
    CCI = (TP - SMA(TP)) / (0.015 * MAD)
    TP = (High + Low + Close) / 3
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(window=length).mean()
    mad = tp.rolling(window=length).apply(lambda x: abs(x - x.mean()).mean())
    cci = (tp - sma) / (0.015 * mad)
    return cci.iloc[-1]
```

**信号**：
- CCI > 100：超买
- CCI < -100：超卖

---

### 3.8 Williams %R

```python
def calculate_williams_r(df, length=14):
    """
    %R = (Highest High - Close) / (Highest High - Lowest Low) * (-100)
    """
    high_max = df["high"].rolling(window=length).max()
    low_min = df["low"].rolling(window=length).min()
    wr = (high_max - df["close"]) / (high_max - low_min) * (-100)
    return wr.iloc[-1]
```

**信号**：
- %R > -20：超买
- %R < -80：超卖

---

## 四、信号检测模式

### 4.1 阈值突破模式

**适用指标**：RSI、KDJ、CCI、Williams %R

```python
def check_threshold_signal(value, prev_value, upper_threshold, lower_threshold):
    """
    检测阈值突破
    
    Returns:
        "enter_upper": 进入上方区域
        "exit_upper": 离开上方区域
        "enter_lower": 进入下方区域
        "exit_lower": 离开下方区域
        None: 无信号
    """
    if value > upper_threshold and (prev_value is None or prev_value <= upper_threshold):
        return "enter_upper"
    if value <= upper_threshold and prev_value is not None and prev_value > upper_threshold:
        return "exit_upper"
    if value < lower_threshold and (prev_value is None or prev_value >= lower_threshold):
        return "enter_lower"
    if value >= lower_threshold and prev_value is not None and prev_value < lower_threshold:
        return "exit_lower"
    return None
```

---

### 4.2 交叉信号模式

**适用指标**：MACD、MA、KDJ

```python
def check_cross_signal(fast_line, slow_line, prev_fast, prev_slow):
    """
    检测两条线的交叉
    
    Returns:
        "golden_cross": 金叉（快线上穿慢线）
        "death_cross": 死叉（快线下穿慢线）
        None: 无信号
    """
    # 金叉：之前快线 <= 慢线，现在快线 > 慢线
    if fast_line > slow_line:
        if prev_fast is not None and prev_slow is not None:
            if prev_fast <= prev_slow:
                return "golden_cross"
    
    # 死叉：之前快线 >= 慢线，现在快线 < 慢线
    if fast_line < slow_line:
        if prev_fast is not None and prev_slow is not None:
            if prev_fast >= prev_slow:
                return "death_cross"
    
    return None
```

---

### 4.3 触碰信号模式

**适用指标**：BB、VEGAS、Keltner Channel

```python
def check_touch_signal(high, low, close, level, prev_state):
    """
    检测价格触碰某条线
    
    Returns:
        "touch_above": 从上方触碰
        "touch_below": 从下方触碰
        None: 无信号
    """
    # 影线穿过该线
    if low < level < high:
        if close > level:
            return "touch_below"  # 从下方触碰后收在上方
        else:
            return "touch_above"  # 从上方触碰后收在下方
    return None
```

---

### 4.4 背离检测模式（复杂）

**适用指标**：RSI、MACD

```python
def check_divergence(prices, indicator_values, lookback=5):
    """
    检测背离
    
    Returns:
        "bullish_divergence": 底背离（价格新低，指标未新低）
        "bearish_divergence": 顶背离（价格新高，指标未新高）
        None: 无背离
    """
    if len(prices) < lookback or len(indicator_values) < lookback:
        return None
    
    recent_prices = prices[-lookback:]
    recent_indicator = indicator_values[-lookback:]
    
    # 底背离
    if recent_prices[-1] < min(recent_prices[:-1]):
        if recent_indicator[-1] > min(recent_indicator[:-1]):
            return "bullish_divergence"
    
    # 顶背离
    if recent_prices[-1] > max(recent_prices[:-1]):
        if recent_indicator[-1] < max(recent_indicator[:-1]):
            return "bearish_divergence"
    
    return None
```

---

## 五、可添加指标列表

### 5.1 趋势类指标

| 指标 | 参数 | 信号类型 | 复杂度 | 优先级 |
|------|------|----------|--------|--------|
| MA 均线 | 7/25/99 | 金叉/死叉 | ⭐ | 高 |
| EMA 指数均线 | 12/26 | 金叉/死叉 | ⭐ | 高 |
| MACD | 12,26,9 | 金叉/死叉/背离 | ⭐⭐ | 高 |
| SAR 抛物线 | 步长0.02,极限0.2 | 翻转信号 | ⭐⭐ | 中 |
| ADX 趋势强度 | 14 | 趋势强度>25 | ⭐⭐ | 中 |

### 5.2 震荡类指标

| 指标 | 参数 | 信号类型 | 复杂度 | 优先级 |
|------|------|----------|--------|--------|
| RSI 相对强弱 | 6/12/14 | 超买>70/超卖<30 | ⭐ | 高 |
| KDJ 随机指标 | 9,3,3 | 金叉/死叉/超买超卖 | ⭐⭐ | 高 |
| CCI 顺势指标 | 14 | >100/<-100 | ⭐ | 中 |
| Williams %R | 14 | 超买/超卖 | ⭐ | 低 |

### 5.3 成交量类指标

| 指标 | 参数 | 信号类型 | 复杂度 | 优先级 |
|------|------|----------|--------|--------|
| OBV 能量潮 | - | 背离/突破 | ⭐⭐ | 中 |
| Volume MA | 20 | 放量/缩量 | ⭐ | 中 |
| MFI 资金流量 | 14 | >80/<20 | ⭐⭐ | 低 |

### 5.4 波动率类指标

| 指标 | 参数 | 信号类型 | 复杂度 | 优先级 |
|------|------|----------|--------|--------|
| ATR 真实波幅 | 14 | 波动率变化 | ⭐ | 中 |
| Keltner Channel | 20,2 | 突破上轨/下轨 | ⭐⭐ | 中 |
| Donchian Channel | 20 | 突破新高/新低 | ⭐ | 低 |

### 5.5 支撑阻力类

| 指标 | 参数 | 信号类型 | 复杂度 | 优先级 |
|------|------|----------|--------|--------|
| Pivot Point | - | 支撑/阻力位 | ⭐⭐ | 中 |
| Fibonacci 回调 | - | 回调位检测 | ⭐⭐⭐ | 低 |

---

## 六、高级功能建议

### 6.1 参数可配置化

当前参数硬编码，建议改为用户可配置：

```python
# db_manager.py 中存储用户自定义参数
{
    "indicator": "RSI",
    "params": {
        "length": 14,
        "oversold": 30,
        "overbought": 70
    }
}
```

### 6.2 信号组合

允许用户同时监控多个指标：

```python
# 用户可选择：RSI + MACD 同时触发才通知
{
    "strategy": "AND",  # AND 或 OR
    "indicators": ["RSI", "MACD"]
}
```

### 6.3 信号强度分级

```python
# 弱信号：RSI 刚进入超卖区
# 中信号：RSI + 背离
# 强信号：RSI + MACD + 成交量确认
```

### 6.4 历史回测

添加回测功能，让用户测试指标效果：

```python
# 命令：/backtest BTC/USDT RSI 30d
# 返回：过去30天 RSI 信号胜率
```

### 6.5 Pine Script 转换

如果需要导入 TradingView 的 Pine Script 指标：

1. 将 Pine Script 逻辑转换为 Python
2. 在 `market_engine.py` 中添加计算函数
3. 在 `notifier.py` 中添加信号检测
4. 在 `bot.py` 中添加用户选项

**示例转换**：

Pine Script:
```pine
//@version=5
indicator("My RSI", overlay=false)
rsi = ta.rsi(close, 14)
plot(rsi)
```

Python:
```python
def calculate_rsi(series, length=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

---

## 七、推荐开发顺序

| 阶段 | 指标 | 原因 |
|------|------|------|
| 第一阶段 | RSI | 最简单，阈值突破模式 |
| 第二阶段 | MACD | 交叉信号模式 |
| 第三阶段 | MA 金叉死叉 | 交叉信号模式 |
| 第四阶段 | KDJ | 综合信号 |
| 第五阶段 | 背离检测 | 复杂逻辑 |

---

*文档版本：v1.0*  
*最后更新：2026-03-07*