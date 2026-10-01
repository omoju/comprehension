# The user
A developer who will call this code from their own and wants to use it correctly.

They care about the behaviour they rely on: what goes in, what comes out, what errors mean and what to do about
them, and why the behaviour is the way it is. They want enough of the inside to predict behaviour, and no more.
Internals that don't change what a caller observes are out of scope, as are tests, typing and CI.

After reading, they can:
- choose the right entry point for their task and configure it correctly
- predict the output and the errors for a given input
- handle each kind of failure correctly
- avoid the common ways of misusing it
