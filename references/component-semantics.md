# Scientific limits of the starter components

These are original explanatory diagrams, not measured results or recovered source data.

## ODE

For `dx/dt = v(x,t)`, uniqueness requires appropriate assumptions on the velocity field
(for example local Lipschitz continuity in x). A single initial condition under such
a field has one deterministic trajectory. Multiple trajectories may represent different
initial conditions. Avoid arbitrary branching of the same state at the same time.
Projected trajectories can cross in a projection without violating uniqueness; the
starter should not invite an unexplained crossing interpretation.

## SDE

For `dX = b(X,t)dt + sigma(X,t)dW`, drift and random increments have different roles.
Multiple sample paths may leave the same initial condition. Illustrated jagged paths
are not empirical uncertainty estimates. Do not label an arbitrary envelope as a
confidence interval or claim a solver, variance, or distribution that was not computed.

## Flow Matching

The starter uses a conditional straight-path example to explain a training target.
Endpoint coupling and the conditional path must be chosen for a specific method.
The learned marginal velocity field and its sampling ODE must be distinguished from
the conditional training path. Flow Matching does not inherently require every
inference trajectory to be straight and is not synonymous with an SDE.

## Reusable versus paper-specific

Store scientific meaning, assumptions, forbidden interpretations and provenance with
each component. Replacing an endpoint label must not silently assert a new distribution.
Do not treat stylistic similarity to a published figure as methodological evidence.
Mingzhe's academic-figure-master is a user-supplied design reference, not the authority
for these scientific statements. No external asset is original merely after recoloring.
