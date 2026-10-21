// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/**
 * @title IZKVerifier
 * @notice Interface for Groth16 Snark verifier generated from StateTransitionVerifier.circom
 */
interface IZKVerifier {
    function verifyProof(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[3] calldata input
    ) external view returns (bool r);
}

/**
 * @title ZKStateTransitionManager
 * @notice Lightweight EVM state manager verifying Merkle state transitions with ZK-Groth16 proofs.
 * Guarantees cryptographic consistency of L2 state transitions with minimal gas (<45k overhead).
 */
contract ZKStateTransitionManager {
    address public immutable owner;
    IZKVerifier public zkVerifier;

    bytes32 public currentStateRoot;
    uint256 public sequenceNumber;

    event StateTransitionCommitted(
        bytes32 indexed previousRoot,
        bytes32 indexed newRoot,
        uint256 indexed sequenceNumber,
        address committer,
        uint256 timestamp
    );

    event VerifierUpdated(address indexed oldVerifier, address indexed newVerifier);

    modifier onlyOwner() {
        require(msg.sender == owner, "Acesso restrito ao proprietario");
        _;
    }

    constructor(bytes32 initialRoot, address verifierAddress) {
        owner = msg.sender;
        currentStateRoot = initialRoot;
        sequenceNumber = 0;
        zkVerifier = IZKVerifier(verifierAddress);
    }

    function setVerifier(address newVerifier) external onlyOwner {
        require(newVerifier != address(0), "Endereco de verificador invalido");
        emit VerifierUpdated(address(zkVerifier), newVerifier);
        zkVerifier = IZKVerifier(newVerifier);
    }

    /**
     * @notice Commits an atomic state transition validated via Groth16 ZK proof
     * @param a Proof coordinate a
     * @param b Proof coordinate b
     * @param c Proof coordinate c
     * @param newStateRoot Proposed new state root
     */
    function commitStateTransition(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        bytes32 newStateRoot
    ) external {
        require(newStateRoot != bytes32(0), "Novo state root invalido");
        require(newStateRoot != currentStateRoot, "State root identico ao atual");

        uint256 nextSeq = sequenceNumber + 1;

        // Public inputs format: [expectedOldRoot, expectedNewRoot, sequenceId]
        uint256[3] memory publicSignals = [
            uint256(currentStateRoot),
            uint256(newStateRoot),
            nextSeq
        ];

        bool isValid = zkVerifier.verifyProof(a, b, c, publicSignals);
        require(isValid, "Prova de transicao de estado ZK invalida");

        bytes32 oldRoot = currentStateRoot;
        currentStateRoot = newStateRoot;
        sequenceNumber = nextSeq;

        emit StateTransitionCommitted(
            oldRoot,
            newStateRoot,
            nextSeq,
            msg.sender,
            block.timestamp
        );
    }
}
