# MMB (Movie Magic Budgeting) Integration

This document describes the MMB file parser integration for SceneIQ.

## Overview

The MMB parser allows users to upload Movie Magic Budgeting files (.mmbx and .csv formats) and automatically:
- Extract production details and budget data
- Calculate eligible expenses based on jurisdiction rules
- Estimate tax credits
- Identify optimization opportunities

## Features

### Supported File Formats
- `.mmbx` - Movie Magic Budgeting XML format
- `.csv` - CSV export from budgeting software

### Parser Capabilities
1. **Production Information Extraction**
   - Title, producer, director
   - Shoot dates and schedule details

2. **Budget Analysis**
   - Total budget breakdown
   - Above-the-line vs. below-the-line expenses
   - Post-production costs
   - Line-item level detail

3. **Jurisdiction-Specific Calculations**
   - Eligible expense filtering
   - Tax credit rate application
   - Special incentive rules (e.g., music scoring uplift)

## API Usage

### Upload Endpoint

**POST** `/api/v1/mmb/upload`

**Parameters:**
- `file` (required): MMB file to upload (.mmbx or .csv)
- `jurisdiction` (optional): Jurisdiction code for calculations (default: "georgia")

**Example Response:**
```json
{
  "filename": "atlanta_heist.mmbx",
  "production": {
    "title": "Atlanta Heist",
    "producer": "Example Productions",
    "director": "Jane Filmmaker",
    "shoot_dates": {
      "start": "2024-06-01",
      "end": "2024-08-15",
      "days": 45
    }
  },
  "summary": {
    "total_budget": 2500000.0,
    "eligible_expenses": 3300000.0,
    "estimated_credit": 1320000.0,
    "credit_rate": "40%",
    "line_items_parsed": 44
  },
  "optimization_opportunities": [
    {
      "category": "Music Scoring",
      "current": 285000.0,
      "potential": 313500.0,
      "recommendation": "Move scoring to Atlanta for 10% uplift"
    }
  ]
}
```

## Testing

### Running Parser Tests

```bash
# Manual test script
python3 << 'TESTEOF'
import sys
sys.path.insert(0, '.')
from src.mmb_parser import MMBParser

parser = MMBParser("tests/fixtures/mmb_files/atlanta_heist.mmbx")
data = parser.parse()
print(f"Total Budget: ${data['summary']['total']:,.0f}")
TESTEOF
```

### Demo Data Loader

Load the sample Atlanta Heist budget into the database:

```bash
python3 scripts/load_demo_budget.py
```

## Sample Data

The repository includes a sample MMB file:
- `tests/fixtures/mmb_files/atlanta_heist.mmbx` - Feature film budget example

This file contains:
- $2.5M total budget
- 5 major categories (Above-the-Line, Below-the-Line, Post-Production, Fringes, Contingency)
- 44 line items across all categories
- Music scoring items to demonstrate Georgia's 10% uplift

## Implementation Details

### Module Structure

```
src/mmb_parser/
├── __init__.py
└── parser.py          # MMBParser class

src/api/v1/endpoints/
└── mmb.py            # API endpoints

tests/
├── fixtures/
│   └── mmb_files/
│       └── atlanta_heist.mmbx
└── test_mmb_parser.py

scripts/
└── load_demo_budget.py
```

### Jurisdiction Rules

The parser implements jurisdiction-specific eligibility rules. For Georgia:
- **Eligible Categories**: Below-the-Line, Post-Production
- **Special Rules**: Music scoring qualifies for additional 10% uplift
- **Base Credit Rate**: 30%
- **With Music Uplift**: 40%

## Future Enhancements

Potential improvements:
1. Support for Excel (.xlsx) format
2. Additional jurisdiction rule sets
3. Batch file processing
4. Export to various formats
5. Budget comparison tools
6. Real-time validation during upload

## Security

- CodeQL scan: 0 alerts
- No security vulnerabilities detected
- Temporary files are properly cleaned up after processing
