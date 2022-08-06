from dataclasses import dataclass
from datetime import datetime
from util.enums import RecommendationType


@dataclass
class Recommendation:
    id: str
    timestamp: datetime
    recommendee: int
    recommender: int
    type: RecommendationType
    title: str
    url: str
