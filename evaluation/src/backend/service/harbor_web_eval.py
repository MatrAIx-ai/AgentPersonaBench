"""Harbor web-eval integration (re-exported for Playground backend imports)."""

import playground.harbor.web_eval as _source

globals().update(
    {name: getattr(_source, name) for name in dir(_source) if not name.startswith("__")}
)
