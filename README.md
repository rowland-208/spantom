<div align="center">
  <img src="https://github.com/rowland-208/spantom/blob/main/etc/logo.png?raw=True" alt="logo" width="600">
</div>

Spantom is a Python package for simple, local application tracing and performance monitoring.

## Context Manager Usage

Spantom spans can be used as context managers. Tags created within a span are automatically associated with that span.

```python
from spantom import SP

for x in range(10):
    with SP.span("foo"):
        SP.tag({"index": x})
        print("foo")

print(SP.summary())
```

## Function Decorator Usage

Alternatively, spans can be attached to functions using decorators:

```python
from spantom import SP

@SP.span()
def foo(x):
    SP.tag({"foo_input": x})
    return "foo"

for x in range(10):
    foo(x)

print(SP.summary())
```

## Clearing the db
To reset the database and clear all spans, you can use the `SP.clear()` method:

```python
from spantom import SP

SP.clear()
```

## Real-World Example

A typical use case is capturing performance metrics and data from loops and function calls:

```python
@SP.span()
def slow_function(x):
    # Calculate something
    # ...
    
    SP.tag({"intermediate_result": y})
    
    # Finish processing
    # ...

for i in range(1000):
    with SP.span("outer_loop"):
        SP.tag({"index": i})
        
        # Perform slow operation
        # ...

        SP.tag({"value": value})

        slow_function(value)

        SP.tag({"threshold_exceeded": value > threshold})

        # Complete iteration
        # ...
```

Spantom automatically records the start and end time of each loop iteration and function call. It captures the dictionary values you tag with `SP.tag()` and associates them with the corresponding span. All data is stored in a SQLite database for later analysis of runtimes and correlations between tags.

## Dashboard

Spantom includes a web dashboard for visualizing and analyzing your spans. Install it with the dashboard option:

```bash
pip install spantom[dashboard]
```

Launch the dashboard:

```bash
spantom
```

![Sample image](https://github.com/rowland-208/spantom/blob/main/etc/dashboard.png?raw=True)

## Database Storage

Spans are automatically saved to a SQLite database. The default location is `/tmp/spantom.db`.
You can configure the database path by setting the `SPANTOM_DB` environment variable.

To use a non-default database with the dashboard:

```bash
spantom --db-path /path/to/my_spans.db
```

## Direct Database Access

For advanced analysis beyond the dashboard, you can query the SQLite database directly. This works particularly well with pandas:

```python
import pandas as pd
from spantom import SP

query = "SELECT name, duration, key, value FROM span_tags LEFT JOIN spans ON span_tags.span_id = spans.id WHERE key='your_key'"
df = pd.read_sql_query(query, SP.conn)
```

## Database Schema

A Spantom database contains two tables:
- `spans`: Contains span metadata (id, name, start, duration)
- `span_tags`: Contains tags associated with spans (id, span_id, key, value)
