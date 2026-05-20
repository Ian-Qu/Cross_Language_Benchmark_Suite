#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_LINE 8192
#define MAX_FIELD 256

typedef struct {
    char symbol[MAX_FIELD];
    char date[MAX_FIELD];
    double open;
    double high;
    double low;
    double close;
    long volume;
} Row;

typedef struct {
    Row *data;
    size_t size;
    size_t capacity;
    int invalid;
} RowArray;

double now_ms() {
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1000000.0;
}

void push_row(RowArray *arr, Row row) {
    if (arr->size == arr->capacity) {
        arr->capacity = arr->capacity == 0 ? 1024 : arr->capacity * 2;
        arr->data = realloc(arr->data, arr->capacity * sizeof(Row));
    }
    arr->data[arr->size++] = row;
}

int split_csv(char *line, char **fields, int max_fields) {
    int count = 0;
    int in_quotes = 0;
    char *start = line;
    for (char *p = line; *p; p++) {
        if (*p == '"') in_quotes = !in_quotes;
        else if (*p == ',' && !in_quotes) {
            *p = '\0';
            if (count < max_fields) fields[count++] = start;
            start = p + 1;
        }
    }
    if (count < max_fields) fields[count++] = start;
    return count;
}

int find_index(char **headers, int count, const char *name) {
    for (int i = 0; i < count; i++) if (strcmp(headers[i], name) == 0) return i;
    return -1;
}

char *pick_field(char **fields, int *idxs, int idx_count) {
    for (int i = 0; i < idx_count; i++) {
        int idx = idxs[i];
        if (idx >= 0 && fields[idx] && strlen(fields[idx]) > 0) return fields[idx];
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    const char *input = NULL;
    const char *task = NULL;
    for (int i = 1; i < argc - 1; i++) {
        if (strcmp(argv[i], "--input") == 0) input = argv[i + 1];
        if (strcmp(argv[i], "--task") == 0) task = argv[i + 1];
    }
    FILE *fp = fopen(input, "r");
    if (!fp) {
        fprintf(stderr, "Could not open input file\n");
        return 1;
    }

    double start = now_ms();
    char line[MAX_LINE];
    char *headers[128];
    fgets(line, sizeof(line), fp);
    line[strcspn(line, "\r\n")] = 0;
    int header_count = split_csv(line, headers, 128);

    int symbol_idxs[] = {find_index(headers, header_count, "symbol"), find_index(headers, header_count, "ticker"), find_index(headers, header_count, "Symbol"), find_index(headers, header_count, "Ticker"), find_index(headers, header_count, "stock"), find_index(headers, header_count, "Stock")};
    int date_idxs[] = {find_index(headers, header_count, "date"), find_index(headers, header_count, "Date")};
    int open_idxs[] = {find_index(headers, header_count, "open"), find_index(headers, header_count, "Open")};
    int high_idxs[] = {find_index(headers, header_count, "high"), find_index(headers, header_count, "High")};
    int low_idxs[] = {find_index(headers, header_count, "low"), find_index(headers, header_count, "Low")};
    int close_idxs[] = {find_index(headers, header_count, "close"), find_index(headers, header_count, "Close")};
    int volume_idxs[] = {find_index(headers, header_count, "volume"), find_index(headers, header_count, "Volume")};

    RowArray rows = {0};
    while (fgets(line, sizeof(line), fp)) {
        line[strcspn(line, "\r\n")] = 0;
        char *fields[128];
        int count = split_csv(line, fields, 128);
        char *symbol = pick_field(fields, symbol_idxs, 6);
        char *date = pick_field(fields, date_idxs, 2);
        char *open_s = pick_field(fields, open_idxs, 2);
        char *high_s = pick_field(fields, high_idxs, 2);
        char *low_s = pick_field(fields, low_idxs, 2);
        char *close_s = pick_field(fields, close_idxs, 2);
        char *volume_s = pick_field(fields, volume_idxs, 2);
        if (!(symbol && date && open_s && high_s && low_s && close_s && volume_s)) {
            rows.invalid++;
            continue;
        }
        Row r;
        snprintf(r.symbol, sizeof(r.symbol), "%s", symbol);
        snprintf(r.date, sizeof(r.date), "%s", date);
        r.open = atof(open_s);
        r.high = atof(high_s);
        r.low = atof(low_s);
        r.close = atof(close_s);
        r.volume = atol(volume_s);
        push_row(&rows, r);
        (void)count;
    }
    fclose(fp);

    int preview_count = 1;
    if (task && strcmp(task, "summary") == 0) {
        preview_count = 0;
        for (size_t i = 0; i < rows.size; i++) {
            int seen = 0;
            for (size_t j = 0; j < i; j++) if (strcmp(rows.data[i].symbol, rows.data[j].symbol) == 0) { seen = 1; break; }
            if (!seen) preview_count++;
        }
    } else if (task && strcmp(task, "analytics") == 0) {
        preview_count = (int)rows.size;
    } else if (task && strcmp(task, "top_movers") == 0) {
        preview_count = 20;
    }

    double elapsed_ms = now_ms() - start;
    printf("{\"language\":\"C\",\"task\":\"%s\",\"elapsed_ms\":%.3f,\"rows_processed\":%zu,\"invalid_rows\":%d,\"preview_count\":%d}\n",
           task ? task : "unknown", elapsed_ms, rows.size, rows.invalid, preview_count);
    free(rows.data);
    return 0;
}