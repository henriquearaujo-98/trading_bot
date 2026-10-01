import pandas as pd
from models.trade_decision import TradeDecision

from technicals.indicators import MACD
from bot.trade_manager import trade_is_open

pd.set_option('display.max_columns', None)
pd.set_option('expand_frame_repr', False)


from api.oanda_api import OandaApi
from models.trade_settings import TradeSettings
import constants.defs as defs

ADDROWS = 201
CROSS_UP = 1
CROSS_DOWN = -1
ALPHA_H = 0.0001
ALPHA_L = 0.00015
SL = 0.02
TP = 0.05
LEVERAGE = 30

def apply_signal(row, trade_settings: TradeSettings):

    if row.SPREAD <= trade_settings.maxspread and row.GAIN >= trade_settings.mingain:
        if row['CROSS'] == CROSS_UP and row['SMA200'] < row['mid_c'] and row['MACD'] < ALPHA_L:
            return defs.BUY
        elif row['CROSS'] == CROSS_DOWN and row['SMA200'] > row['mid_c'] and row['MACD'] > ALPHA_H:
            return defs.SELL
    return defs.NONE

def apply_SL(row, trade_settings: TradeSettings):
    if row.SIGNAL == defs.BUY:
        return row.mid_c * (1 - SL / LEVERAGE)
    elif row.SIGNAL == defs.SELL:
        return row.mid_c * (1 + SL / LEVERAGE)
    return 0.0


def apply_TP(row):
    
    if row.SIGNAL == defs.BUY:
        return row.mid_c * (1 + TP / LEVERAGE)
    elif row.SIGNAL == defs.SELL:
        return row.mid_c * (1 - TP / LEVERAGE)
    return 0.0


def process_candles(df: pd.DataFrame, pair, trade_settings: TradeSettings, api:OandaApi, log_message):

    df.reset_index(drop=True, inplace=True)
    df['DECISION'] = defs.NONE
    df['PAIR'] = pair
    df['SPREAD'] = df.ask_c - df.bid_c

    df = MACD(df)
    df['MACD_DIFF'] = df['MACD'] - df['SIGNAL']
    df['CROSS'] = 0

    # Detect crosses
    df.loc[(df['MACD_DIFF'].shift(-1) < 0) & (df['MACD_DIFF'] > 0), 'CROSS'] = CROSS_DOWN
    df.loc[(df['MACD_DIFF'].shift(-1) > 0) & (df['MACD_DIFF'] < 0), 'CROSS'] = CROSS_UP
    df = df.drop(columns=['MACD_DIFF'])

    # Hist diff
    df['PREV_HIST'] = df['HIST'].shift(-1)
    df['HIST_DIFF'] = df['HIST'] - df['PREV_HIST']
    df = df.drop(columns=['PREV_HIST'])

    df['SMA200'] = df['mid_c'].ewm(span=200, adjust=False).mean()
    df.dropna(inplace=True)

    df['GAIN'] = abs(df.mid_c * (1 + TP))
    df['SIGNAL'] = df.apply(apply_signal, axis=1, trade_settings=trade_settings)
    df['TP'] = df.apply(apply_TP, axis=1)
    df['SL'] = df.apply(apply_SL, axis=1, trade_settings=trade_settings)
    df['LOSS'] = abs(df.mid_c - df.SL)
    

    log_cols = ['PAIR', 'time', 'mid_c', 'mid_o', 'SL', 'TP', 'SPREAD', 'GAIN', 'LOSS', 'SIGNAL', 'DECISION', 'HIST_DIFF', 'MACD_DIFF']
    

    last_row = df[log_cols].iloc[-1]

    # if we have an open trade on this pair, check if we should close is or not
    if trade_is_open(pair, api):

        pos_type = df[df['SIGNAL'] != 0].iloc[-1].SIGNAL

        if pos_type == defs.BUY and last_row.HIST_DIFF > 0:
            last_row.DECISION = defs.CLOSE

        if pos_type == defs.SELL and last_row.HIST_DIFF < 0:
            last_row.DECISION = defs.CLOSE

    log_message(f"process_candles:\n{df[log_cols].tail()}", pair)

    return last_row


def fetch_candles(pair, row_count, candle_time, granularity,
                    api: OandaApi, log_message):

    df = api.get_candles_df(pair, count=row_count, granularity=granularity)

    if df is None or df.shape[0] == 0:
        log_message("tech_manager fetch_candles failed to get candles", pair)
        return None
    
    if df.iloc[-1].time != candle_time:
        log_message(f"tech_manager fetch_candles {df.iloc[-1].time} not correct", pair)
        return None

    return df

def get_trade_decision(candle_time, pair, granularity, api: OandaApi, 
                            trade_settings: TradeSettings, log_message):


    max_rows = trade_settings.n_ma + ADDROWS

    log_message(f"tech_manager: max_rows:{max_rows} candle_time:{candle_time} granularity:{granularity}", pair)

    df = fetch_candles(pair, max_rows, candle_time,  granularity, api, log_message)

    if df is not None:
        last_row = process_candles(df, pair, trade_settings, api, log_message)

        return TradeDecision(last_row)

    return None


