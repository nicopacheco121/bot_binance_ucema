"""
En este archivo estara lo relacionado a la api de okx.
Utilizaremos la libreria python-okx para interactuar con la api de okx.

Como obtener los datos para interactuar con la api de okx:
Registro en okx: (si usan este link acceden a un 20% de cashback en las operaciones)
Login OKX —> Trade —> Demo Trading —> Personal Center —> Demo Trading API -> Create Demo Trading V5 API Key —> Start your Demo Trading

Link de la libreria
https://github.com/okxapi/python-okx

Lo que haremos con la api es:
- Obtener balance
- Obtener posiciones abiertas
- Descargar precios
- Setear leverage
- Consultar contratos
- Abrir una posicion == Enviar una orden market
- Consultar una orden
- Cerrar una posicion (enviar client_order_id)

"""
import pandas as pd
import pprint  # import print para poder imprimir los json de manera mas ordenada

# Usaremos la libreria okx para interactuar con la api de okx
from okx.Account import AccountAPI
import okx.MarketData as MarketData
from okx.Trade import TradeAPI

from keys import API_KEY, API_SECRET, PASSPHRASE


# Funciones para obtener ciertos objetos necesarios para interactuar con la api de okx
def get_account_api(api_key, api_secret, passphrase, flag='1'):
    # flag = "1"  # live trading: 0, demo trading: 1
    return AccountAPI(api_key, api_secret, passphrase, flag=flag, debug=False)


def get_account_md_api(flag='1'):
    return MarketData.MarketAPI(flag=flag, debug=False)


def get_account_trade_api(api_key, api_secret, passphrase, flag='1'):
    return TradeAPI(api_key, api_secret, passphrase, flag=flag, debug=False)


# Funciones para interactuar con la api de okx
def get_instruments(account_api, instType='SWAP'):
    """
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-instruments

    Esto lo vamos a utilizar para calcular el size a enviar en las ordenes, ya que el el size en este caso no es una
    cantidad de usdt, sino una cantidad de contratos.

    Lo que tendremos en cuenta es
    - ctVal: Contract value, es el valor de un contrato en usd. Por ejemplo, en BTC-USDT-SWAP es 0.001
    - minSz: Minimum size, es el minimo size que se puede enviar en una orden. Por ejemplo, en BTC-USDT-SWAP es 0.1
    - tickSz: Tick size, es el incremento minimo que se puede enviar en una orden. Por ejemplo, en BTC-USDT-SWAP es 0.1

    Valor del contrato = ctVal * precio del activo
    Cantidad de contratos = Margen * Leverage / Valor del contrato
    Luego ajustamos el size por el tick size

    Entonces, si queremos enviar una orden de 100 usdt de margen con leverage 1 en BTC-USDT-SWAP, a un precio del
    activo de 60.000 USDT, debemos calcular el size de la siguiente manera:

    Valor del contrato = 0.001 * 60.000 = 60 USDT
    Size = 100 * 1 / 60 = 1.6666666666666667
    Size ajustado por el tick size = 1.6

    https://www.okx.com/es-es/trade-market/info/swap

    """

    instruments = account_api.get_instruments(instType=instType)
    data = instruments.get('data', [])
    return data


def get_data_instruments(account_api, tickers, instType='SWAP'):
    """
    Obtengo los datos de los instrumentos que me interesan
    :param tickers: list
    :return:
    """

    instruments = get_instruments(account_api=account_api, instType=instType)

    data = {}
    for i in instruments:
        if i['instId'] in tickers:
            data[i['instId']] = {}
            data[i['instId']]['ctVal'] = i['ctVal']
            data[i['instId']]['minSz'] = i['minSz']
            data[i['instId']]['tickSz'] = i['tickSz']

    # podriamos tambien entregar el max leverage, etc...

    return data


def set_leverage(account_trade_api, instId, lever):
    """
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-set-leverage
    """
    long = account_trade_api.set_leverage(instId=instId, lever=lever, mgnMode='isolated', posSide='long')
    short = account_trade_api.set_leverage(instId=instId, lever=lever, mgnMode='isolated', posSide='short')

    if long['code'] == '0' and short['code'] == '0':
        return True

    return False


def get_balance(account_api):
    """
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance
    """
    result = account_api.get_account_balance()

    balance = {}
    for i in result['data'][0]['details']:
        coin = i['ccy']
        monto = i['availBal']

        balance[coin] = monto

    return balance


def get_usdt_balance(account_api):
    balance = get_balance(account_api)
    usdt = balance.get('USDT', 0)

    return usdt


def get_positions(account_api, instType='SWAP'):
    """
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions
    """
    positions = account_api.get_positions(instType=instType)
    data = positions.get('data', [])
    return data


def get_positions_dict(account_api, instType='SWAP'):
    """
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions
    """
    data = get_positions(account_api=account_api, instType=instType)

    positions_dict = {}
    for i in data:
        instId = i['instId']
        posSide = i['posSide']
        avgPx = i['avgPx']
        markPx = i['markPx']
        fee = i['fee']
        lever = i['lever']
        margin = i['margin']
        notionalUsd = i['notionalUsd']

        positions_dict[instId] = {
            'posSide': posSide,
            'avgPx': avgPx,
            'markPx': markPx,
            'fee': fee,
            'lever': lever,
            'margin': margin,
            'notionalUsd': notionalUsd
        }

    return positions_dict


def get_historical_prices(client_md, instId, bar='1m', limit=300):
    """
    https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks
    """
    data = client_md.get_candlesticks(instId, bar=bar, limit=limit)
    data = data.get('data', [])
    df = pd.DataFrame(data)

    return df


def get_historical_data_formatted(client_md, instId, bar='1m', limit=300):
    """
    https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks
    """
    columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm']

    df = get_historical_prices(client_md, instId, bar=bar, limit=limit)

    df = df.astype(float)  # convierto a float

    df.columns = columns  # renombro las columnas

    df['time'] = pd.to_datetime(df['time'], unit='ms')  # convierto el tiempo a datetime
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)  # ordeno el index por fecha

    # elimino la vela no confirmada, es decir, la que es 0
    df = df[df['confirm'] == 1]

    return df


# VOY POR ACA
def send_market_order(account_trade_api, instId, tdMode, ccy, clOrdId, side, posSide, ordType, sz):
    """
    https://www.okx.com/docs-v5/en/#trading-trade-api-place-order
    """
    order = account_trade_api.place_order(instId=instId,
                                          tdMode=tdMode,
                                          ccy=ccy,
                                          clOrdId=clOrdId,
                                          side=side,
                                          posSide=posSide,
                                          ordType=ordType,
                                          sz=sz)

    return order


if __name__ == '__main__':

    account_api = get_account_api(API_KEY, API_SECRET, PASSPHRASE)  # Ir a los metodos de account api para mostrar
    account_trade_api = get_account_trade_api(API_KEY, API_SECRET, PASSPHRASE)
    client_md = get_account_md_api()

    """ BALANCE """
    account_api.get_account_balance()
    balance = get_balance(account_api)
    print(balance)

    usdt = get_usdt_balance(account_api)
    print(usdt)

    """ POSICIONES ABIERTAS """
    instType = 'SWAP'  # SWAP es para futuros perpetuos, tambien puede ser SPOT, etc
    # previo abrir una posicion para ver algo
    posiciones = get_positions(account_api=account_api, instType=instType)
    print(posiciones)

    # Ver detalle en ejemplo_order.py

    dict_positions = get_positions_dict(account_api=account_api, instType=instType)
    pprint.pprint(dict_positions)

    """ DATA DE INSTRUMENTOS Y LEVERAGE """
    # Instruments
    tickers = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']
    instruments = get_data_instruments(account_api, tickers)
    print(instruments)

    # Setear leverage
    instId = 'BTC-USDT-SWAP'
    lever = 5
    print(set_leverage(account_api, instId, lever))

    """ PRECIOS """
    instId = "BTC-USDT-SWAP"

    # Traigo los precios de BTC-USDT-SWAP
    data = client_md.get_candlesticks('BTC-USDT-SWAP', bar='1m', limit=300)
    data = data.get('data', [])
    df = pd.DataFrame(data)
    print(df)

    # Ahora usando las funciones que formatean los datos
    df = get_historical_data_formatted(client_md, instId, bar='1m', limit=300)

    print(df)
    print(df.columns)

    """ ORDENES """
    # # Creo una orden
    order = account_trade_api.place_order(instId='BTC-USDT-SWAP',
                                          tdMode='isolated',  # cross es para margen cruzado, isolated es para margen aislado
                                          ccy='USDT',  # moneda de la orden
                                          clOrdId='test',  # id de la orden
                                          side='buy',  # buy o sell
                                          posSide='long',  # long o short
                                          ordType='market',
                                          sz='1')

    print(order)
    # la diferencia entre cross e isolated es que en cross se usa el total del balance para la operacion, en isolated se usa un margen aislado

    order_id = order['data'][0]['ordId']

    # Consultar una orden
    order = account_trade_api.get_order(instId='BTC-USDT-SWAP', ordId=order_id)
    pprint.pprint(order)
    # Ver detalle en ejemplo_order.py

    # Cerrar una posicion
    order = account_trade_api.close_positions(instId='BTC-USDT-SWAP',
                                              mgnMode='isolated',
                                              posSide='long',
                                              ccy='USDT',
                                              autoCxl='true',
                                              clOrdId='test123')
    # en este caso me conviene enviar el clOrdId para luego poder consultar la orden, ya que el cierre de posicion
    # no me devuelve un order id
    print(order)

    # Consulto posicion cerrada
    client_order_id = 'test123'
    order = account_trade_api.get_order(instId='BTC-USDT-SWAP', clOrdId=client_order_id)
    pprint.pprint(order)

    # Ver detalle en ejemplo_order.py
