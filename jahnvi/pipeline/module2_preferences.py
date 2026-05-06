from jahnvi.schemas.user import PersonaQuestionAnswers


def get_questions() -> list[dict]:
    """
    Return the preference question bank shown on Screen 2.
    Questions should be simple enough to answer in under 2 minutes.

    Expected output:
        [
            {
                "id": "travel_style",
                "question": "How do you prefer to travel?",
                "type": "single_select",
                "options": ["Solo", "With a partner", "With family", "In a group"]
            },
            {
                "id": "food_interest",
                "question": "How important is local food to you?",
                "type": "scale",
                "min": 1,
                "max": 5,
                "labels": ["Not important", "Very important"]
            },
            ...
        ]
    """
    # TODO: return the full question bank list
    raise NotImplementedError


def parse_answers(raw: dict) -> PersonaQuestionAnswers:
    """
    Map raw form values from Screen 2 into a PersonaQuestionAnswers object.

    Expected input:
        {
            "food_interest": 5,
            "adventure_interest": 2,
            "culture_interest": 4,
            "nature_interest": 3,
            "nightlife_interest": 1,
            "budget_style": "mid_range",
            "travel_style": "couple",
            "pace_preference": "relaxed",
            "energy_level": 3
        }

    Expected output:
        PersonaQuestionAnswers(
            food_interest=5, adventure_interest=2, culture_interest=4,
            nature_interest=3, nightlife_interest=1, budget_style=BudgetStyle.mid_range,
            travel_style=TravelStyle.couple, pace_preference=PacePreference.relaxed,
            energy_level=3
        )
    """
    # TODO: validate ranges, map string values to enums, return model
    raise NotImplementedError
