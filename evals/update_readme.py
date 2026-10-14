"""Copy results/summary.md into README.md between the EVAL_TABLE markers."""
import re
from pathlib import Path

summary = Path("results/summary.md").read_text().strip()
readme = Path("README.md")
readme.write_text(re.sub(
    r"(<!-- EVAL_TABLE_START -->).*?(<!-- EVAL_TABLE_END -->)",
    lambda m: f"{m.group(1)}\n{summary}\n{m.group(2)}",
    readme.read_text(), flags=re.S))
print("README updated")
