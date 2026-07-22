# Crew Calls Workflow - SceneIQ Production Schedule

## What Are Crew Calls?

Crew Calls are per-department call times for each shoot day. They tell each department when to report to set, and optionally when they wrap. They appear in the Crew Calls section of generated call sheets.

## Data Structure

Each crew call entry has four fields:

- department (required) - e.g. "Camera", "Lighting", "Hair/MU"
- name (optional) - e.g. "John Smith, DP"
- call_time (required) - e.g. "05:30 AM"
- wrap_time (optional) - e.g. "07:30 PM"

## How to Set Crew Calls

### Via API

PATCH a shoot day with a crew_calls array:

    PATCH /api/0.1.0/production-schedule/{productionId}/shoot-days/{shootDayId}

    Body:
    {
      "crew_calls": [
        { "department": "Camera",    "name": "John Smith, DP",  "call_time": "05:30 AM" },
        { "department": "Lighting",  "name": "Jane Doe, Gaffer","call_time": "05:00 AM" },
        { "department": "Sound",     "name": "Mike R, Mixer",   "call_time": "06:00 AM" },
        { "department": "Hair/MU",   "name": "Sarah L",         "call_time": "04:30 AM" },
        { "department": "Catering",  "name": "Chicago Catering","call_time": "05:00 AM" },
        { "department": "Transport", "name": "Driver Pool",     "call_time": "04:00 AM" }
      ]
    }

### Via Stripboard UI

Edit a shoot day in the stripboard view. The Crew Calls section appears in the edit form. Add rows for each department with their call time.

## How Crew Calls Flow Into Call Sheets

1. Crew calls stored on ShootDay.crewCalls (JSON column in database)
2. Call sheet requested: GET /production-schedule/{id}/call-sheet/{dayNumber}
3. System loads shoot day, passes crew_calls to call sheet generator
4. Generator renders them in the Crew Calls table (JSON or PDF output)

## Key Rules

- FULL REPLACEMENT: sending crew_calls in a PATCH replaces the entire list
- Omitting crew_calls (null) leaves existing values unchanged
- Departments like Hair/MU and Transport typically call 1-2 hours before general crew call
- The general call time on the shoot day (call_time field) is the baseline
- Crew calls are department-specific overrides of that baseline

## Integration with Crew Intelligence Engine

The Crew Intelligence Engine (POST /productions/{id}/crew/analyze) uses the shoot day callTime (general call) to calculate turnaround between consecutive days. It does NOT currently read individual department crew calls. Future enhancement: per-department turnaround checking.

## Example: Midnight Harbour Day 1

General Call: 06:00 AM

Department Crew Calls:
  Transport      04:00 AM  (2hr early - vehicle staging)
  Hair/Makeup    04:30 AM  (1.5hr early - lead actor prep)
  Catering       05:00 AM  (1hr early - breakfast setup)
  Lighting       05:00 AM  (1hr early - pre-rig)
  Camera         05:30 AM  (30min early - camera prep)
  Sound          06:00 AM  (general call)
  Background     07:00 AM  (1hr after call - later scenes)
