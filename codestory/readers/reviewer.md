# The reviewer
Someone deciding whether to approve this change: they did not write it, and they will be accountable for it once
it merges. They will not read the diff line by line. They need to know what the change makes different, what it
keeps the same, and what could go wrong.

They care about behaviour before and after: what a caller now gets that it did not get before, and what it no
longer gets. They care about evidence: which tests show the difference, and what those tests do not cover. They
care about risk: new defaults and settings, new failure modes, callers that relied on the old behaviour, and
anything the change touches that no test runs. Style, naming and refactoring matter only where they change
behaviour.

After reading, they can:
- state what the change makes true that was not true before, and under which conditions
- name the evidence for each claim, and say which claims rest on code alone
- name what the change could break, and for whom
- decide whether they would approve it, and what they would ask the author first
