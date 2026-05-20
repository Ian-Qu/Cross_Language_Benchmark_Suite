from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / 'results' / 'benchmark_results.csv'
SUMMARY_PATH = ROOT / 'results' / 'summary_table.csv'
LANGUAGE_COLORS = alt.Scale(
    domain=["Python", "C", "Java", "Rust"],
    range=["#4cf27e", "#2f80ed", "#f2994a", "#eb5757"]
)

st.set_page_config(page_title='Cross Language Benchmark Dashboard', layout='wide')
st.title('Language Benchmark Dashboard')
st.caption('Interactive dashboard for comparing C, Java, Python, and Rust on stock CSV analytics workloads.')

@st.cache_data
def load_results():
    return pd.read_csv(RESULTS_PATH)

@st.cache_data
def load_summary():
    return pd.read_csv(SUMMARY_PATH)

if not RESULTS_PATH.exists() or not SUMMARY_PATH.exists():
    st.warning('Run scripts/run_benchmarks.py first to generate benchmark results.')
    st.stop()

results = load_results()
summary = load_summary()

languages = st.sidebar.multiselect('Languages', sorted(summary['language'].dropna().unique()), default=sorted(summary['language'].dropna().unique()))
tasks = st.sidebar.multiselect('Tasks', sorted(summary['task'].dropna().unique()), default=sorted(summary['task'].dropna().unique()))
metric = st.sidebar.selectbox('Metric', ['median_ms', 'mean_ms', 'std_ms', 'speedup_vs_python'])

filtered_summary = summary[summary['language'].isin(languages) & summary['task'].isin(tasks)]
filtered_results = results[results['language'].isin(languages) & results['task'].isin(tasks)]

c1, c2, c3, c4 = st.columns(4)
if not filtered_summary.empty:
    fastest = filtered_summary.loc[filtered_summary['median_ms'].idxmin()]
    slowest = filtered_summary.loc[filtered_summary['median_ms'].idxmax()]
    c1.metric('Fastest median', f"{fastest['language']} - {fastest['task']}")
    c2.metric('Best median ms', f"{fastest['median_ms']:.3f}")
    c3.metric('Slowest median', f"{slowest['language']} - {slowest['task']}")
    c4.metric('Worst median ms', f"{slowest['median_ms']:.3f}")

st.subheader('Task comparison')
bar = alt.Chart(filtered_summary).mark_bar().encode(
    x=alt.X('task:N', title='Task'),
    y=alt.Y(f'{metric}:Q', title=metric.replace('_', ' ').title()),
    color=alt.Color(
    'language:N',
    scale=LANGUAGE_COLORS,
    legend=alt.Legend(title='Language')
),
    tooltip=['language', 'task', 'median_ms', 'mean_ms', 'std_ms', 'speedup_vs_python']
).properties(height=420)
st.altair_chart(bar, width='stretch')

st.subheader('Run-to-run variability')

variability_task = st.selectbox(
    'Choose a task to view',
    sorted(filtered_results['task'].dropna().unique())
)

variability_results = filtered_results[
    filtered_results['task'] == variability_task
].dropna(subset=['elapsed_ms'])

scatter = alt.Chart(variability_results).mark_circle(size=90).encode(
    x=alt.X('run_number:O', title='Run number'),
    y=alt.Y('elapsed_ms:Q', title='Elapsed time (ms)'),
    color=alt.Color(
        'language:N',
        scale=LANGUAGE_COLORS,
        legend=alt.Legend(title='Language')
    ),
    tooltip=['language', 'task', 'run_number', 'elapsed_ms']
).properties(height=320)

st.altair_chart(scatter, width='stretch')

st.subheader('Summary table')
st.dataframe(filtered_summary, width='stretch')

st.subheader('Raw benchmark results')
st.dataframe(filtered_results, width='stretch')
