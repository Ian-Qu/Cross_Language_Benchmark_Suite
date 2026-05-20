package com.ianquaye.benchmark;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class Main {
    static class Row {
        String symbol;
        String date;
        double open;
        double high;
        double low;
        double close;
        long volume;

        Row(String symbol, String date, double open, double high, double low, double close, long volume) {
            this.symbol = symbol;
            this.date = date;
            this.open = open;
            this.high = high;
            this.low = low;
            this.close = close;
            this.volume = volume;
        }
    }

    static class LoadResult {
        List<Row> rows;
        int invalid;
        LoadResult(List<Row> rows, int invalid) { this.rows = rows; this.invalid = invalid; }
    }

    static String pick(Map<String, String> row, String... names) {
        for (String name : names) {
            if (row.containsKey(name)) {
                String value = row.get(name);
                if (value != null && !value.isEmpty()) return value;
            }
        }
        return null;
    }

    static Double parseFloat(String value) {
        try {
            return Double.parseDouble(value.replace(",", ""));
        } catch (Exception e) {
            return null;
        }
    }

    static Long parseInt(String value) {
        try {
            return (long) Double.parseDouble(value.replace(",", ""));
        } catch (Exception e) {
            return null;
        }
    }

    static Row normalizeRow(Map<String, String> row) {
        String symbol = pick(row, "symbol", "ticker", "Symbol", "Ticker", "stock", "Stock");
        String date = pick(row, "date", "Date");
        Double open = parseFloat(pick(row, "open", "Open"));
        Double high = parseFloat(pick(row, "high", "High"));
        Double low = parseFloat(pick(row, "low", "Low"));
        Double close = parseFloat(pick(row, "close", "Close"));
        Long volume = parseInt(pick(row, "volume", "Volume"));
        if (symbol == null || date == null || open == null || high == null || low == null || close == null || volume == null) return null;
        return new Row(symbol, date, open, high, low, close, volume);
    }

    static List<String> parseCsvLine(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder sb = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                inQuotes = !inQuotes;
            } else if (c == ',' && !inQuotes) {
                out.add(sb.toString());
                sb.setLength(0);
            } else {
                sb.append(c);
            }
        }
        out.add(sb.toString());
        return out;
    }

    static LoadResult loadRows(String path) throws IOException {
        List<Row> valid = new ArrayList<>();
        int invalid = 0;
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String headerLine = br.readLine();
            if (headerLine == null) return new LoadResult(valid, invalid);
            List<String> headers = parseCsvLine(headerLine);
            String line;
            while ((line = br.readLine()) != null) {
                List<String> values = parseCsvLine(line);
                Map<String, String> row = new HashMap<>();
                int limit = Math.min(headers.size(), values.size());
                for (int i = 0; i < limit; i++) row.put(headers.get(i), values.get(i));
                Row normalized = normalizeRow(row);
                if (normalized == null) invalid++;
                else valid.add(normalized);
            }
        }
        return new LoadResult(valid, invalid);
    }

    static List<Double> movingAverage(List<Double> values, int window) {
        Deque<Double> q = new ArrayDeque<>();
        List<Double> out = new ArrayList<>();
        double total = 0.0;
        for (double v : values) {
            q.addLast(v);
            total += v;
            if (q.size() > window) total -= q.removeFirst();
            out.add(total / q.size());
        }
        return out;
    }

    static int taskSummary(List<Row> rows) {
        Map<String, List<Row>> grouped = new HashMap<>();
        for (Row row : rows) grouped.computeIfAbsent(row.symbol, k -> new ArrayList<>()).add(row);
        return grouped.size();
    }

    static int taskAnalytics(List<Row> rows) {
        Map<String, List<Row>> grouped = new HashMap<>();
        for (Row row : rows) grouped.computeIfAbsent(row.symbol, k -> new ArrayList<>()).add(row);
        int count = 0;
        for (List<Row> items : grouped.values()) {
            items.sort(Comparator.comparing(r -> r.date));
            List<Double> closes = new ArrayList<>();
            for (Row r : items) closes.add(r.close);
            List<Double> ma7 = movingAverage(closes, 7);
            List<Double> ma30 = movingAverage(closes, 30);
            double prevClose = 0.0;
            boolean hasPrev = false;
            for (int i = 0; i < items.size(); i++) {
                double dailyReturn = (!hasPrev || prevClose == 0.0) ? Double.NaN : (items.get(i).close - prevClose) / prevClose;
                prevClose = items.get(i).close;
                hasPrev = true;
                double ignore = dailyReturn + ma7.get(i) + ma30.get(i);
                if (Double.isNaN(ignore) || ignore > -1e18) count++;
            }
        }
        return count;
    }

    static int taskTopMovers(List<Row> rows) {
        Map<String, List<Row>> grouped = new HashMap<>();
        for (Row row : rows) grouped.computeIfAbsent(row.symbol, k -> new ArrayList<>()).add(row);
        List<Double> gains = new ArrayList<>();
        for (List<Row> items : grouped.values()) {
            items.sort(Comparator.comparing(r -> r.date));
            Double largestGain = null;
            Double largestLoss = null;
            for (int i = 0; i < items.size(); i++) {
                Row row = items.get(i);
                if (i == 0 || items.get(i - 1).close == 0.0) continue;
                double change = (row.close - items.get(i - 1).close) / items.get(i - 1).close;
                largestGain = largestGain == null ? change : Math.max(largestGain, change);
                largestLoss = largestLoss == null ? change : Math.min(largestLoss, change);
            }
            gains.add(largestGain == null ? -999.0 : largestGain);
        }
        gains.sort(Collections.reverseOrder());
        return Math.min(20, gains.size());
    }

    public static void main(String[] args) throws Exception {
        String input = null;
        String task = null;
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals("--input")) input = args[i + 1];
            if (args[i].equals("--task")) task = args[i + 1];
        }
        long start = System.nanoTime();
        LoadResult loaded = loadRows(input);
        int previewCount;
        switch (task) {
            case "parse_only": previewCount = 1; break;
            case "summary": previewCount = taskSummary(loaded.rows); break;
            case "analytics": previewCount = taskAnalytics(loaded.rows); break;
            case "top_movers": previewCount = taskTopMovers(loaded.rows); break;
            default: throw new IllegalArgumentException("Unknown task: " + task);
        }
        double elapsedMs = (System.nanoTime() - start) / 1_000_000.0;
        System.out.printf(Locale.US, "{\"language\":\"Java\",\"task\":\"%s\",\"elapsed_ms\":%.3f,\"rows_processed\":%d,\"invalid_rows\":%d,\"preview_count\":%d}%n",
                task, elapsedMs, loaded.rows.size(), loaded.invalid, previewCount);
    }
}