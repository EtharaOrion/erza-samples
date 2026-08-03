"""Resolution of a published differential signal bias onto an arbitrary
observable pair, and the slant-to-vertical reduction that consumes it.

The bias tables are the per-label TSV extracts of the CAS/IGG multi-GNSS DCB
product (Bias-SINEX 1.00).  A row carries BD(obs1, obs2) = B(obs1) - B(obs2)
in nanoseconds, per Bias-SINEX 1.00 section 6.3.1 equation (7).
"""
import os

# Bias-SINEX 1.00, section 6.3.3: GPS C1W / C2W are the reference observables.
REFERENCE_OBSERVABLES = ("C1W", "C2W")


def load_table(path):
    """Read one TSV extract into {(obs1, obs2): value_ns}."""
    rows = {}
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if parts[0] == "obs1":
                continue
            rows[(parts[0], parts[1])] = float(parts[2])
    return rows


def load_label(directory, kind, label):
    return load_table(os.path.join(directory, "dsb_%s_%s.tsv" % (kind, label)))


def _shortest_chains(rows, start, end):
    """All shortest observable chains from start to end over the rows present."""
    nodes = set()
    for obs1, obs2 in rows:
        nodes.add(obs1)
        nodes.add(obs2)
    if start not in nodes or end not in nodes:
        return []
    adjacency = {n: set() for n in nodes}
    for obs1, obs2 in rows:
        adjacency[obs1].add(obs2)
        adjacency[obs2].add(obs1)
    frontier = [[start]]
    seen = {start: 0}
    found, depth = [], None
    while frontier:
        nxt = []
        for path in frontier:
            for neighbour in sorted(adjacency[path[-1]]):
                if neighbour in path:
                    continue
                extended = path + [neighbour]
                if neighbour == end:
                    if depth is None or len(extended) == depth:
                        depth = len(extended)
                        found.append(extended)
                    continue
                if depth is not None:
                    continue
                if seen.get(neighbour, 10 ** 6) < len(extended):
                    continue
                seen[neighbour] = len(extended)
                nxt.append(extended)
        if depth is not None:
            break
        frontier = nxt
    return found


def _chain_value(rows, chain):
    total = 0.0
    for left, right in zip(chain, chain[1:]):
        if (left, right) in rows:
            total += rows[(left, right)]
        else:
            total -= rows[(right, left)]
    return total


def resolve(rows, obs1, obs2, reference=REFERENCE_OBSERVABLES):
    """BD(obs1, obs2) in nanoseconds for the entries in `rows`.

    Precedence, highest first:
      1. the row whose ordered pair is exactly (obs1, obs2)  -> as published;
      2. the row whose ordered pair is the reverse           -> negated;
      3. the pair is absent: the signed sum along the shortest chain of rows
         that links the two observables; where several chains are equally
         short, the one whose intermediate observables are the constellation's
         reference observables.
    """
    if (obs1, obs2) in rows:
        return rows[(obs1, obs2)]
    if (obs2, obs1) in rows:
        return -rows[(obs2, obs1)]
    chains = _shortest_chains(rows, obs1, obs2)
    if not chains:
        raise KeyError("no chain links %s to %s" % (obs1, obs2))
    chains.sort(key=lambda c: (sum(1 for n in c[1:-1] if n not in reference), c))
    return _chain_value(rows, chains[0])


def chain_count(rows, obs1, obs2):
    """How many equally short chains exist (build-time uniqueness check)."""
    if (obs1, obs2) in rows or (obs2, obs1) in rows:
        return 0
    return len(_shortest_chains(rows, obs1, obs2))
