<div align="center">
  <img src="https://github.com/rowland-208/spantom/blob/main/etc/logo.png?raw=True" alt="logo" width="600">
</div>

Spantom is a python package for simple local tracing.

To get started try this example:
```python
from spantom import SP

SP.init()

@SP.span()
def foo(x):
    SP.tag({"foo_input": x})
    return "foo"

print(SP.summary())
```

Spans are saved to a sqlite database.
The default database is `/tmp/spantom.db`,
but you can specify a different path at init:
```
SP.init("/path/to/my_spans.db")
```

A typical use case would be to capture metrics from a for loop:
```python
@SP.span()
def my_slow_function(x):
    ...
    
    @SP.tag({"intermediate_result": y})
    
    ...

for i in range(1000):
    my_slow_function(i)
```

When a function is tagged with span Tracelite will record the start and end time of the function call.
This allows you to measure function durations and find bottlenecks in your code.

Additionally span tags are a powerful mechanism to record arbitrary metadata about the function call.
The tag keys and values can be any strings.
This allows you to capture metrics, parameters, or any other relevant information.

Tracelite comes with a simple viewer to query and plot the spans.
To use the viewer, install spantom with the dashboard option:
```bash
pip install spantom[dashboard]
```

Then launch the viewer:
```bash
spantom --db-path /path/to/my_spans.db
```
![Sample image](https://github.com/rowland-208/spantom/blob/main/etc/dashboard.png?raw=True)

Or you can query the spans manually using sqlite3.
This works well in combination with pandas.
```python
import sqlite3

import pandas as pd
from spantom import DEFAULT_DB

self.conn = sqlite3.connect(DEFAULT_DB)
self.curs = self.conn.cursor()
df_spans = pd.read_sql_query("SELECT * FROM spans", self.conn)
df_tags = pd.read_sql_query("SELECT * FROM span_tags", self.conn)
```

A Tracelite database contains two tables:
- `spans`: Contains the span data: id, name, start, and duration
- `span_tags`: Contains tags associated with spans: id, span_id, key, value
