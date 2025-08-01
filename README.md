<div align="center">
  <img src="https://github.com/rowland-208/spantom/blob/main/etc/logo.png?raw=True" alt="logo" width="600">
</div>

Spantom is a python package for simple local tracing.

Spantom spans can use a context manager. Span tags are associated with the span they are created in.
```python
from spantom import SP

SP.init()

for x in range(10):
    with SP.span("foo"):
        SP.tag({"index": x})
        print("foo")

print(SP.summary())
```

Or spans can be attached to functions.
```python
from spantom import SP

SP.init()

@SP.span()
def foo(x):
    SP.tag({"foo_input": x})
    return "foo"

for x in range(10):
    foo(x)

print(SP.summary())
```

A typical use case would be to capture metrics from a for loop.
```python
@SP.span()
def slow_function(x):
    # calculate something
    ...
    
    @SP.tag({"intermediate_result": y})
    
    #finish up
    ...

for i in range(1000):
    with SP.span("outer_loop"):
        SP.tag({"index": i})
        
        # do something slow
        ...

        SP.tag({"value": value})

        slow_function(value)

        SP.tag({"threshold_exceeded": x > threshold})

        # finish up
        ...
```

Spantom will record the start and end time of each loop, and of each call to slow_function.
It will record the dictionary values you tagged with SP.tag and associate them with the corresponding span.
These values are stored in a sqlite database where you can analyze runtimes and correlations between tags.

Try the spantom dashboard to get started analyzing spans.
It can be installed with pip options.
```bash
pip install spantom[dashboard]
```

To launch the dashboard:
```bash
spantom
```
![Sample image](https://github.com/rowland-208/spantom/blob/main/etc/dashboard.png?raw=True)

Spans are saved to a sqlite database.
The default database is `/tmp/spantom.db`.
You can configure the database path by setting the SPANTOM_DB environment variable,
or by passing a path to SP.init().

You can specify a different database path for the dashboard:
```bash
spantom --db-path /path/to/my_spans.db
```

I use the spantom dashboard for quick analysis of spans.
For more in depth analysis, you can use the sqlite database directly.
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

A Spantom database contains two tables:
- `spans`: Contains the span data:id, name, start, and duration
- `span_tags`: Contains tags associated with spans: id, span_id, key, value
