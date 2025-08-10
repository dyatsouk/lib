# Optimization Helpers

This package provides utilities for tuning strategy parameters by running
simulations.  The functions use a light-weight hill-climbing search to
adjust parameters and observe how the win rate changes.

* `optimise_parameter` – tweak a single parameter for one role.
* `optimise_all` – iteratively optimise parameters for multiple roles and
  supports tuning several parameters for the same role.
* `optimise_from_config` – load an optimisation run from a JSON/YAML file.

Both functions accept a `seed` argument so that optimisation runs remain
reproducible during tests.

## Command Line Usage

Optimisations can be executed directly from the shell by pointing the module
at a configuration file:

```bash
python -m mafia.optimization example_configs/optimization.yaml
```

The configuration format mirrors `example_configs/optimization.yaml` and
allows specifying which parameters to tune – including multiple parameters
per role – along with any fixed strategies for other roles.
