"""Parse a TOML string with Tomli, exactly as the README's first example shows."""

import tomli

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

toml_dict = tomli.loads(toml_str)

print(toml_dict)

assert toml_dict == {
    "players": [{"name": "Lehtinen", "number": 26}, {"name": "Numminen", "number": 27}]
}
