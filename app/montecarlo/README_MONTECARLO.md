# Monte Carlo Engine Documentation

## Overview
The Monte Carlo engine simulates project cost evolution over time, tracking the impact of mitigation actions and emerging risks. It supports both independent sampling and advanced category-based correlation using a normalized database structure with lookup tables.

## Key Features

### Statistical Modeling
- **Lognormal distributions** for cost and impact modeling
- Calculation of distribution parameters from P10/P90 percentiles
- Proper handling of risk probabilities

### Advanced Correlation System
The engine uses a sophisticated correlation system based on normalized lookup table relationships:

**Correlation Rules:**
1. **Same Owner**: 0.5 correlation
2. **Same Discipline**: 0.4 correlation  
3. **Same Phase**: 0.3 correlation
4. **Adjacent Phases**: 0.2 correlation (based on phase_order)
5. **Same Location**: 0.3 correlation
6. **Parent-Child Locations**: 0.2 correlation
7. **Same Risk Category**: 0.4 correlation
8. **Same Risk Log**: 0.2 correlation

### Time-Based Evolution
- Weekly checkpoints for tracking changes
- Event-driven updates (only re-runs when changes occur)
- Tracks both mitigation impacts and new risk impacts

## Database Schema (Normalized Structure)

### Lookup Tables

The engine uses the following normalized lookup tables for robust correlation modeling:

1. **disciplines** - Engineering disciplines (Civil, Mechanical, Electrical, etc.)
2. **project_phases** - Project phases with ordering (Conceptual, FEED, Detailed Design, etc.) 
3. **locations** - Hierarchical locations (Site, Units, Buildings)
4. **risk_categories** - Risk categories (Technical, Commercial, Schedule, etc.)
5. **risk_logs** - Risk register logs (Project Risk Register, Technical Risk Log, etc.)

### Foreign Key Columns

Each main table has foreign key references:
- `discipline_id` → disciplines.discipline_id
- `phase_id` → project_phases.phase_id  
- `location_id` → locations.location_id
- `risk_category_id` → risk_categories.risk_category_id (risks table only)
- `risk_log_id` → risk_logs.risk_log_id (risks table only)

### Performance Optimization

- Individual attribute indexes for fast lookups
- Composite indexes for multi-attribute correlation queries
- Optimized correlation matrix caching

## Usage Examples

### Basic Simulation
```python
from app.montecarlo import MonteCarloEngine
from datetime import datetime

engine = MonteCarloEngine()
result = engine.simulate_cost_evolution(
    data_date=datetime(2024, 1, 1),
    n_simulations=1000,
    enable_correlation=True
)

# Access time series results
time_series = result.time_series  # DataFrame with P10, P50, P90 by date
summary = result.summary_statistics  # Final statistics
```

### Advanced Configuration
```python
from app.montecarlo import SimulationConfig

config = SimulationConfig(
    data_date=datetime(2024, 1, 1),
    frequency="M",  # Monthly simulation
    periods=24,     # 24 months
    n_simulations=10000,
    enable_correlation=True,
    correlation_method="category"  # Uses normalized lookup relationships
)

result = engine.simulate_cost_evolution(config)

# Access correlation information
correlation_info = result.correlation_info
print(f"Total correlated pairs: {correlation_info['total_pairs']}")
print(f"Average correlation: {correlation_info['avg_correlation']:.3f}")
```

### Direct Usage Example
```python
import pandas as pd
from datetime import datetime
from app.montecarlo import MonteCarloEngine, SimulationConfig

# Configure simulation
config = SimulationConfig(
    data_date=datetime.now(),
    n_simulations=5000,
    enable_correlation=True,
    correlation_method="category"
)

# Create engine
engine = MonteCarloEngine(config)

# Load your data into DataFrames
capex_items = pd.DataFrame({...})    # See data format below
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

## Data Models

All Pydantic models support the normalized database structure:

```python
class CapexItem(BaseModel):
    item_id: int
    name: str
    owner: str
    p10_cost: float
    p90_cost: float
    base_date: datetime
    # Normalized foreign keys
    discipline_id: Optional[int] = None
    phase_id: Optional[int] = None  
    location_id: Optional[int] = None
```

## Data Requirements

### Required Fields
- All monetary values in consistent currency
- P10/P90 percentiles for cost distributions
- Probability values between 0 and 1 for risks
- Valid date formats

### Optional Fields for Enhanced Correlation
**CAPEX Items:**
- `discipline_id`: Foreign key to disciplines table
- `phase_id`: Foreign key to project_phases table
- `location_id`: Foreign key to locations table
- `item_owner`: Owner name (used for owner-based correlation)

**Risks:**
- `discipline_id`: Foreign key to disciplines table
- `phase_id`: Foreign key to project_phases table
- `location_id`: Foreign key to locations table
- `risk_category_id`: Foreign key to risk_categories table
- `risk_log_id`: Foreign key to risk_logs table
- `risk_owner`: Owner name (used for owner-based correlation)

## Lookup Table Management

### Adding New Lookup Data
```python
from app.database import get_supabase_client

supabase = get_supabase_client()

# Add new discipline
supabase.table('disciplines').insert({
    'discipline_name': 'Software Engineering',
    'description': 'Software and digital systems'
}).execute()

# Update entity with new discipline
supabase.table('capex_items').update({
    'discipline_id': discipline_id
}).eq('item_id', item_id).execute()
```

## Output Format

The engine returns a DataFrame with:
- `date`: Checkpoint date
- `p20`, `p50`, `p80`: Cost percentiles
- `deterministic`: Deterministic estimate
- `mitigation_impacts`: List tracking mitigation effects
- `risk_impacts`: List tracking new risk effects

## Architecture

```
app/montecarlo/
├── __init__.py              # Package exports
├── mc_engine.py             # Main simulation engine
├── mc_models.py             # Pydantic data models
├── mc_correlations.py       # Normalized correlation logic
├── mc_distributions.py      # Statistical distributions
├── mc_utils.py              # Utility functions
├── mc_validators.py         # Input validation
├── test_montecarlo.py       # Test suite
└── README_MONTECARLO.md     # This documentation
```

## Key Benefits

1. **Scalable Correlation**: Normalized structure supports complex relationships
2. **Data Integrity**: Foreign key constraints ensure consistency
3. **Performance**: Optimized indexes for fast correlation queries
4. **Maintainability**: Lookup tables easy to modify without touching main data
5. **Flexibility**: Hierarchical structures (locations, phases) for advanced correlation
6. **Transparency**: Detailed correlation reporting for audit trails

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

## Testing

Run comprehensive tests:
```bash
python app/montecarlo/test_montecarlo.py
```

Tests cover:
- Database connectivity
- Correlation matrix generation
- Simulation accuracy
- Performance benchmarks
- Data validation

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

## Current Status

✅ **Production Ready**: The Monte Carlo engine is fully operational with normalized database structure
✅ **Lookup Tables**: All correlation lookup tables are in place and populated
✅ **Foreign Keys**: Foreign key columns exist in main tables for correlation modeling
✅ **Correlation Engine**: Python-based correlation system works with existing data structure
✅ **Performance**: Optimized for production workloads

The Monte Carlo engine is ready for production use with advanced correlation modeling capabilities!
