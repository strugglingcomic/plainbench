# PlainBench Examples

**Working examples demonstrating PlainBench features**

All examples are self-contained and executable. Run them to see PlainBench in action!

---

## Quick Start

```bash
# Run all examples
python examples/basic_decorator.py
python examples/shell_commands.py
python examples/isolation_comparison.py
python examples/database_queries.py
python examples/algorithm_comparison.py
python examples/queue_benchmarking.py

# Or run a specific example
python examples/basic_decorator.py
```

**Note:** Most examples store results in `./benchmarks.db`. The database queries example reads from this database, so run other examples first!

---

## Example Files

### 1. basic_decorator.py

**What it demonstrates:**
- Simple `@benchmark` decorator usage
- Different warmup and run configurations
- Custom metrics selection
- Named benchmarks
- Multiple function benchmarking
- Disabling garbage collection
- Custom database locations

**Concepts covered:**
- Decorator parameters
- Default vs. custom configuration
- Database storage
- How benchmarked functions work normally

**Run time:** ~30 seconds

**Output:**
- Console output showing benchmark execution
- Results stored in `./benchmarks.db` and `./my_benchmarks.db`

**Example snippet:**
```python
@benchmark(warmup=5, runs=20, metrics=['wall_time', 'python_memory'])
def list_comprehension(n):
    return [i**2 for i in range(n)]

result = list_comprehension(5000)
```

**Learn:**
- How to add benchmarking to your functions
- How to customize benchmark parameters
- Where benchmark data is stored

---

### 2. shell_commands.py

**What it demonstrates:**
- Shell command benchmarking with `benchmark_shell()`
- Snapshot vs. continuous monitoring
- Timeout handling
- Output capture
- Comparing different command approaches
- Resource monitoring (memory, CPU, I/O)
- Statistical analysis of results

**Concepts covered:**
- Shell command execution
- Process monitoring modes
- Resource metrics collection
- Performance comparison methodology
- Coefficient of variation

**Run time:** ~1 minute

**Output:**
- Detailed benchmark results for shell commands
- Resource usage statistics
- Performance comparisons

**Example snippet:**
```python
result = benchmark_shell(
    'find /usr -name "*.py"',
    monitoring_mode='continuous',
    monitoring_interval=0.1
)
print(f"Peak memory: {result.statistics.peak_memory.mean / 1024 / 1024:.2f} MB")
```

**Learn:**
- How to benchmark external commands
- Different monitoring strategies
- When to use snapshot vs. continuous mode
- How to interpret resource metrics

---

### 3. isolation_comparison.py

**What it demonstrates:**
- Three isolation levels (minimal, moderate, maximum)
- Same workload with different isolation
- Impact of isolation on reproducibility
- Querying and analyzing results from database
- Calculating coefficient of variation
- Visual comparison of consistency

**Concepts covered:**
- Isolation strategies
- Reproducibility vs. overhead trade-offs
- Statistical variance
- Database querying

**Run time:** ~1 minute

**Output:**
- Benchmark results for each isolation level
- Statistical comparison
- Recommendations for choosing isolation

**Example snippet:**
```python
@benchmark(isolation='moderate', runs=20)
def compute_with_moderate_isolation(n=50000):
    return sum(i**2 for i in range(n))
```

**Learn:**
- When to use each isolation level
- How isolation affects measurement variance
- Trade-offs between reproducibility and overhead
- How to choose the right isolation for your needs

---

### 4. database_queries.py

**What it demonstrates:**
- Querying benchmark results from database
- Getting latest runs and historical data
- Accessing measurements and statistics
- Comparing benchmark runs
- Detecting performance regressions
- Exporting data to JSON

**Concepts covered:**
- Database operations
- Run metadata
- Measurement vs. statistics
- Benchmark comparison
- Regression detection
- Data export

**Prerequisites:**
- Run other examples first to populate database

**Run time:** ~10 seconds

**Output:**
- Database query results
- Run comparisons
- Exported JSON file

**Example snippet:**
```python
db = BenchmarkDatabase("./benchmarks.db")
db.initialize()

latest = db.get_latest_run()
history = db.get_benchmark_history("fibonacci", limit=10)
stats = db.get_statistics(run_id=latest.run_id)
```

**Learn:**
- How to query benchmark results
- Database schema and relationships
- How to compare runs
- How to detect regressions
- Exporting data for external analysis

---

### 5. algorithm_comparison.py

**What it demonstrates:**
- Complete real-world benchmarking workflow
- Comparing multiple algorithm implementations
- Statistical analysis and interpretation
- Speedup calculations
- Coefficient of variation analysis
- Range ratio for outlier detection
- Best practices for algorithm benchmarking

**Algorithms benchmarked:**
1. Python's built-in sorted() (Timsort)
2. Bubble sort
3. Quicksort
4. Insertion sort

**Concepts covered:**
- Algorithm complexity (O(n²) vs. O(n log n))
- Appropriate test data sizing
- Correctness verification before benchmarking
- Performance comparison methodology
- Statistical significance
- Presenting results

**Run time:** ~2 minutes

**Output:**
- Sorted results by performance
- Speedup analysis
- Statistical insights
- Recommendations

**Example snippet:**
```python
@benchmark(name="sort_builtin", isolation='moderate', runs=20)
def builtin_sort(data):
    return sorted(data)

@benchmark(name="sort_quicksort", isolation='moderate', runs=20)
def quick_sort(data):
    return _quicksort(data.copy())

# Compare performance
```

**Learn:**
- How to structure a benchmark comparison
- Choosing appropriate test data
- Analyzing and presenting results
- Best practices for fair comparisons
- Real-world benchmarking methodology

---

### 6. queue_benchmarking.py

**What it demonstrates:**
- SQLite-backed queue implementation
- Benchmarking enqueue/dequeue operations
- Batch vs. single operation comparison
- Mixed workload patterns (producer-consumer)
- Disk I/O analysis
- Throughput calculations
- Performance recommendations

**Concepts covered:**
- Queue operations
- Batch processing benefits
- SQLite WAL mode
- Disk I/O metrics
- Throughput analysis
- Real-world workload simulation

**Run time:** ~1 minute

**Output:**
- Queue operation performance
- Batch vs. single operation speedup
- Throughput analysis
- Recommendations for production

**Example snippet:**
```python
@benchmark(name="queue_enqueue_batch", metrics=['wall_time', 'disk_io'])
def benchmark_enqueue_batch():
    queue.clear()
    messages = [f"Message {i}" for i in range(1000)]
    queue.enqueue_batch(messages)
    return queue.size()
```

**Learn:**
- Benchmarking database operations
- Benefits of batch processing
- SQLite performance optimization
- Queue implementation patterns
- Production recommendations

**Bonus:** Demonstrates the original PlainBench vision from the README!

---

## Example Progression

### Beginner Path

1. **basic_decorator.py** - Learn decorator basics
2. **shell_commands.py** - Benchmark external commands
3. **database_queries.py** - Query and analyze results

### Intermediate Path

1. **basic_decorator.py** - Foundation
2. **isolation_comparison.py** - Understand isolation
3. **algorithm_comparison.py** - Real-world comparison
4. **database_queries.py** - Analysis and export

### Advanced Path

1. **algorithm_comparison.py** - Complete methodology
2. **queue_benchmarking.py** - Production patterns
3. **isolation_comparison.py** - Reproducibility deep-dive
4. **database_queries.py** - Advanced analysis

---

## Running Examples

### Run Individual Example

```bash
python examples/basic_decorator.py
```

### Run All Examples (in order)

```bash
# Populate database with varied benchmarks
python examples/basic_decorator.py
python examples/shell_commands.py
python examples/isolation_comparison.py
python examples/algorithm_comparison.py
python examples/queue_benchmarking.py

# Then analyze all the data
python examples/database_queries.py
```

### Clean Up

```bash
# Remove benchmark databases
rm benchmarks.db benchmarks.db-* my_benchmarks.db benchmark_run_*.json
```

---

## Expected Output

### Typical Run

```bash
$ python examples/basic_decorator.py

PlainBench Basic Decorator Examples
======================================================================

Running Example 1: Simple sum with defaults...
  Result: 49995000

Running Example 2: List comprehension with custom runs...
  Result length: 5000

...

======================================================================
All benchmarks completed!

Results stored in:
  - ./benchmarks.db (examples 1-6)
  - ./my_benchmarks.db (example 7)
```

### Database After Examples

```bash
$ sqlite3 benchmarks.db "SELECT COUNT(*) FROM benchmark_runs;"
# Should show multiple runs

$ sqlite3 benchmarks.db "SELECT benchmark_name FROM benchmark_runs LIMIT 5;"
# Shows names of benchmarked functions
```

---

## Common Issues

### Issue: Import Error

```
ImportError: No module named 'plainbench'
```

**Solution:** Install PlainBench
```bash
pip install -e .
```

### Issue: Database Locked

```
sqlite3.OperationalError: database is locked
```

**Solution:** Close other connections or wait for previous example to finish

### Issue: Permission Denied (Isolation)

```
PermissionError: CPU affinity requires elevated privileges
```

**Solution:** This is expected on some platforms. The example will continue with available features.

---

## Customizing Examples

### Modify Example Data

Edit the example files to change:
- Data sizes (e.g., `n=50000`)
- Number of runs (e.g., `runs=20`)
- Metrics collected (e.g., `metrics=['wall_time', 'python_memory']`)
- Isolation levels (e.g., `isolation='maximum'`)

### Add Your Own Functions

```python
@benchmark(name="my_custom_function", runs=15)
def my_function(n):
    # Your code here
    return result

# Run it
my_function(10000)
```

### Experiment with Settings

Try different combinations:

```python
# Low overhead, less consistent
@benchmark(isolation='minimal', runs=10)

# High reproducibility, more overhead
@benchmark(isolation='maximum', runs=50, warmup=10)

# Memory-focused
@benchmark(metrics=['python_memory', 'process_memory'], runs=20)
```

---

## Next Steps

After running the examples:

1. **Read the Documentation**
   - [Quick Start Guide](../docs/quickstart.md)
   - [User Guide](../docs/user-guide.md)

2. **Apply to Your Code**
   - Add `@benchmark` to your functions
   - Compare algorithm implementations
   - Track performance over time

3. **Explore the Database**
   ```bash
   sqlite3 benchmarks.db
   SELECT * FROM benchmark_runs;
   SELECT * FROM benchmark_statistics;
   ```

4. **Create Your Own Benchmarks**
   - Start with simple functions
   - Gradually add complexity
   - Build a benchmark suite for your project

---

## Example Comparison Matrix

| Example | Difficulty | Runtime | Database | Concepts |
|---------|-----------|---------|----------|----------|
| basic_decorator.py | Beginner | 30s | Creates | Decorator basics |
| shell_commands.py | Beginner | 1m | Independent | Shell benchmarking |
| isolation_comparison.py | Intermediate | 1m | Creates | Isolation levels |
| database_queries.py | Intermediate | 10s | Reads | Database operations |
| algorithm_comparison.py | Advanced | 2m | Creates | Full workflow |
| queue_benchmarking.py | Advanced | 1m | Creates | Production patterns |

---

## Support

**Questions or Issues?**

- Check the [User Guide](../docs/user-guide.md)
- See [Troubleshooting](../docs/user-guide.md#troubleshooting)
- Review [DEVELOPMENT.md](../DEVELOPMENT.md) for implementation details

**Want to Contribute?**

These examples are a great starting point for understanding PlainBench internals!

---

## Summary

The PlainBench examples provide:

✅ **7 working examples** covering all major features
✅ **Progressive difficulty** from beginner to advanced
✅ **Real-world scenarios** including algorithm comparison and queue benchmarking
✅ **Best practices** demonstrated throughout
✅ **Complete workflows** from benchmarking to analysis

**Start with `basic_decorator.py` and work your way up!**

Happy benchmarking! 🚀
