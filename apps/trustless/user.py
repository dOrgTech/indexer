
from typing import List, Optional
from datetime import datetime, timezone
from apps.trustless.transaction import Transaction

class User:
    def __init__(self, 
                 address: str, 
                 native_earned: str, 
                 usdt_earned: str, 
                 native_spent: str, 
                 usdt_spent: str, 
                 projects_contracted: List[str], 
                 projects_arbitrated: List[str], 
                 projects_backed: List[str], 
                 projects_authored: List[str], 
                 last_active: datetime, 
                 name: Optional[str] = None, 
                 link: Optional[str] = None, 
                 about: Optional[str] = None):
        self.actions: List[Transaction] = []
        self.address = address
        self.native_earned = native_earned
        self.usdt_earned = usdt_earned
        self.native_spent = native_spent
        self.usdt_spent = usdt_spent
        self.name = name
        self.link = link
        self.about = about
        self.projects_contracted = projects_contracted
        self.projects_arbitrated = projects_arbitrated
        self.projects_authored = projects_authored
        self.projects_backed = projects_backed
        self.last_active = datetime.now(timezone.utc)

    def to_json(self) -> dict:
        return {
            'nativeEarned': self.native_earned,
            'link': self.link,
            'usdtEarned': self.usdt_earned,
            'nativeSpent': self.native_spent,
            'usdtSpent': self.usdt_spent,
            'name': self.name,
            'about': self.about,
            'projectsContracted': self.projects_contracted,
            'projectsArbitrated': self.projects_arbitrated,
            'projectsAuthored': self.projects_authored,
            'projectsBacked': self.projects_backed,
            'lastActive': self.last_active,
        }
