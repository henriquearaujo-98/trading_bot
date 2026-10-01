
from api.oanda_api import OandaApi
from bot.trade_risk_calculator import get_trade_units
from models.trade_decision import TradeDecision
import constants.defs as defs

def trade_is_open(pair, api: OandaApi):

    open_trades = api.get_open_trades()

    # Don't allow multiple positions on the same pair
    for ot in open_trades:
        if ot.instrument == pair:
            return ot.id

    return None

def close_trade(trade_decision: TradeDecision, api:OandaApi):
    open_trade_id = trade_is_open(trade_decision.pair, api)

    if open_trade_id is not None:

        log_message(f"Found open trade for {trade_decision.pair} with trade id {open_trade_id}. Decision: {trade_decision.decision}")

        if trade_decision.decision == defs.CLOSE:
            log_message(f"Trying to close {trade_decision.pair}")
            api.close_trade(open_trade_id)
            log_message(f"Closed trade {trade_decision}", trade_decision.pair)
            return None

        log_message(f"Failed to close trade {trade_decision}: {open_trade_id}", trade_decision.pair)
        return None


def place_trade(trade_decision: TradeDecision, api: OandaApi, log_message, log_error, trade_risk):

    open_trade_id = trade_is_open(trade_decision.pair, api)

    if open_trade_id is not None:
        log_message(f"Failed to place trade {trade_decision}, already open: {open_trade_id}", trade_decision.pair)
        return None

    trade_units = get_trade_units(api, trade_decision.pair, trade_decision.signal, 
                            trade_decision.loss, trade_risk, log_message)

    trade_id = api.place_trade(
        trade_decision.pair, 
        trade_units,
        trade_decision.signal,
        trade_decision.sl,
        trade_decision.tp
    )

    if trade_id is None:
        log_error(f"ERROR placing {trade_decision}")
        log_message(f"ERROR placing {trade_decision}", trade_decision.pair)
    else:
        log_message(f"placed trade_id:{trade_id} for {trade_decision}", trade_decision.pair)


