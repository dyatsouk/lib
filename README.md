# Sports Mafia Simulation

This project provides a minimal framework for simulating the **sports mafia** party game.  
The goal is to allow experimentation with different player strategies and to gather
statistics over multiple games.

## Game Overview

The implementation roughly follows the [sports mafia rules](https://dom-mafia.ru/sport_mafia_game_rules):

* Ten players participate.
* Roles consist of seven civilians (one of which is the **sheriff**) and three mafia members (one of which is the **don**).
* The game alternates between **day** and **night** phases.
  * During the day each alive player may nominate at most one opponent for elimination and may claim to be the sheriff revealing a check result.
  * After speeches all alive players vote on the nominated candidates. If at least one candidate exists every player must cast a vote; failing to choose assigns the vote to the last nominated player. On the very first day a single nomination skips voting entirely. The player with the most votes is eliminated. When multiple candidates tie for the most votes, the tied players receive an additional 30 seconds to speak and a revote is held. If the revote reduces the set of tied players the process repeats; if the same set ties again the table votes on whether all tied players should be eliminated. An absolute majority eliminates all of them; otherwise nobody is removed.
  * At night special roles act:
    * The sheriff secretly checks a player and learns if they are mafia. If the sheriff is killed during the night they still perform this final check before dying at dawn.
    * The don searches for the sheriff.
    * The mafia collectively choose one player to kill.
* The game ends when either all mafia members are eliminated (civilians win) or the number of mafia equals or exceeds the number of civilians (mafia win).

## Code Structure

```
mafia/
├── actions.py      # Dataclasses describing speeches, votes and round logs
├── game.py         # Main game engine coordinating day/night cycles
├── player.py       # Player representation tying a role to a strategy
├── roles.py        # Role enum and helpers
├── strategies.py   # Base strategy classes and simple default strategies
├── config.py       # Load strategy configuration from JSON/YAML files
├── simulate.py     # Utility for running multiple games and collecting stats
├── history.py      # SQLite game history logger with configurable batching
└── optimization/   # Helpers to tune strategy parameters via simulations
```

### Strategies

Every player owns a strategy object. Strategies decide what the player says, how they vote,
and (for special roles) whom they check or kill.  The framework accepts any user‑defined
strategy implementing the following methods:

* `speak(player, game) -> SpeechAction`
* `vote(player, game, nominations) -> Optional[int]`
* `sheriff_check(player, game, candidates)` *(sheriff only)*
* `mafia_kill(player, game, candidates)` *(mafia and don)*
* `don_check(player, game, candidates)` *(don only)*

`game` exposes the full history of previous rounds so strategies can base their decisions on
past events.  It also emits a callback whenever a new speech is recorded.  Strategies that
define ``on_speech(day_no, index, speech)`` will receive these events and can update their
internal state only when new information appears instead of rescanning the entire history.
This event‑driven approach is used by the "SingleSheriff" strategies to efficiently track
sheriff claims.

The repository includes simple example strategies:

* **CivilianStrategy** – randomly nominates and votes.
* **SheriffStrategy** – performs random checks and, upon finding a mafia member, claims
  to be the sheriff and nominates the discovered mafia.
* **MafiaStrategy** – attempts to nominate civilians and cooperates with the don to kill
  discovered sheriffs at night.
* **DonStrategy** – in addition to mafia behaviour, checks for the sheriff at night and
  shares the information with fellow mafia members.
* **SingleSheriff strategies** – a coordinated set where civilians trust the first
  sheriff claimant. Once the sheriff reveals himself, civilians mirror his
  nominations and votes (unless they are the nominated target) while mafia
  focus on eliminating the sheriff and his confirmed allies. The civilian
  behaviour exposes a ``random_nomination_chance`` parameter allowing
  simulations to tune how often unaided civilians nominate at random, and the
  mafia and don variants accept ``nomination_prob`` to control how frequently
  they nominate civilians during the day.

## Running a Simulation

Use the helper script to run a batch of games and display win statistics. A
progress bar from `tqdm` keeps track of the simulation progress so longer
runs can be monitored easily:

```bash
python -m mafia.simulate 100
```

The number (`100` in the example) specifies how many games to simulate.

### Using a configuration file

Strategies and their parameters can be described in a JSON **or YAML** file.
Each role is mapped to a strategy class name and optional constructor
arguments. For example in JSON. Sample YAML configurations are available
in the ``example_configs`` directory:

```json
{
  "CIVILIAN": {"strategy": "CivilianStrategy", "params": {"nomination_prob": 0.2}},
  "SHERIFF": {"strategy": "SheriffStrategy", "params": {"reveal_prob": 0.8}},
  "MAFIA": {"strategy": "MafiaStrategy", "params": {"nomination_prob": 0.3}},
  "DON": {"strategy": "DonStrategy", "params": {"nomination_prob": 0.3}}
}
```

Run simulations with the configuration via:

```bash
python -m mafia.simulate 100 --config config.json  # or config.yaml
```

The same configuration can be loaded programmatically with
``mafia.config.load_config`` and passed to ``simulate_games``.  Strategy
classes are located by name at runtime, so adding a new strategy class to
``mafia.strategies`` automatically makes it available to configuration files
without further changes.

## Persisting Game Histories

The `mafia.history` module records entire games to an SQLite database.  To
reduce disk overhead, game inserts are buffered and committed in batches.  The
batch size is configurable via ``GameHistoryDB(batch_size=n)``; higher values
offer better performance but risk losing the most recent games if the process
terminates before the buffer is flushed:

```python
from mafia.history import GameHistoryDB
db = GameHistoryDB(batch_size=10)  # commit after every 10 games
```

Closing the database connection flushes any remaining buffered games.

### Parameter Optimisation

The ``mafia.optimization`` package offers helpers for tuning strategy
parameters. It runs batches of simulations and applies a simple
hill-climbing search to discover parameter values that increase the win
rate for a chosen role. Multiple parameters per role can be tuned in a
single run. A `tqdm` progress bar reports how many optimisation steps have
been completed. Optimisations can be launched from the command line using a
configuration file:

```bash
python -m mafia.optimization example_configs/optimization.yaml
```

Additional scenarios include optimising a single parameter
(`example_configs/optimization_civilian.yaml`) or all parameters of a single
role (`example_configs/optimization_sheriff.yaml`).

See ``mafia/optimization/README.md`` for more details on the configuration
format and further examples.

---
This framework is intentionally lightweight; its main purpose is to provide a base for
experimenting with more sophisticated strategies or for teaching the fundamentals of the
sports mafia game.
