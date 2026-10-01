# The maintainer
Someone, human or agent, who has just been handed this code and must change it without breaking it.

They care about how it actually works inside, where the load-bearing parts are, which invariants other code
relies on, and where it is fragile or surprising. Tests matter when they pin down behaviour a change could break.
Build tooling, CI and release mechanics matter only if a change would touch them.

After reading, they can:
- trace a typical request or value through the code, naming the functions it passes through
- say which invariants a change must preserve, and where each is enforced
- predict what a small, specific change would break
- find the right place to make a given kind of change
