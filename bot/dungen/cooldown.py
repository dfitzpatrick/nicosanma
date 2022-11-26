from datetime import datetime, timezone, timedelta
from typing import NamedTuple, Dict, Optional, List

import discord
from discord.app_commands import CommandInvokeError
from discord import Interaction
from pydantic import BaseModel
import logging

log = logging.getLogger(__name__)




class HashableBaseModel(BaseModel):

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))


class Rule(HashableBaseModel):
    max_times: int
    duration_in_seconds: int



class Contract(BaseModel):
    rule: Rule
    user_id: int
    quantity: int = 0
    created_at: datetime

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.rule.duration_in_seconds)

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.is_expired or self.quantity <= self.rule.max_times

    def increment(self):
        self.quantity += 1

    def __str__(self):
        return f"Contract(rule={self.rule}, user_id={self.user_id} quantity={self.quantity}, created_at={self.created_at}, expires_at={self.expires_at}, is_expired={self.is_expired}, is_valid={self.is_valid})"


class DungenCooldownError(Exception):

    def __init__(self, contract: Contract, **kwargs):
        super(DungenCooldownError, self).__init__()
        self.contract = contract



DEFAULT_RULES = [
    Rule(max_times=300, duration_in_seconds=60*60),
    Rule(max_times=1000, duration_in_seconds=60*60*24)
]

class DungenCooldown:

    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules if rules is not None else DEFAULT_RULES
        self.users: Dict[int, Dict[Rule, Contract]] = {}

    def check(self, func):
        async def inner(itx: Interaction):
            user_id = itx.user.id
            for rule in self.rules:
                now = datetime.now(timezone.utc)
                if rule not in self.users.get(user_id, {}).keys():
                    contract = Contract(rule=rule, user_id=user_id, created_at=now)
                    self.users[user_id] = {}
                    self.users[user_id][rule] = contract
                contract = self.users[user_id][rule]
                if contract.is_expired:
                    # Reset
                    contract = Contract(rule=rule, user_id=user_id, created_at=now)
                    self.users[user_id][rule] = contract
                contract.increment()
                if contract.is_valid:
                    await func(itx)
                else:
                    embed = discord.Embed(
                        title="Uh Oh!",
                        description=f"You've exceeded your rate limit. You cannot use this command until the time listed below",
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="Expires at")
                    embed.timestamp = contract.expires_at
                    await itx.response.send_message(embed=embed, ephemeral=True)
        return inner







