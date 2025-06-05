import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
README = ROOT / "README.md"


def extract_python_code(markdown_text):
    pattern = r"```python\n(.*?)\n```"
    return re.findall(pattern, markdown_text, re.DOTALL)


def test_extract_markdown():
    FUN1 = """\
 def hello():
    print("hi")   
"""
    FUN2 = """\
x = 10
y = 20
print(x + y)
"""
    markdown_content = f"""\
Here is some text.

```python
{FUN1}
```

Some more text.

```python
{FUN2}
```
"""
    extracted = extract_python_code(markdown_content)
    assert extracted == [FUN1, FUN2]


@pytest.mark.repo
def test_readme():
    """Make sure the code in the readme can be executed."""
    with open(README) as f:
        content = f.read()

    code = "\n".join(extract_python_code(content))
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
