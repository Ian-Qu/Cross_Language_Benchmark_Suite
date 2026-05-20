import argparse
import csv
import json
import time
from collections import defaultdict, deque
from statistics import mean
from pathlib import Path


def parse_float(value):
    try:
        return float(str(value).replace(',', ''))
    except Exception:
        return None


def parse_int(value):
    try:
        return int(float(str(value).replace(',', '')))
    except Exception:
        return None


def pick(row, *names):
    for name in names:
        if name in row and row[name] not in (None, ''):
            return row[name]
    return None


def normalize_row(row):
    symbol = pick(row, 'symbol', 'ticker', 'Symbol', 'Ticker', 'stock', 'Stock')
    date = pick(row, 'date', 'Date')
    open_ = parse_float(pick(row, 'open', 'Open'))
    high = parse_float(pick(row, 'high', 'High'))
    low = parse_float(pick(row, 'low', 'Low'))
    close = parse_float(pick(row, 'close', 'Close'))
    volume = parse_int(pick(row, 'volume', 'Volume'))
    if not all([symbol, date]) or None in (open_, high, low, close, volume):
        return None
    return {'symbol': symbol, 'date': date, 'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume}


def load_rows(path):
    valid, invalid = [], 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = normalize_row(row)
            if normalized is None:
                invalid += 1
            else:
                valid.append(normalized)
    return valid, invalid


def task_parse_only(rows, invalid):
    return {'valid_rows': len(rows), 'invalid_rows': invalid}


def task_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['symbol']].append(row)
    result = []
    for symbol, items in grouped.items():
        closes = [r['close'] for r in items]
        result.append({'symbol': symbol, 'row_count': len(items), 'avg_close': mean(closes), 'min_close': min(closes), 'max_close': max(closes), 'total_volume': sum(r['volume'] for r in items)})
    return result


def moving_average(values, window):
    q = deque()
    total = 0.0
    out = []
    for v in values:
        q.append(v)
        total += v
        if len(q) > window:
            total -= q.popleft()
        out.append(total / len(q))
    return out


def task_analytics(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['symbol']].append(row)
    result = []
    for symbol, items in grouped.items():
        items.sort(key=lambda r: r['date'])
        closes = [r['close'] for r in items]
        ma7 = moving_average(closes, 7)
        ma30 = moving_average(closes, 30)
        prev_close = None
        for i, row in enumerate(items):
            daily_return = None if prev_close in (None, 0) else (row['close'] - prev_close) / prev_close
            prev_close = row['close']
            result.append({'symbol': symbol, 'date': row['date'], 'close': row['close'], 'daily_return': daily_return, 'ma7': ma7[i], 'ma30': ma30[i]})
    return result


def task_top_movers(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['symbol']].append(row)
    movers = []
    for symbol, items in grouped.items():
        items.sort(key=lambda r: r['date'])
        largest_gain = None
        largest_loss = None
        total_volume = 0
        for i, row in enumerate(items):
            total_volume += row['volume']
            if i == 0 or items[i - 1]['close'] == 0:
                continue
            change = (row['close'] - items[i - 1]['close']) / items[i - 1]['close']
            largest_gain = change if largest_gain is None else max(largest_gain, change)
            largest_loss = change if largest_loss is None else min(largest_loss, change)
        movers.append({'symbol': symbol, 'largest_gain': largest_gain, 'largest_loss': largest_loss, 'avg_volume': total_volume / len(items)})
    movers.sort(key=lambda x: (x['largest_gain'] if x['largest_gain'] is not None else -999), reverse=True)
    return movers[:20]


def run_task(rows, invalid, task):
    if task == 'parse_only':
        return task_parse_only(rows, invalid)
    if task == 'summary':
        return task_summary(rows)
    if task == 'analytics':
        return task_analytics(rows)
    if task == 'top_movers':
        return task_top_movers(rows)
    raise ValueError(f'Unknown task: {task}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--task', required=True, choices=['parse_only', 'summary', 'analytics', 'top_movers'])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    start = time.perf_counter()
    rows, invalid = load_rows(args.input)
    output = run_task(rows, invalid, args.task)
    elapsed_ms = (time.perf_counter() - start) * 1000
    result = {'language': 'Python', 'task': args.task, 'elapsed_ms': round(elapsed_ms, 3), 'rows_processed': len(rows), 'invalid_rows': invalid, 'preview_count': len(output) if isinstance(output, list) else 1}
    if args.json:
        print(json.dumps(result))
    else:
        print(result)


if __name__ == '__main__':
    main()
