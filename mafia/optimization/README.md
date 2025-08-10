# Optimization Helpers

This package provides utilities for tuning strategy parameters by running
simulations.  The functions use a light-weight hill-climbing search to
adjust parameters and observe how the win rate changes.

* `optimise_parameter` – tweak a single parameter for one role.
* `optimise_all` – iteratively optimise parameters for multiple roles.

Both functions accept a `seed` argument so that optimisation runs remain
reproducible during tests.
