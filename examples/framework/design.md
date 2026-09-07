# Design decisions

Status: rejected visual draft, retained for historical review. Not a recommended
composition or a user-approved reference. See the main gallery for current demos.

## Reader question

How does velocity supervision during training become conditional generation?

## Scientific graph

Training: `(x₀, x₁, t)` feeds the straight interpolant `xₜ`.
`(xₜ, t, c)` feeds the learned velocity function, whose output is compared against
the displacement `x₁−x₀`. Both reach the squared-error loss. Generation starts from
new base noise, conditions on `c`, and integrates the learned field to an endpoint.
The downward dashed connection carries learned parameters, not a state sample.

This is the independent linear-path teaching formulation described in the scene's
source notes. It does not illustrate minibatch optimal-transport pairing.

Source check: Tong et al., Section 3.2.2, Equations (14)–(15) and the following
zero-smoothing paragraph, checked in the original arXiv HTML. The drawing uses the
`σ = 0` straight-path case. External condition `c` is an explicit teaching extension,
not the source's endpoint-pair variable `z`. No conclusion from its nonzero-smoothed
endpoint proposition is used for the unsmoothed drawing.

## Composition

Two stacked horizontal bands reserve the larger continuous view for generation.
The training band exposes endpoint states, intermediate points, the learned function,
and both vectors entering the loss. The lower band shows the noise-to-output route
over a visible vector grid rather than merely labelling a box “ODE.”

A single connected diagram would put the training target near inference inputs and
invite a false dependency. Separate panels cost vertical space but keep these roles
clear. There are no zoom leaders because no computation appears at two scales.

## Visual roles

- Blue states come from the base distribution.
- Coral denotes endpoint data, target velocity or generated endpoints.
- Violet denotes interpolation states and the learned velocity function.
- Neutral thin grid lines supply coordinates without becoming scientific categories.
- Solid arrowed lines show state flow. Dashed arrows show conditions or parameter transfer.

Arial labels and restrained geometry form one modern visual system. No former ODE
font-comparison asset is reused. All artwork and layout are original; literature
references supply equations only, not a visual template.

## Review requirements

- Inputs, velocity prediction, target and loss must have no ambiguous junctions.
- Straight training paths and curved inference paths must remain distinct.
- The inference curves may not branch from the same state or cross each other.
- Labels must remain legible in a full-width README preview.
- The actual exported PowerPoint must contain native shapes and no raster slide.
- A representative selected-object edit must preserve every unselected source object.

The point clouds, field and trajectories are schematic. They do not assert a
numerically solved process, density estimate, confidence interval, or model result.
