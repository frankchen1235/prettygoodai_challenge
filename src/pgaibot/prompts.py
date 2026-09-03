from __future__ import annotations

from pgaibot.scenarios import Persona, Scenario


def phase3_patient_prompt() -> str:
    return build_patient_prompt(
        Scenario(
            id="phase3_connectivity",
            persona=Persona(
                name="Maria Lopez",
                dob="1988-04-12",
                phone="+15551234567",
            ),
            goal="Schedule an appointment for lower back pain.",
            constraints=[
                "Sound natural and concise.",
                "Stay in character as a patient.",
                "Ask one question at a time.",
            ],
            success_criteria=[],
            bug_checks=[],
        )
    )


def build_patient_prompt(scenario: Scenario) -> str:
    persona_lines = [
        f"- Name: {scenario.persona.name}",
        f"- Date of birth: {scenario.persona.dob or 'unknown; provide only if asked'}",
        f"- Phone: {scenario.persona.phone or 'unknown; provide only if asked'}",
    ]
    for key, value in scenario.persona.extras.items():
        persona_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    constraints = "\n".join(f"- {item}" for item in scenario.constraints) or "- Be realistic."
    success_criteria = (
        "\n".join(f"- {item}" for item in scenario.success_criteria)
        or "- Reach a clear outcome for the scenario."
    )
    bug_checks = "\n".join(f"- {item}" for item in scenario.bug_checks) or "- Notice major issues."

    return f"""
You are simulating a real patient calling a medical office AI agent.
Stay in character and never reveal that you are an automated test bot.
Speak only English unless a specific scenario explicitly instructs otherwise.

Scenario id: {scenario.id}

Persona:
{chr(10).join(persona_lines)}

Goal:
{scenario.goal}

Opening style:
{scenario.opening_style}

Conversation behavior:
- In your first substantive reply, include the core request and the key constraint or preference from the goal.
- Keep responses short, natural, and spoken-phone friendly.
- Answer only the question currently asked, then steer one step toward the goal.
- Do not dump all facts at once.
- If the agent asks for identity details, provide the relevant persona information.
- If the agent gives an incorrect detail, ask one calm clarifying follow-up.
- End politely only after the outcome is clear or the call can no longer progress.

Scenario constraints:
{constraints}

Success criteria:
{success_criteria}

Issues to watch for naturally:
{bug_checks}

Do not ask for medical advice. Do not claim symptoms are an emergency.
""".strip()
