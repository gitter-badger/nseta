from nseta.strategy.strategy import *
from nseta.common.history import *
from nseta.common.log import logdebug, default_logger
from nseta.cli.inputs import *
from nseta.cli.livecli import live_intraday

import click
from datetime import datetime

__all__ = ['test_trading_strategy', 'forecast_strategy']

@logdebug
def smac_strategy(df, autosearch, lower, upper):
	if not autosearch:
		backtest_smac_strategy(df, fast_period=10, slow_period=50)
	else:
		backtest_smac_strategy(df, fast_period=range(10, 30, 3), slow_period=range(40, 60, 3))

@logdebug
def emac_strategy(df, autosearch, lower, upper):
	if not autosearch:
		backtest_smac_strategy(df, fast_period=10, slow_period=50)
	else:
		backtest_smac_strategy(df, fast_period=range(10, 30, 3), slow_period=range(40, 50, 3))

@logdebug
def bbands_strategy(df, autosearch, lower, upper):
	backtest_bbands_strategy(df, period=20, devfactor=2.0)

@logdebug
def rsi_strategy(df, autosearch, lower, upper):
	if not autosearch:
		backtest_rsi_strategy(df, rsi_period=14, rsi_lower=lower, rsi_upper=upper)
	else:
		backtest_rsi_strategy(df, rsi_period=[5,7,11,14], rsi_lower=[15,30,40], rsi_upper=[60,70,80,90] )

@logdebug
def macd_strategy(df, autosearch, lower, upper):
	if not autosearch:
		backtest_macd_strategy(df, fast_period=12, slow_period=26)
	else:
		backtest_macd_strategy(df, fast_period=range(4, 12, 2), slow_period=range(14, 26, 2))

@logdebug
def multi_strategy(df, autosearch, lower, upper):
	if not autosearch:
		backtest_multi_strategy(df, key_variable= "smac", fast_period=10, slow_period=50)
	else:
		# key_variables = ["smac", "emac", "macd"]
		result_smac = backtest_multi_strategy(df, key_variable= "smac", fast_period=10, slow_period=[40,50], rsi_lower=[15,30], rsi_upper=70)
		result_emac = backtest_multi_strategy(df, key_variable= "emac", fast_period=10, slow_period=[40,50], rsi_lower=[15,30], rsi_upper=70)
		result_macd = backtest_multi_strategy(df, key_variable= "macd", fast_period=12, slow_period=[26,40], rsi_lower=[15,30], rsi_upper=70)
		print(result_smac[['smac.fast_period', 'smac.slow_period', 'rsi.rsi_lower', 'rsi.rsi_upper', 'init_cash', 'final_value', 'pnl']].head())
		print ('\n')
		print(result_emac[['emac.fast_period', 'emac.slow_period', 'rsi.rsi_lower', 'rsi.rsi_upper', 'init_cash', 'final_value', 'pnl']].head())
		print('\n')
		print(result_macd[['macd.fast_period', 'macd.slow_period', 'rsi.rsi_lower', 'rsi.rsi_upper', 'init_cash', 'final_value', 'pnl']].head())
		print('\n')

STRATEGY_MAPPING = {
	"rsi": rsi_strategy,
	"smac": smac_strategy,
	# "base": BaseStrategy,
	"macd": macd_strategy,
	"emac": emac_strategy,
	"bbands": bbands_strategy,
	# "buynhold": BuyAndHoldStrategy,
	# "sentiment": SentimentStrategy,
	# "custom": CustomStrategy,
	# "ternary": TernaryStrategy,
	"multi": multi_strategy
}

KEY_MAPPING = {
	'dt': 'Date',
	'open': 'Open',
	'high': 'High',
	'low': 'Low',
	'close': 'Close',
	'volume': 'Volume',
}

STRATEGY_MAPPING_KEYS = list(STRATEGY_MAPPING.keys()) + ['custom']

@click.command(help='Measure the performance of your trading strategy')
@click.option('--symbol', '-S',  help='Security code')
@click.option('--start', '-s', help='Start date in yyyy-mm-dd format')
@click.option('--end', '-e', help='End date in yyyy-mm-dd format')
@click.option('--strategy', default='rsi', type=click.Choice(STRATEGY_MAPPING_KEYS),
	help=', '.join(STRATEGY_MAPPING_KEYS) + ". Choose one.")
@click.option('--upper', '-u', default=1.5, help='Used as upper limit, for example, for RSI. Only when strategy is "custom", we buy the security when the predicted next day return is > +{upper} %')
@click.option('--lower', '-l', default=1.5, help='Used as lower limit, for example, for RSI. Only when strategy is "custom", we sell the security when the predicted next day return is < -{lower} %')
@click.option('--autosearch/--no-autosearch', default=False, 
	help='--auto for allowing to automatically measure the performance of your trading strategy on multiple combinations of parameters.')
@click.option('--intraday', '-i', is_flag=True, help='Get the current intraday price history (Optional)')
@logdebug
def test_trading_strategy(symbol, start, end, autosearch, strategy, upper=1.5, lower=1.5, intraday=False):
	if not intraday:
		if not validate_inputs(start, end, symbol):
			print_help_msg(test_trading_strategy)
			return
		sd = datetime.strptime(start, "%Y-%m-%d").date()
		ed = datetime.strptime(end, "%Y-%m-%d").date()

	try:
		if intraday:
			df = live_intraday(symbol)
			for key in KEY_MAPPING.keys():
				df[key] = df[KEY_MAPPING[key]]
			df.drop(INTRADAY_EQUITY_HEADERS, axis = 1, inplace = True)
		else:
			df = get_history(symbol, sd, ed)
			df['datetime'] = df['Date']
		strategy = strategy.lower()
		if strategy in STRATEGY_MAPPING:
			STRATEGY_MAPPING[strategy](df, autosearch, lower, upper)
		elif strategy == 'custom':
			for key in KEY_MAPPING.keys():
				df[key] = df[KEY_MAPPING[key]]
			df.set_index('dt', inplace=True)
			df.drop(EQUITY_HEADERS, axis = 1, inplace = True)
			backtest_custom_strategy(df, symbol, strategy, upper_limit=upper, lower_limit=lower)
		else:
			STRATEGY_MAPPING['rsi'](df, autosearch, upper, lower)
	except Exception as e:
		default_logger().error(e, exc_info=True)
		click.secho('Failed to test trading strategy. Please check the inputs.', fg='red', nl=True)
		return
	except SystemExit:
		pass

@click.command(help='Forecast & measure performance of a trading model')
@click.option('--symbol', '-S',  help='Security code')
@click.option('--start', '-s', help='Start date in yyyy-mm-dd format')
@click.option('--end', '-e', help='End date in yyyy-mm-dd format')
@click.option('--strategy', default='rsi', type=click.Choice(STRATEGY_MAPPING_KEYS), 
	help=', '.join(STRATEGY_MAPPING_KEYS) + ". Choose one.")
@click.option('--upper', '-u', default=1.5, help='Only when strategy is "custom". We buy the security when the predicted next day return is > +{upper} %')
@click.option('--lower', '-l', default=1.5, help='Only when strategy is "custom". We sell the security when the predicted next day return is < -{lower} %')
@logdebug
def forecast_strategy(symbol, start, end, strategy, upper, lower):
	if not validate_inputs(start, end, symbol):
		print_help_msg(forecast_strategy)
		return
	sd = datetime.strptime(start, "%Y-%m-%d").date()
	ed = datetime.strptime(end, "%Y-%m-%d").date()

	try:
		df = get_history(symbol, sd, ed)
		df['datetime'] = df['Date']
		for key in KEY_MAPPING.keys():
			df[key] = df[KEY_MAPPING[key]]
		df.set_index('dt', inplace=True)
		df.drop(EQUITY_HEADERS, axis = 1, inplace = True)
		plt, result = daily_forecast(df, symbol, strategy, upper_limit=float(upper), lower_limit=float(lower), periods=7)
		if plt is not None:
			plt.show()
	except Exception as e:
		default_logger().error(e, exc_info=True)
		click.secho('Failed to forecast trading strategy. Please check the inputs.', fg='red', nl=True)
		return
	except SystemExit:
		pass
