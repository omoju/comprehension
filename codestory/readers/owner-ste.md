# The owner, in Simplified Technical English
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

## How this reader wants it written: ASD-STE100 (Simplified Technical English)
Write the whole chapter, narration and callouts, by these rules:
- One topic per sentence. Descriptive sentences have at most 25 words; instructions have at most 20.
- Paragraphs have at most 6 sentences and start with the topic sentence.
- Active voice. Name the agent: "escape() replaces the five characters", not "the five characters are replaced".
- Present tense for what the code does; simple past only for what already happened in the run.
- Instructions to the reader are imperatives: "Check the default", not "You should check the default".
- One word, one meaning, everywhere. Use the names the code uses (`escape`, `Markup`, `striptags`) and do not
  replace them with synonyms. Do not use metaphors, idioms, or words with more than one meaning in context.
- No noun clusters of more than three words. Break them up with prepositions.
- No gerunds as nouns ("the escaping of the text" → "escape() escapes the text").
- Prefer short, common words: "use" not "utilize", "start" not "initiate", "if" not "in the event that".
- Write numbers as figures. Write the data's real values from the trace exactly as they appear.
- Warnings and cautions come before the sentence they apply to, as their own sentence.
The story still follows the data in close third person; STE changes the sentences, not the plot.
