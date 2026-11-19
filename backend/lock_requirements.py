"""Run after installing requirements.in in an isolated environment."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement

root=Path(__file__).parent
queue=[Requirement(line) for line in (root/'requirements.in').read_text().splitlines() if line.strip() and not line.startswith('#')]
seen={}
while queue:
    req=queue.pop()
    dist=distribution(req.name)
    if dist.metadata['Name'] in seen: continue
    seen[dist.metadata['Name']]=dist.version
    for line in dist.requires or []:
        child=Requirement(line)
        if child.marker is None or any(child.marker.evaluate({'extra':extra}) for extra in (req.extras or {''})):
            queue.append(child)
(root/'requirements.txt').write_text('# Resolved runtime dependencies; regenerate with python lock_requirements.py.\n'+
    ''.join(f'{name}=={version}\n' for name,version in sorted(seen.items(),key=lambda p:p[0].lower())))
