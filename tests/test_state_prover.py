"""
Unit Test Suite for ZK State Prover and Merkle State Transition Engine.
Validates leaf updates, cryptographic path consistency, and witness artifact generation.
"""

import sys
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

try:
    from deliverables.dorahacks_zk_state_prover.scripts.state_prover import (
        MerkleStateTree,
        hash_step,
        LEVELS,
        LEAF_CAPACITY,
    )
except ImportError:
    from scripts.state_prover import (
        MerkleStateTree,
        hash_step,
        LEVELS,
        LEAF_CAPACITY,
    )


def test_hash_step_determinism():
    h1 = hash_step(12345, 67890)
    h2 = hash_step(12345, 67890)
    assert h1 == h2
    assert h1 > 0


def test_merkle_state_tree_leaf_and_path():
    tree = MerkleStateTree(depth=LEVELS)

    # Initial zero root
    root_0, path_elems_0, path_indices_0 = tree.get_merkle_root_and_path(0)
    assert len(path_elems_0) == LEVELS
    assert len(path_indices_0) == LEVELS

    # Set leaf at index 2
    tree.set_leaf(2, 555)
    root_1, path_elems_1, path_indices_1 = tree.get_merkle_root_and_path(2)
    assert root_1 != root_0

    # Path indices for index 2 (binary 0010): [0, 1, 0, 0]
    assert path_indices_1[0] == 0
    assert path_indices_1[1] == 1


def test_state_transition_proof_generation():
    tree = MerkleStateTree(depth=LEVELS)
    target_idx = 5
    old_value = 100
    new_value = 500

    tree.set_leaf(target_idx, old_value)

    res = tree.update_leaf_and_prove_transition(
        leaf_index=target_idx,
        new_value=new_value,
        sequence_id=1
    )

    assert "old_root" in res
    assert "new_root" in res
    assert res["old_root"] != res["new_root"]

    witness = res["witness_input"]
    assert witness["oldLeaf"] == str(old_value)
    assert witness["newLeaf"] == str(new_value)
    assert witness["sequenceId"] == 1
    assert len(witness["pathElements"]) == LEVELS
    assert len(witness["pathIndices"]) == LEVELS

    proof = res["proof"]
    assert len(proof["a"]) == 2
    assert len(proof["b"]) == 2
    assert len(proof["c"]) == 2


def test_out_of_bounds_leaf_rejection():
    tree = MerkleStateTree(depth=LEVELS)
    with pytest.raises(IndexError):
        tree.set_leaf(LEAF_CAPACITY + 1, 999)


if __name__ == "__main__":
    test_hash_step_determinism()
    test_merkle_state_tree_leaf_and_path()
    test_state_transition_proof_generation()
    test_out_of_bounds_leaf_rejection()
    print("Todos os testes unitários do ZK State Prover foram aprovados com 100% de sucesso!")
