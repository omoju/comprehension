# The owner
Someone accountable for code they did not write: a reviewer, a tech lead, an owner who must vouch for it.
They will not read it line by line. They need to know what it guarantees and what could go wrong.

They care about behaviour and guarantees, trust boundaries, failure modes, security-relevant choices and their
defaults, and the decisions a reasonable person might disagree with. Internals matter only where they carry a
guarantee or a risk. Tests, typing, packaging and CI are out of scope unless they are where a guarantee lives.

After reading, they can:
- state what the code guarantees and under which conditions
- name the ways it can fail or be misused, and what happens when it does
- identify the defaults and design choices that carry risk, and why they were made
- decide whether they would sign off on it, and what they would ask first
