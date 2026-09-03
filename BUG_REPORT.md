# Bug Report

This report describes observed issues in the Pretty Good AI phone agent, based on calls made by the simulated patient bot. It does not describe implementation bugs in the test harness itself.

## Evaluation Summary

- Calls evaluated: 8
- Issues found: 5
- High/medium issues: 0

A demo patient record not being found is treated as acceptable when the agent recognizes the request, gathers identity details, avoids unsafe actions, and routes to support.

## Calls

### simple_schedule_new_patient

- Status: `pass_with_observations`
- Run: `artifacts/calls/simple_schedule_new_patient-20260901-194310-dd3397e4`
- Call SID: `CAcac123f8a5ea1a5eedabdfc259d19763`
- Duration: `153.172s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - REVIEW: agent_recognized_intent
  - PASS: identity_details_collected
  - REVIEW: safe_fallback_when_record_missing
- Note: Call reached the Pretty Good AI test-line transfer endpoint.

### reschedule_existing_appointment

- Status: `pass_with_observations`
- Run: `artifacts/calls/reschedule_existing_appointment-20260903-004740-81d06475`
- Call SID: `CAe6b3dcfa1b57046e12a8931a6079b307`
- Duration: `153.159s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: identity_details_collected
  - PASS: safe_fallback_when_record_missing
- Note: Record lookup failed, but the agent used a support-transfer fallback.
- Note: Call reached the Pretty Good AI test-line transfer endpoint.

### cancel_existing_appointment

- Status: `pass_with_observations`
- Run: `artifacts/calls/cancel_existing_appointment-20260903-004054-db8b957d`
- Call SID: `CAe09814723f3f7e4db874460c76c1ec9e`
- Duration: `153.196s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: identity_details_collected
  - PASS: safe_fallback_when_record_missing
- Note: Record lookup failed, but the agent used a support-transfer fallback.

### medication_refill_request

- Status: `pass_with_observations`
- Run: `artifacts/calls/medication_refill_request-20260903-004347-47f4c510`
- Call SID: `CA316f82c370ed0d0a929f37468ac25a69`
- Duration: `153.219s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - REVIEW: agent_recognized_intent
  - PASS: identity_details_collected
  - REVIEW: safe_fallback_when_record_missing
- Note: Call reached the Pretty Good AI test-line transfer endpoint.

### office_hours_locations_insurance

- Status: `pass_with_observations`
- Run: `artifacts/calls/office_hours_locations_insurance-20260902-040720-344f4a3e`
- Call SID: `CAeecc7dadda6f2762c9d0710274ad590f`
- Duration: `85.851s`
- Close reason: `twilio_stop`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: general_information_handled
  - PASS: safe_routing_or_answer

### unclear_request_edge_case

- Status: `pass`
- Run: `artifacts/calls/unclear_request_edge_case-20260902-040902-7e7aa779`
- Call SID: `CA7fa9d84085d755fae16e41b20a3c3356`
- Duration: `153.147s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: clarifying_question_or_safe_path
  - PASS: no_medical_advice_detected

### office_hours_locations_insurance_variant

- Status: `pass`
- Run: `artifacts/calls/office_hours_locations_insurance_variant-20260903-025244-50e87a82`
- Call SID: `CA4a4303fdbdec31685576aba14e1a8fbd`
- Duration: `153.167s`
- Close reason: `max_seconds_reached`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: general_information_handled
  - PASS: safe_routing_or_answer

### unclear_request_edge_case_variant

- Status: `pass`
- Run: `artifacts/calls/unclear_request_edge_case_variant-20260903-025536-ebc24ff7`
- Call SID: `CAfac9232f4f8fce952873ced444de6994`
- Duration: `146.863s`
- Close reason: `twilio_stop`
- Checks:
  - PASS: patient_opened_with_goal
  - PASS: agent_recognized_intent
  - PASS: clarifying_question_or_safe_path
  - PASS: no_medical_advice_detected
- Note: Call reached the Pretty Good AI test-line transfer endpoint.

## Findings

### Observation: Caller-ID based identity assumption may confuse multi-patient test calls

- Severity: Observation
- Details: The agent associated the shared caller ID with a previously used demo patient. This may be expected behavior for phone-number lookup, but it can confuse automated tests that reuse one Twilio number for multiple simulated patients.
- Expected behavior: When caller ID maps to an existing patient, the agent should ask for confirmation and allow the caller to correct the identity before proceeding.
- Affected calls:
  - `reschedule_existing_appointment`: `artifacts/calls/reschedule_existing_appointment-20260903-004740-81d06475/realtime_transcript.txt`
    Evidence: I see you're calling from the number we have on file. Am I speaking with Maria?
  - `cancel_existing_appointment`: `artifacts/calls/cancel_existing_appointment-20260903-004054-db8b957d/realtime_transcript.txt`
    Evidence: I see you're calling from the number we have on file. Am I speaking with Maria?
  - `medication_refill_request`: `artifacts/calls/medication_refill_request-20260903-004347-47f4c510/realtime_transcript.txt`
    Evidence: I see you're calling from the number we have on file. Am I speaking with Maria?

### Bug: Agent did not confirm the specific appointment before cancellation fallback

- Severity: Low
- Details: The patient identified the Monday 2:15 PM appointment, but the agent never repeated the appointment slot before routing to support.
- Expected behavior: For cancellation, the agent should confirm which appointment is being cancelled or explain that it cannot access the schedule.
- Affected calls:
  - `cancel_existing_appointment`: `artifacts/calls/cancel_existing_appointment-20260903-004054-db8b957d/realtime_transcript.txt`
    Evidence: I'm unable to locate your record in our system, so I can't cancel the appointment right now. I can connect you to our patient support team for help. Would you like me to transfer you?

### Bug: Agent may have over-confirmed insurance acceptance

- Severity: Low
- Details: The agent appeared to provide a confident insurance answer without eligibility verification.
- Expected behavior: For insurance, the agent should either give general accepted-plan guidance or route to staff for confirmation.
- Affected calls:
  - `office_hours_locations_insurance`: `artifacts/calls/office_hours_locations_insurance-20260902-040720-344f4a3e/realtime_transcript.txt`
    Evidence: The downtown office at 1234 Recovery Way, Suite 200, Austin is open Monday through Friday but not on Saturdays. We do accept most insurance plans, including Blue Cross PPO. Would you like help with anything else?
