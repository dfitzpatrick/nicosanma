import asyncio
from typing import Dict
import logging

log = logging.getLogger(__name__)


class TaskDebounce:

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.loop = asyncio.get_running_loop()

    def create_task(self, coro, name):
        existing_task = self.tasks.get(name)
        if existing_task:
            log.debug(f"Existing task {existing_task.get_name()} Found. Canceling for new task")
            existing_task.cancel()
        log.debug(f"New Task created {name}")
        task = asyncio.create_task(coro, name=name)
        self.tasks[name] = task

