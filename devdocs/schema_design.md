# Schema Design

AVIS strictly types all internal data passing between pipeline stages. The core schema is the `EvidenceGraph`, built using Pydantic, which transforms raw machine learning detections into explainable geometric and semantic relationships.

## 1. The Evidence Graph Data Model

The `EvidenceGraph` is not a flat list of objects; it is a typed graph.

### Nodes

Every physical entity detected in the image is represented as a node. Nodes contain their spatial bounds (`BBox`) and ML confidence score.

- **`Vehicle`**: Represents cars, motorcycles, trucks, buses, or bicycles. Stores a `type`, `bbox`, and `confidence`. Also tracks which calibration zones it sits inside (`in_zones`).
- **`Person`**: Represents humans. Includes a `role` enum (`rider`, `driver`, `pedestrian`). Can carry attribute scores (e.g., `helmet: bool`, `seatbelt: bool`).
- **`Light`**: A traffic light. Tracks its `state` (`red`, `amber`, `green`, `unknown`).
- **`Plate`**: A cropped license plate. Tracks `text` (OCR output) and `regex_ok` (whether it matches standard Indian plate formats).
- **`Zone`**: A geometric area derived from the camera calibration file. Can be a `stop_line`, `no_parking`, or `lane` zone. Defined by a `polygon`.

### Edges

Edges define the relationships between nodes. A violation is essentially a small subgraph.

- **`rides`**: `Person` → `Vehicle:motorcycle`. Links a rider to a bike. Used for helmet and triple-riding rules.
- **`drives`**: `Person` → `Vehicle:car`. Links a driver to a car. Used for seatbelt rules.
- **`has_plate`**: `Vehicle` → `Plate`. Links OCR text to a specific vehicle.
- **`located_in`**: `Vehicle` → `Zone`. Determines if a vehicle has breached a calibration polygon.
- **`governed_by`**: `Vehicle` → `Light`. Links a vehicle to the specific traffic light dictating its allowed movement.

## 2. Violation Representation

When the Rule Engine identifies a violation subgraph, it generates structured records.

### `Candidate`

An intermediate object representing a potential violation before routing or VLM verification.
- `type`: E.g., `TRIPLE_RIDING`.
- `tier`: The evidence sufficiency tier (`A`, `B`, `C`, `D`).
- `subjects`: A list of node IDs involved in the violation (e.g., `["motorcycle_1", "rider_1", "rider_2", "rider_3"]`).
- `rule_score`: Mathematical confidence of the rule logic.

### `Violation`

The final output payload, destined for the database and e-challan generation.
- Inherits the `Candidate` data but adds the final ruling:
- `evidence_sufficiency`: `sufficient`, `candidate`, or `insufficient`.
- `scores`: A fused object containing `detection`, `rule`, `vlm`, and `fused` scores.
- `route`: How the decision was made (`auto_confirmed`, `vlm_confirmed`, `human_review`).
- `reason`: A human-readable, single-sentence justification.
- `legal`: A dictionary containing the `act`, `section`, and `fine` amount.
- `evidence_hash`: A SHA-256 hash of the original image to prove no tampering occurred.

## 3. Database Schema (PostgreSQL)

Because the `EvidenceGraph` is highly variable and deeply nested, AVIS does not use a strict relational schema for detections. Instead, it utilizes **JSONB columns** in PostgreSQL via SQLModel.

This provides:
1. **Relational Integrity**: Metadata (timestamp, camera ID, status) is stored in standard relational columns for fast indexing and queue management.
2. **Flexible Storage**: The entire `EvidenceGraph` and the resulting `Violation` JSON are dumped into a JSONB column. This allows querying the database for specific graph conditions using Postgres JSON operators while allowing the schema to evolve without heavy migrations.
