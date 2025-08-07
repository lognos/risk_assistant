# Monte Carlo Engine Documentation

## Overview
The Monte Carlo engine simulates project cost evolution over time, tracking the impact of mitigation actions and emerging risks. It supports both independent sampling (Phase 1) and category-based correlation (Phase 2).

## Key Features

### Statistical Modeling
- **Lognormal distributions** for cost and impact modeling
- Calculation of distribution parameters from P10/P90 percentiles
- Proper handling of risk probabilities

### Correlation Support
- **Phase 1**: Independent sampling (no correlation)
- **Phase 2**: Category-based correlation
  - Same owner: 0.3 correlation
  - Same discipline: 0.4 correlation
  - Same phase: 0.2 correlation
  - Same location: 0.5 correlation
  - Risk categories have specific correlations (e.g., weather: 0.7)

### Time-Based Evolution
- Weekly checkpoints for tracking changes
- Event-driven updates (only re-runs when changes occur)
- Tracks both mitigation impacts and new risk impacts

## Usage Example

```python
import pandas as pd
from datetime import datetime
from app.montecarlo import MonteCarloEngine, SimulationConfig

# Configure simulation
config = SimulationConfig(
    data_date=datetime.now(),
    n_simulations=5000,
    enable_correlation=True,  # Enable Phase 2 correlation
    correlation_method="category"
)

# Create engine
engine = MonteCarloEngine(config)

# Load your data into DataFrames
capex_items = pd.DataFrame({...})    # See data format in montecarlo_engine_method.md
capex_actions = pd.DataFrame({...})
risks = pd.DataFrame({...})
risk_actions = pd.DataFrame({...})

# Run simulation
results = engine.simulate_cost_evolution(
    capex_items=capex_items,
    capex_actions=capex_actions,
    risks=risks,
    risk_actions=risk_actions,
    data_date=datetime.now()
)

# Access results
if results is not None:
    print(results[['date', 'p20', 'p50', 'p80', 'deterministic']])
```

## Data Requirements

### For Correlation (Phase 2)
Add these optional fields to enable category-based correlation:

**CAPEX Items:**
- `item_owner`: Owner name
- `discipline`: Technical discipline (e.g., "Mechanical", "Civil", "IT")
- `phase`: Project phase (e.g., "Phase 1", "Phase 2")
- `location`: Physical location

**Risks:**
- `risk_owner`: Owner name
- `risk_category`: Category (e.g., "regulatory", "weather", "supply_chain", "technical", "financial")

## Output Format

The engine returns a DataFrame with:
- `date`: Checkpoint date
- `p20`, `p50`, `p80`: Cost percentiles
- `deterministic`: Deterministic estimate
- `mitigation_impacts`: List tracking mitigation effects
- `risk_impacts`: List tracking new risk effects

## Architecture

```
montecarlo/
├── mc_engine.py         # Main simulation engine
├── mc_distributions.py  # Statistical distributions
├── mc_correlations.py   # Correlation handling
├── mc_models.py        # Pydantic data models
├── mc_utils.py         # Utility functions
└── mc_validators.py    # Input validation
```

## Future Enhancements (Planned)

### Phase 3: User-Defined Dependencies
- Explicit dependency specification
- Strength levels (weak, moderate, strong)

### Phase 4: Historical Correlation Learning
- Learn correlations from past project data
- Automated pattern recognition

### Phase 5: Dynamic Correlation
- Adjust correlations based on project conditions
- Real-time correlation updates

## Validation and Error Handling

The engine includes comprehensive validation:
- Input data structure validation
- Value range validation (P10 < ML < P90)
- Probability range validation [0, 1]
- Correlation matrix positive semi-definite check
- Detailed error logging

## Performance Considerations

- Vectorized NumPy operations for efficiency
- Lazy evaluation (only re-runs when needed)
- Correlation matrix caching
- Typical performance: ~1-2 seconds for 5000 iterations with 50 items/risks

## Dependencies

- numpy >= 1.24.0
- pandas >= 2.0.0
- scipy >= 1.10.0
- pydantic >= 2.5.0
