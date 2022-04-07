from decimal import Decimal
from datetime import datetime

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum.logging import get_logger
from electrum.exchange_rate import FxThread
from electrum.simple_config import SimpleConfig
from electrum.util import register_callback
from electrum.bitcoin import COIN

class QEFX(QObject):
    def __init__(self, fxthread: FxThread, config: SimpleConfig, parent=None):
        super().__init__(parent)
        self.fx = fxthread
        self.config = config
        register_callback(self.on_quotes, ['on_quotes'])
        register_callback(self.on_history, ['on_history'])

    _logger = get_logger(__name__)

    quotesUpdated = pyqtSignal()
    def on_quotes(self, event, *args):
        self._logger.debug('new quotes')
        self.quotesUpdated.emit()

    historyUpdated = pyqtSignal()
    def on_history(self, event, *args):
        self._logger.debug('new history')
        self.historyUpdated.emit()

    currenciesChanged = pyqtSignal()
    @pyqtProperty('QVariantList', notify=currenciesChanged)
    def currencies(self):
        return self.fx.get_currencies(self.historicRates)

    rateSourcesChanged = pyqtSignal()
    @pyqtProperty('QVariantList', notify=rateSourcesChanged)
    def rateSources(self):
        return self.fx.get_exchanges_by_ccy(self.fiatCurrency, self.historicRates)

    fiatCurrencyChanged = pyqtSignal()
    @pyqtProperty(str, notify=fiatCurrencyChanged)
    def fiatCurrency(self):
        return self.fx.get_currency()

    @fiatCurrency.setter
    def fiatCurrency(self, currency):
        if currency != self.fiatCurrency:
            self.fx.set_currency(currency)
            self.enabled = self.enabled and currency != ''
            self.fiatCurrencyChanged.emit()
            self.rateSourcesChanged.emit()

    historicRatesChanged = pyqtSignal()
    @pyqtProperty(bool, notify=historicRatesChanged)
    def historicRates(self):
        return self.fx.get_history_config()

    @historicRates.setter
    def historicRates(self, checked):
        if checked != self.historicRates:
            self.fx.set_history_config(checked)
            self.historicRatesChanged.emit()
            self.rateSourcesChanged.emit()

    rateSourceChanged = pyqtSignal()
    @pyqtProperty(str, notify=rateSourceChanged)
    def rateSource(self):
        return self.fx.config_exchange()

    @rateSource.setter
    def rateSource(self, source):
        if source != self.rateSource:
            self.fx.set_exchange(source)
            self.rateSourceChanged.emit()

    enabledUpdated = pyqtSignal() # curiously, enabledChanged is clashing, so name it enabledUpdated
    @pyqtProperty(bool, notify=enabledUpdated)
    def enabled(self):
        return self.fx.is_enabled()

    @enabled.setter
    def enabled(self, enable):
        if enable != self.enabled:
            self.fx.set_enabled(enable)
            self.enabledUpdated.emit()

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, bool, result=str)
    def fiatValue(self, satoshis, plain=True):
        rate = self.fx.exchange_rate()
        try:
            sd = Decimal(satoshis)
            if sd == 0:
                return ''
        except:
            return ''
        if plain:
            return self.fx.ccy_amount_str(self.fx.fiat_value(satoshis, rate), False)
        else:
            return self.fx.value_str(satoshis, rate)

    @pyqtSlot(str, str, result=str)
    def fiatValueHistoric(self, satoshis, timestamp, plain=True):
        try:
            sd = Decimal(satoshis)
            if sd == 0:
                return ''
            td = Decimal(timestamp)
            if td == 0:
                return ''
        except:
            return ''
        dt = datetime.fromtimestamp(td)
        if plain:
            return self.fx.ccy_amount_str(self.fx.historical_value(satoshis, dt), False)
        else:
            return self.fx.historical_value_str(satoshis, dt)

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, bool, result=str)
    def satoshiValue(self, fiat, plain=True):
        rate = self.fx.exchange_rate()
        try:
            fd = Decimal(fiat)
        except:
            return ''
        v = fd / Decimal(rate) * COIN
        if v.is_nan():
            return ''
        if plain:
            return str(v.to_integral_value())
        else:
            return self.config.format_amount(v)
