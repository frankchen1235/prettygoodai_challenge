# Pretty Good AI Voice Bot

Python voice-bot test harness for the Pretty Good AI engineering challenge. It calls the assessment phone line, simulates realistic patient conversations with OpenAI Realtime, saves both sides of each call as transcript/audio artifacts, and generates a bug report from the resulting conversations.

## What It Tests

The included scenarios cover the challenge categories:

- New patient appointment scheduling
- Appointment rescheduling
- Appointment cancellation
- Medication refill requests
- Office hours, locations, and insurance questions
- Edge cases with unclear requests

## Setup

Use Python 3.12. A local virtual environment is recommended:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Install the project in editable mode with development tools:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Alternatively, install directly from requirement files:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Create `.env` from `.env.example` and fill in Twilio/OpenAI credentials. The real `.env` is ignored by git:

```powershell
Copy-Item .env.example .env
```

Required runtime values:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TARGET_PHONE_NUMBER`
- `PUBLIC_BASE_URL`
- `OPENAI_API_KEY`

## Safety Guard

The bot is hard-guarded to call only:

```text
+18054398008
```

If `TARGET_PHONE_NUMBER` is missing or set to any other number, the CLI exits before making a call.

## Running Calls

Start the local FastAPI server:

```powershell
python -m pgaibot serve
```

Expose it with an HTTPS tunnel, then set `PUBLIC_BASE_URL` in `.env` to that tunnel URL.

Dry-run a scenario without calling Twilio:

```powershell
python -m pgaibot run --scenario scenarios/01_simple_schedule.yaml --dry-run
```

Run the scenario calls:

```powershell
python -m pgaibot run --scenario scenarios/01_simple_schedule.yaml
python -m pgaibot run --scenario scenarios/02_reschedule_appointment.yaml
python -m pgaibot run --scenario scenarios/03_cancel_appointment.yaml
python -m pgaibot run --scenario scenarios/04_medication_refill.yaml
python -m pgaibot run --scenario scenarios/05_office_hours_locations_insurance.yaml
python -m pgaibot run --scenario scenarios/06_unclear_request_edge_case.yaml
python -m pgaibot run --scenario scenarios/07_office_hours_locations_insurance_variant.yaml
python -m pgaibot run --scenario scenarios/08_unclear_request_edge_case_variant.yaml
```

Each run writes artifacts under:

```text
artifacts/calls/<run-id>/
```

Important files:

- `recording.mp3`: Twilio dual-channel call recording
- `realtime_transcript.txt`: both sides of the conversation
- `realtime_summary.json`: call duration, close reason, and event counts
- `run_context.json`: exact scenario and prompt used for the call
- `metadata.json`: Twilio call metadata

## Reports

Generate the bug/eval report:

```powershell
python -m pgaibot report
```

Outputs:

- `BUG_REPORT.md`
- `artifacts/eval_report.json`

The evaluator treats demo-patient record lookup failure as acceptable when the Pretty Good AI agent recognizes the request, gathers appropriate identity details, avoids unsafe action, and routes to support.

## Submitted Call Artifacts

The challenge asks for a minimum of 10 calls with both sides of each conversation, including MP3/OGG audio and transcripts. This repo includes 12 qualifying calls with both transcript and MP3 artifacts.

All calls were placed from the same Twilio caller number, as requested by the submission instructions. The scenario files intentionally use multiple simulated patient personas to cover different workflow categories. Because one caller ID is reused across personas, caller-ID based patient lookup behavior is treated as an observation in `BUG_REPORT.md`, not as a high-confidence agent bug.

Qualifying calls:

| Run ID | Duration | Transcript | Recording |
| --- | ---: | --- | --- |
| `simple_schedule_new_patient-20260901-191317-2b3139fe` | 130.9s | `artifacts/calls/simple_schedule_new_patient-20260901-191317-2b3139fe/realtime_transcript.txt` | `artifacts/calls/simple_schedule_new_patient-20260901-191317-2b3139fe/recording.mp3` |
| `simple_schedule_new_patient-20260901-194310-dd3397e4` | 153.2s | `artifacts/calls/simple_schedule_new_patient-20260901-194310-dd3397e4/realtime_transcript.txt` | `artifacts/calls/simple_schedule_new_patient-20260901-194310-dd3397e4/recording.mp3` |
| `reschedule_existing_appointment-20260901-200514-092406b1` | 153.2s | `artifacts/calls/reschedule_existing_appointment-20260901-200514-092406b1/realtime_transcript.txt` | `artifacts/calls/reschedule_existing_appointment-20260901-200514-092406b1/recording.mp3` |
| `reschedule_existing_appointment-20260903-004740-81d06475` | 153.2s | `artifacts/calls/reschedule_existing_appointment-20260903-004740-81d06475/realtime_transcript.txt` | `artifacts/calls/reschedule_existing_appointment-20260903-004740-81d06475/recording.mp3` |
| `cancel_existing_appointment-20260901-200804-71e773bd` | 153.2s | `artifacts/calls/cancel_existing_appointment-20260901-200804-71e773bd/realtime_transcript.txt` | `artifacts/calls/cancel_existing_appointment-20260901-200804-71e773bd/recording.mp3` |
| `cancel_existing_appointment-20260903-004054-db8b957d` | 153.2s | `artifacts/calls/cancel_existing_appointment-20260903-004054-db8b957d/realtime_transcript.txt` | `artifacts/calls/cancel_existing_appointment-20260903-004054-db8b957d/recording.mp3` |
| `medication_refill_request-20260901-203245-fefcba59` | 153.2s | `artifacts/calls/medication_refill_request-20260901-203245-fefcba59/realtime_transcript.txt` | `artifacts/calls/medication_refill_request-20260901-203245-fefcba59/recording.mp3` |
| `medication_refill_request-20260903-004347-47f4c510` | 153.2s | `artifacts/calls/medication_refill_request-20260903-004347-47f4c510/realtime_transcript.txt` | `artifacts/calls/medication_refill_request-20260903-004347-47f4c510/recording.mp3` |
| `office_hours_locations_insurance-20260902-040720-344f4a3e` | 85.9s | `artifacts/calls/office_hours_locations_insurance-20260902-040720-344f4a3e/realtime_transcript.txt` | `artifacts/calls/office_hours_locations_insurance-20260902-040720-344f4a3e/recording.mp3` |
| `office_hours_locations_insurance_variant-20260903-025244-50e87a82` | 153.2s | `artifacts/calls/office_hours_locations_insurance_variant-20260903-025244-50e87a82/realtime_transcript.txt` | `artifacts/calls/office_hours_locations_insurance_variant-20260903-025244-50e87a82/recording.mp3` |
| `unclear_request_edge_case-20260902-040902-7e7aa779` | 153.1s | `artifacts/calls/unclear_request_edge_case-20260902-040902-7e7aa779/realtime_transcript.txt` | `artifacts/calls/unclear_request_edge_case-20260902-040902-7e7aa779/recording.mp3` |
| `unclear_request_edge_case_variant-20260903-025536-ebc24ff7` | 146.9s | `artifacts/calls/unclear_request_edge_case_variant-20260903-025536-ebc24ff7/realtime_transcript.txt` | `artifacts/calls/unclear_request_edge_case_variant-20260903-025536-ebc24ff7/recording.mp3` |

## Known Limitations

- The bot needs Twilio and OpenAI credentials to place real calls.
- A public HTTPS tunnel is required so Twilio can reach the local FastAPI webhook and WebSocket bridge.
- Demo patients usually do not exist in the Pretty Good AI test system, so record lookup failure is treated as acceptable when the agent gathers identity details and routes to support.
- All simulated patients reuse one caller ID because the submission instructions require one calling number. This can affect caller-ID based lookup behavior.
- The evaluator is deterministic and conservative. It is meant to summarize evidence from transcripts, not replace human review of the recordings.

## Iteration Notes

Early Realtime calls showed turn-taking issues: the simulated patient sometimes started speaking before the Pretty Good AI greeting finished, and generated speech could be cut off. I adjusted the bridge to wait for the called agent to speak first, avoid Twilio `clear` messages, add a response delay, and track Twilio `mark` events before scheduling patient replies.

After listening to appointment calls, I noticed the patient sometimes gave timing preference without clearly saying the visit reason. I updated the prompt builder so the first substantive patient response includes the core request and key constraint or preference from the scenario, then reran the appointment scenario and confirmed the opening included lower back pain and next Tuesday afternoon.

I also iterated on evaluation quality after reviewing recordings. Caller-ID based references to Maria were originally flagged as possible identity bugs, but because all calls intentionally reuse one Twilio caller number, I downgraded this to an observation. A transcript-only date-of-birth mismatch was removed after audio review confirmed the agent said June 14 correctly.

## Development Checks

```powershell
python -m pgaibot doctor
python -m pytest
python -m ruff check .
python -m pgaibot report
```
