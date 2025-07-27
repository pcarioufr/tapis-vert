"""
Topic Generator Library
Provides random Top 10 topics for game rounds
"""

import random


# Static list of Top 10 topics
TOPICS = [
    "Top 10 des meilleurs films de tous les temps",
    "Top 10 des destinations de voyage à visiter absolument",
    "Top 10 des plats français les plus délicieux",
    "Top 10 des inventions qui ont changé le monde",
    "Top 10 des livres à lire avant de mourir",
]


def topic() -> str:
    """
    Returns a random topic for a new Top 10 round.
    
    Returns:
        str: A random topic from the predefined list
    """
    return random.choice(TOPICS)


# Export the topic function at package level
__all__ = ['topic', 'TOPICS']

