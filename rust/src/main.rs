use std::collections::{HashMap, VecDeque};
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::time::Instant;

#[derive(Clone)]
struct Row {
    symbol: String,
    date: String,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    volume: i64,
}

fn pick<'a>(row: &'a HashMap<String, String>, names: &[&str]) -> Option<&'a String> {
    for name in names {
        if let Some(v) = row.get(*name) {
            if !v.is_empty() {
                return Some(v);
            }
        }
    }
    None
}

fn parse_float(value: &str) -> Option<f64> {
    value.replace(',', "").parse::<f64>().ok()
}

fn parse_int(value: &str) -> Option<i64> {
    value.replace(',', "").parse::<f64>().ok().map(|v| v as i64)
}

fn split_csv_line(line: &str) -> Vec<String> {
    let mut fields = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    for c in line.chars() {
        if c == '"' {
            in_quotes = !in_quotes;
        } else if c == ',' && !in_quotes {
            fields.push(current.clone());
            current.clear();
        } else {
            current.push(c);
        }
    }
    fields.push(current);
    fields
}

fn normalize_row(row: &HashMap<String, String>) -> Option<Row> {
    let symbol = pick(row, &["symbol", "ticker", "Symbol", "Ticker", "stock", "Stock"])?;
    let date = pick(row, &["date", "Date"])?;
    let open = parse_float(pick(row, &["open", "Open"])? )?;
    let high = parse_float(pick(row, &["high", "High"])? )?;
    let low = parse_float(pick(row, &["low", "Low"])? )?;
    let close = parse_float(pick(row, &["close", "Close"])? )?;
    let volume = parse_int(pick(row, &["volume", "Volume"])? )?;
    Some(Row { symbol: symbol.clone(), date: date.clone(), open, high, low, close, volume })
}

fn load_rows(path: &str) -> (Vec<Row>, i32) {
    let file = File::open(path).expect("Could not open file");
    let reader = BufReader::new(file);
    let mut lines = reader.lines();
    let header_line = lines.next().unwrap().unwrap();
    let headers = split_csv_line(&header_line);
    let mut rows = Vec::new();
    let mut invalid = 0;

    for line in lines {
        let line = line.unwrap();
        let values = split_csv_line(&line);
        let mut map = HashMap::new();
        for (h, v) in headers.iter().zip(values.iter()) {
            map.insert(h.clone(), v.clone());
        }
        if let Some(row) = normalize_row(&map) {
            rows.push(row);
        } else {
            invalid += 1;
        }
    }
    (rows, invalid)
}

fn moving_average(values: &[f64], window: usize) -> Vec<f64> {
    let mut q: VecDeque<f64> = VecDeque::new();
    let mut total = 0.0;
    let mut out = Vec::new();
    for v in values {
        q.push_back(*v);
        total += *v;
        if q.len() > window {
            total -= q.pop_front().unwrap();
        }
        out.push(total / q.len() as f64);
    }
    out
}

fn task_summary(rows: &[Row]) -> usize {
    let mut grouped: HashMap<String, Vec<&Row>> = HashMap::new();
    for row in rows {
        grouped.entry(row.symbol.clone()).or_default().push(row);
    }
    grouped.len()
}

fn task_analytics(rows: &[Row]) -> usize {
    let mut grouped: HashMap<String, Vec<&Row>> = HashMap::new();
    for row in rows {
        grouped.entry(row.symbol.clone()).or_default().push(row);
    }
    let mut result_count = 0;
    for items in grouped.values_mut() {
        items.sort_by(|a, b| a.date.cmp(&b.date));
        let closes: Vec<f64> = items.iter().map(|r| r.close).collect();
        let ma7 = moving_average(&closes, 7);
        let ma30 = moving_average(&closes, 30);
        let mut prev_close: Option<f64> = None;
        for i in 0..items.len() {
            let _daily_return = match prev_close {
                Some(pc) if pc != 0.0 => (items[i].close - pc) / pc,
                _ => f64::NAN,
            };
            prev_close = Some(items[i].close);
            let _ = ma7[i] + ma30[i];
            result_count += 1;
        }
    }
    result_count
}

fn task_top_movers(rows: &[Row]) -> usize {
    let mut grouped: HashMap<String, Vec<&Row>> = HashMap::new();
    for row in rows {
        grouped.entry(row.symbol.clone()).or_default().push(row);
    }
    let mut gains = Vec::new();
    for items in grouped.values_mut() {
        items.sort_by(|a, b| a.date.cmp(&b.date));
        let mut largest_gain: Option<f64> = None;
        let mut _largest_loss: Option<f64> = None;
        let mut _total_volume: i64 = 0;
        for i in 0..items.len() {
            _total_volume += items[i].volume;
            if i == 0 || items[i - 1].close == 0.0 { continue; }
            let change = (items[i].close - items[i - 1].close) / items[i - 1].close;
            largest_gain = Some(match largest_gain { Some(g) => g.max(change), None => change });
            _largest_loss = Some(match _largest_loss { Some(l) => l.min(change), None => change });
        }
        gains.push(largest_gain.unwrap_or(-999.0));
    }
    gains.sort_by(|a, b| b.partial_cmp(a).unwrap());
    gains.len().min(20)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut input = String::new();
    let mut task = String::new();
    let mut i = 0;
    while i + 1 < args.len() {
        if args[i] == "--input" { input = args[i + 1].clone(); }
        if args[i] == "--task" { task = args[i + 1].clone(); }
        i += 1;
    }

    let start = Instant::now();
    let (rows, invalid) = load_rows(&input);
    let preview_count = match task.as_str() {
        "parse_only" => 1,
        "summary" => task_summary(&rows),
        "analytics" => task_analytics(&rows),
        "top_movers" => task_top_movers(&rows),
        _ => 0,
    };
    let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
    println!("{{\"language\":\"Rust\",\"task\":\"{}\",\"elapsed_ms\":{:.3},\"rows_processed\":{},\"invalid_rows\":{},\"preview_count\":{}}}",
             task, elapsed_ms, rows.len(), invalid, preview_count);
}