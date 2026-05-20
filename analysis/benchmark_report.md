# Language Benchmark Report

## Overview
This report summarizes benchmark results for four implementations of the same stock CSV analytics workload on a Windows 64-bit system using Visual Studio Code as the development environment. The toolchain used for the project was Python 3.14.0, Java 17.0.6, Maven 3.9.16, Cargo 1.95.0, GNU Make 4.4.1, and GCC 14.2.0, as specified in the project setup notes.

The original expected performance order from slowest to fastest was Python, Java, Rust, and C. The measured results confirmed Python as slowest and C as fastest, but Java consistently outperformed Rust, so the actual middle ranking was Java ahead of Rust.

## Test Environment
The benchmarks were run on a Windows 64-bit laptop. The attached system image shows an MSI machine with a 13th Gen Intel Core i7-13620H processor, 16.0 GB of installed RAM, an NVIDIA GeForce RTX 4050 Laptop GPU with 6 GB, and Intel UHD Graphics.[image:1]

The workload processed 310,122 rows in each run, and each language was tested five times for each task: `parse_only`, `summary`, `analytics`, and `top_movers`. No invalid rows were reported in the recorded runs, which indicates that all implementations handled the dataset successfully during benchmarking.

## Results
Across all four tasks, C produced the fastest median times, ranging from 395.227 ms to 468.849 ms, while Python produced the slowest median times, ranging from 1,654.282 ms to 2,122.762 ms. Java placed second in every task, with median runtimes between 659.052 ms and 772.225 ms, while Rust placed third with medians between 1,029.774 ms and 1,076.491 ms.

| Task | Python median (ms) | Java median (ms) | Rust median (ms) | C median (ms) |
|------|--------------------|------------------|------------------|---------------|
| parse_only | 1654.282  | 659.052  | 1029.774  | 395.227  |
| summary | 1906.426  | 696.646  | 1041.276  | 468.849  |
| analytics | 2122.762  | 748.520  | 1056.124  | 412.019  |
| top_movers | 1934.616  | 772.225  | 1076.491  | 399.093  |

Relative to Python, C achieved speedups from 4.066x to 5.152x depending on the task, Java achieved speedups from 2.505x to 2.836x, and Rust achieved speedups from 1.606x to 2.010x. The largest measured C advantage appeared in the `analytics` workload, where C was 5.152x faster than Python based on median runtime.

## Variability and Consistency
Run-to-run variation was modest for all compiled implementations, especially C, whose standard deviation stayed between 5.270 ms and 15.376 ms across the four tasks. Java also showed stable results, with standard deviation from 9.964 ms to 25.819 ms, while Rust varied from 24.796 ms to 33.043 ms.

Python showed the highest variability in absolute terms, with standard deviation between 37.656 ms and 87.927 ms. Even with that variation, the rank order remained unchanged across tasks: Python was slowest, Java outperformed Rust, and C remained fastest.

## Discussion
The results show a clear separation between the interpreted Python implementation and the compiled languages, with C establishing the best overall performance on every task. The most notable finding is that Java exceeded the initial expectation by outperforming Rust across all workloads rather than trailing it.

This outcome suggests that for this particular project, implementation details and library behavior mattered more than a simple language-level assumption about performance. In practical terms, C delivered the strongest raw speed, Java offered a strong middle-ground result, Rust remained substantially faster than Python, and Python traded performance for convenience and development simplicity.

## Conclusion
The benchmark data supports the final performance ranking of Python, Rust, Java, and C from slowest to fastest. That ranking differs from the original hypothesis only in the middle positions, where Java consistently finished ahead of Rust in all four benchmark categories.

Overall, the experiment demonstrates that expected language rankings should be tested empirically rather than assumed. On this Windows 64-bit MSI system, C was the clear leader, Java was the second-fastest option, Rust was third, and Python was the slowest for the tested CSV analytics workloads.
