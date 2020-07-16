import os, math
import sys
import pandas as pd
import backtrader as bt
from backtrader.indicators import EMA

class MacdCross(bt.Strategy):
    params = (
        # Standard MACD Parameters
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('pfast', 13),  # period for the fast moving average
        ('pslow', 50),   # period for the slow moving average
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist', 3.0),   # ATR distance for stop price
        ('smaperiod', 30),  # SMA Period (pretty standard)
        ('dirperiod', 10),  # Lookback period to consider SMA trend direction
        ('order_pct', 0.95),
        ('ticker', 'QQQ'),
    )

    def notify_order(self, order):
        if order.status == order.Completed:
            pass

        if not order.alive():
            self.order = None  # indicate no order is pending

    def __init__(self):
        self.macd = bt.indicators.MACD(self.data,
                                       period_me1=self.p.macd1,
                                       period_me2=self.p.macd2,
                                       period_signal=self.p.macdsig)

        # Cross of macd.macd and macd.signal
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        self.cci = bt.indicators.CommodityChannelIndex(self.data,
                                       period=20,
                                       factor=0.015,
                                       upperband=100.0,
                                       lowerband=-100.0)

        # To set the stop price
        self.atr = bt.indicators.ATR(self.data, period=self.p.atrperiod)

        # Control market trend
        sma1 = bt.indicators.SMA(self.data, period=self.p.pfast)
        sma2 = bt.indicators.SMA(self.data, period=self.p.pslow)
        self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        self.smadir = self.sma - self.sma(-self.p.dirperiod)
        # ao = bt.indicators.AwesomeOscillator(self.data)

    def start(self):
        self.order = None  # sentinel to avoid operrations on pending order

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:  # not in the market
            if self.mcross > 0:
                if (((self.macd.signal < 0) and (self.cci[0] > -100.0)) or
                    ((self.macd.signal > 0) and (self.cci[0] > 50.0))): 
                        amount_to_invest = (self.p.order_pct * self.broker.cash)
                        self.size = math.floor(amount_to_invest / self.data.close)
                        print("Buy {} shares of {} at {}".format(self.size, self.p.ticker, self.data.close[0]))
                        self.buy(size=self.size)
                        pdist = self.atr[0] * self.p.atrdist
                        self.pstop = self.data.close[0] - pdist

        else:  # in the market
            if ((self.cci[0] < 100.0) or ((self.mcross < 0 ) and (self.macd.signal > 0))):  # or (self.data.close[0] <= sma2)):
                pclose = self.data.close[0]
                pstop = self.pstop
                    
                if pclose < pstop:
                    self.close()  # stop met - get out
                    print("Sell {} shares of {} at {}".format(self.size, self.p.ticker, self.data.close[0]))

                else:
                    pdist = self.atr[0] * self.p.atrdist
                    # Update only if greater than
                    self.pstop = max(pstop, pclose - pdist)

