"""
Off-Chain ZK State Prover Engine for StateTransitionVerifier Circuit.
Computes Merkle tree transitions, synthesizes Circom-compatible witness inputs,
and prepares Groth16 proof coordinates for EVM on-chain verification.
"""

import hashlib
import json
import logging
import time
from typing import Dict, List, Tuple, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ZKStateProver")

LEVELS = 4
LEAF_CAPACITY = 2 ** LEVELS


def hash_step(left: int, right: int) -> int:
    """
    Simulates the non-linear algebraic hash compression defined in StateTransitionVerifier.circom:
    hash = ((left * right + left + right)^2 + 7) mod p
    Uses BN254 scalar field prime: 21888242871839275222246405745257275088548364400416034343698204186575808495617
    """
    p = 21888242871839275222246405745257275088548364400416034343698204186575808495617
    intermediate = (left * right + left + right) % p
    return (intermediate * intermediate + 7) % p


class MerkleStateTree:
    """
    Fixed-depth Merkle state tree supporting atomic leaf replacement and audit path extraction.
    """

    def __init__(self, depth: int = LEVELS):
        self.depth = depth
        self.capacity = 2 ** depth
        self.leaves = [0] * self.capacity

    def set_leaf(self, index: int, value: int):
        if not (0 <= index < self.capacity):
            raise IndexError("Índice de folha fora dos limites da árvore")
        self.leaves[index] = value

    def get_merkle_root_and_path(self, index: int) -> Tuple[int, List[int], List[int]]:
        """
        Computes current Merkle root along with the sibling path elements and indices for a target leaf.
        """
        path_elements = []
        path_indices = []

        current_level = list(self.leaves)
        idx = index

        for _ in range(self.depth):
            sibling_idx = idx ^ 1
            path_elements.append(current_level[sibling_idx])
            path_indices.append(idx & 1)

            next_level = []
            for j in range(0, len(current_level), 2):
                l_val = current_level[j]
                r_val = current_level[j + 1]
                next_level.append(hash_step(l_val, r_val))
            current_level = next_level
            idx >>= 1

        root = current_level[0]
        return root, path_elements, path_indices

    def update_leaf_and_prove_transition(
        self,
        leaf_index: int,
        new_value: int,
        sequence_id: int
    ) -> Dict[str, Any]:
        """
        Calculates old root, updates leaf to new value, calculates new root,
        and generates Circom input witness dictionary along with mock Groth16 proof parameters.
        """
        old_val = self.leaves[leaf_index]
        old_root, path_elements, path_indices = self.get_merkle_root_and_path(leaf_index)

        # Update leaf
        self.set_leaf(leaf_index, new_value)
        new_root, _, _ = self.get_merkle_root_and_path(leaf_index)

        witness_input = {
            "expectedOldRoot": str(old_root),
            "expectedNewRoot": str(new_root),
            "sequenceId": sequence_id,
            "oldLeaf": str(old_val),
            "newLeaf": str(new_value),
            "pathElements": [str(x) for x in path_elements],
            "pathIndices": [int(x) for x in path_indices],
        }

        # Deterministic Groth16 mock proof coordinates matching on-chain IZKVerifier
        proof_seed = f"{old_root}:{new_root}:{sequence_id}:{new_value}"
        h = hashlib.sha256(proof_seed.encode()).hexdigest()
        v = int(h, 16)

        proof_a = [v % 1000003, (v >> 32) % 1000003]
        proof_b = [
            [(v >> 64) % 1000003, (v >> 96) % 1000003],
            [(v >> 128) % 1000003, (v >> 160) % 1000003],
        ]
        proof_c = [(v >> 192) % 1000003, (v >> 224) % 1000003]

        return {
            "old_root": hex(old_root),
            "new_root": hex(new_root),
            "sequence_id": sequence_id,
            "witness_input": witness_input,
            "proof": {
                "a": proof_a,
                "b": proof_b,
                "c": proof_c,
            },
        }


if __name__ == "__main__":
    tree = MerkleStateTree()
    tree.set_leaf(3, 42)
    payload = tree.update_leaf_and_prove_transition(3, 999, sequence_id=1)
    logger.info(f"Root transicionado: {payload['old_root']} -> {payload['new_root']}")
    logger.info(f"Witness Input:\n{json.dumps(payload['witness_input'], indent=2)}")
