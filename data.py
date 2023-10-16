from binance import Client
import pandas as pd
from datetime import datetime
from secret import KEY, SECRET


def get_and_preprocess_data(binance_client: Client,
                            start: str,
                            end: str = datetime.today().strftime('%d %b %Y'),
                            symbol: str = 'BTCUSDT',
                            interval: str = Client.KLINE_INTERVAL_1DAY,
                            save: bool = True,
                            dir: str = 'data'):
    # Path to save file
    from pathlib import Path
    dir = Path(dir)
    filename = f'{symbol}_{interval}_data.csv'
    path = dir / filename

    # Binance Key and Secret
    client = binance_client

    # Download data
    data = client.get_historical_klines(symbol=symbol,
                                        interval=interval,
                                        start_str=start,
                                        end_str=end)
    # Convert to DataFrame
    data = pd.DataFrame(data)

    # Rename columns
    data.columns = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume',
                    'Number of Trades', 'TB Base Volume', 'TB Quote Volume', 'Ignore']

    # Pick the columns
    data = data[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

    # Fix datatypes
    data.loc[:, 'Timestamp'] = pd.to_datetime(data['Timestamp']/1000, unit='s')
    data[data.columns[1:]] = data[data.columns[1:]].apply(
        pd.to_numeric, axis='columns')

    # Save to csv
    if save == True:
        data.to_csv(path, index=False)

    return data
