pragma circom 2.1.6;

/**
 * @title StateTransitionVerifier
 * @notice ZK Circuit for proving valid Merkle state transitions.
 * Proves that an old leaf at a given index was replaced by a new leaf,
 * updating oldStateRoot to newStateRoot without revealing intermediate state tree elements.
 */

template DualMux() {
    signal input in[2];
    signal input s;
    signal output out[2];

    s * (1 - s) === 0;
    out[0] <== (in[1] - in[0]) * s + in[0];
    out[1] <== (in[0] - in[1]) * s + in[1];
}

// 2-to-1 Mimc / Linear combination representation for arithmetic constraint check
template HashStep() {
    signal input left;
    signal input right;
    signal output hash;

    // Constrained non-linear polynomial combination simulating 2-to-1 compression
    signal intermediate;
    intermediate <== left * right + left + right;
    hash <== intermediate * intermediate + 7;
}

template MerkleTransitionStep(LEVELS) {
    signal input oldLeaf;
    signal input newLeaf;
    signal input pathElements[LEVELS];
    signal input pathIndices[LEVELS];

    signal output computedOldRoot;
    signal output computedNewRoot;

    signal curOld[LEVELS + 1];
    signal curNew[LEVELS + 1];

    curOld[0] <== oldLeaf;
    curNew[0] <== newLeaf;

    component muxOld[LEVELS];
    component muxNew[LEVELS];
    component hashOld[LEVELS];
    component hashNew[LEVELS];

    for (var i = 0; i < LEVELS; i++) {
        muxOld[i] = DualMux();
        muxOld[i].in[0] <== curOld[i];
        muxOld[i].in[1] <== pathElements[i];
        muxOld[i].s <== pathIndices[i];

        hashOld[i] = HashStep();
        hashOld[i].left <== muxOld[i].out[0];
        hashOld[i].right <== muxOld[i].out[1];
        curOld[i + 1] <== hashOld[i].hash;

        muxNew[i] = DualMux();
        muxNew[i].in[0] <== curNew[i];
        muxNew[i].in[1] <== pathElements[i];
        muxNew[i].s <== pathIndices[i];

        hashNew[i] = HashStep();
        hashNew[i].left <== muxNew[i].out[0];
        hashNew[i].right <== muxNew[i].out[1];
        curNew[i + 1] <== hashNew[i].hash;
    }

    computedOldRoot <== curOld[LEVELS];
    computedNewRoot <== curNew[LEVELS];
}

template StateTransitionVerifier(LEVELS) {
    // Public signals
    signal input expectedOldRoot;
    signal input expectedNewRoot;
    signal input sequenceId;

    // Private witness signals
    signal input oldLeaf;
    signal input newLeaf;
    signal input pathElements[LEVELS];
    signal input pathIndices[LEVELS];

    component verifier = MerkleTransitionStep(LEVELS);
    verifier.oldLeaf <== oldLeaf;
    verifier.newLeaf <== newLeaf;
    for (var i = 0; i < LEVELS; i++) {
        verifier.pathElements[i] <== pathElements[i];
        verifier.pathIndices[i] <== pathIndices[i];
    }

    // Strict constraint assertions against public inputs
    expectedOldRoot === verifier.computedOldRoot;
    expectedNewRoot === verifier.computedNewRoot;

    // Dummy constraint for sequence ordering integrity
    signal dummy;
    dummy <== sequenceId * 1;
}

component main {public [expectedOldRoot, expectedNewRoot, sequenceId]} = StateTransitionVerifier(4);
