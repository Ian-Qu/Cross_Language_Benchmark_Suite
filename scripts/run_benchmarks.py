import argparse
import csv
import json
import statistics
import subprocess
from pathlib import Path

TASKS = ['parse_only', 'summary', 'analytics', 'top_movers']


def safe_build(name, fn, root):
    try:
        fn(root)
        return None
    except Exception as e:
        return f"{name} build failed: {e}"


def build_c(root):
    subprocess.run(["mingw32-make"], cwd=root / "c", check=True)


def build_rust(root):
    subprocess.run(["cargo", "build", "--release"], cwd=root / "rust", check=True)


def build_java(root):
    java_dir = root / "java"
    src_root = java_dir / "src" / "main" / "java"
    out_dir = java_dir / "target" / "classes"
    out_dir.mkdir(parents=True, exist_ok=True)
    java_files = [str(p) for p in src_root.rglob("*.java")]
    if not java_files:
        raise RuntimeError("No Java source files found")
    subprocess.run(
        ["javac", "-d", str(out_dir), *java_files],
        cwd=java_dir,
        check=True
    )


def run_command(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    output = result.stdout.strip()
    if not output:
        raise RuntimeError("Command produced no stdout output")

    last_line = output.splitlines()[-1].strip()
    try:
        return json.loads(last_line)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Expected JSON on last stdout line, got: {last_line}\n\nFull stdout:\n{output}\n\nStderr:\n{result.stderr.strip()}"
        )


def not_built_row(language, task, status='not_built'):
    return {
        'language': language,
        'task': task,
        'elapsed_ms': None,
        'rows_processed': 0,
        'invalid_rows': 0,
        'preview_count': 0,
        'status': status,
    }


def run_python(input_path, task, root):
    return run_command([
        'python', 'python/main.py', '--input', str(input_path), '--task', task, '--json'
    ], cwd=root)


def run_c(input_path, task, root):
    candidates = [
        root / 'c' / 'benchmark.exe',
        root / 'c' / 'benchmark',
        root / 'c' / 'main.exe',
        root / 'c' / 'main',
    ]
    exe = next((p for p in candidates if p.exists()), None)
    if exe is None:
        return not_built_row('C', task)
    return run_command([str(exe), '--input', str(input_path), '--task', task])


def run_rust(input_path, task, root):
    candidates = [
        root / 'rust' / 'target' / 'release' / 'stock_language_benchmark.exe',
        root / 'rust' / 'target' / 'release' / 'stock_language_benchmark',
    ]
    exe = next((p for p in candidates if p.exists()), None)
    if exe is None:
        return not_built_row('Rust', task)
    return run_command([str(exe), '--input', str(input_path), '--task', task])


def run_java(input_path, task, root):
    classes = root / 'java' / 'target' / 'classes'
    if not classes.exists():
        return not_built_row('Java', task)
    return run_command([
        'java', '-cp', str(classes), 'com.ianquaye.benchmark.Main',
        '--input', str(input_path), '--task', task
    ])


def summarize(results, out_path):
    grouped = {}
    for row in results:
        if row.get('elapsed_ms') is None:
            continue
        key = (row['language'], row['task'])
        grouped.setdefault(key, []).append(float(row['elapsed_ms']))

    summary_rows = []
    python_baseline = {}

    for (language, task), vals in grouped.items():
        median_ms = statistics.median(vals)
        mean_ms = statistics.mean(vals)
        std_ms = statistics.stdev(vals) if len(vals) > 1 else 0.0
        if language == 'Python':
            python_baseline[task] = median_ms
        summary_rows.append({
            'language': language,
            'task': task,
            'median_ms': round(median_ms, 3),
            'mean_ms': round(mean_ms, 3),
            'std_ms': round(std_ms, 3),
        })

    for row in summary_rows:
        base = python_baseline.get(row['task'])
        row['speedup_vs_python'] = round(base / row['median_ms'], 3) if base and row['median_ms'] else None

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['language', 'task', 'median_ms', 'mean_ms', 'std_ms', 'speedup_vs_python']
        )
        writer.writeheader()
        writer.writerows(summary_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--runs', type=int, default=5)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    input_path = Path(args.input)
    results_dir = root / 'results'
    results_dir.mkdir(exist_ok=True)

    c_build_error = safe_build('C', build_c, root)
    rust_build_error = safe_build('Rust', build_rust, root)
    java_build_error = safe_build('Java', build_java, root)

    for err in [c_build_error, rust_build_error, java_build_error]:
        if err:
            print(err)

    results = []

    for task in TASKS:
        for run_number in range(1, args.runs + 1):
            py = run_python(input_path, task, root)
            py['run_number'] = run_number
            py.setdefault('status', '')
            results.append(py)

            c = run_c(input_path, task, root)
            c['run_number'] = run_number
            if c_build_error and c.get('status') == 'not_built':
                c['status'] = 'build_failed'
            results.append(c)

            rs = run_rust(input_path, task, root)
            rs['run_number'] = run_number
            if rust_build_error and rs.get('status') == 'not_built':
                rs['status'] = 'build_failed'
            results.append(rs)

            jv = run_java(input_path, task, root)
            jv['run_number'] = run_number
            if java_build_error and jv.get('status') == 'not_built':
                jv['status'] = 'build_failed'
            results.append(jv)

    with open(results_dir / 'benchmark_results.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'language', 'task', 'elapsed_ms', 'rows_processed',
            'invalid_rows', 'preview_count', 'run_number', 'status'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fieldnames})

    summarize(results, results_dir / 'summary_table.csv')
    print('Wrote results/benchmark_results.csv and results/summary_table.csv')


if __name__ == '__main__':
    main()