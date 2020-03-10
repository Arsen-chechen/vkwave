from vkwave_api.methods import API
from vkwave_api.methods import APIOptionsRequestContext
from .http import AbstractHTTPClient
from .http import AIOHTTPClient
from typing import Union, Optional, List, cast, NewType, AsyncGenerator
from vkwave_types.objects import GroupsLongPollServer

Update = NewType("Update", dict)

class BotLongpollData:
    def __init__(self, group_id: int, wait: Optional[int] = None):
        self.key: Optional[str] = str()
        self.server: Optional[str] = str()
        self.ts: Optional[str] = str()
        self.wait: int = wait or 25
        self.group_id = group_id

        self._first_request: bool = False
        
    async def update_data(self, api: APIOptionsRequestContext) -> None:
        data = await api.groups.get_long_poll_server(group_id=self.group_id)
        response = data.response
        response = cast(GroupsLongPollServer, response)
        self.key = response.key
        self.server = response.server
        self.ts = response.ts

    async def handle_error(self, data: dict, client: AbstractHTTPClient, api: APIOptionsRequestContext) -> List[Update]:
        code = data["failed"]
        if code == 1:
            self.ts = data["ts"]
            return await self.get_updates(client, api)
        elif code == 2 or code == 3:
            await self.update_data(api)
            return await self.get_updates(client, api)
        return await self.get_updates(client, api)

    async def get_updates(self, http_client: AbstractHTTPClient, api: APIOptionsRequestContext) -> List[Update]:
        if not self._first_request:
            await self.update_data(api)
        data = await http_client.request("POST", f"{self.server}?act=a_check&key={self.key}&ts={self.ts}&wait={self.wait}")
        
        if "failed" in data:
            return await self.handle_error(data, http_client, api)

        return data["updates"]

class BotLongpoll:
    def __init__(self, api: APIOptionsRequestContext, bot_longpoll_data: BotLongpollData, http_client: Optional[AbstractHTTPClient] = None):

        self.api: APIOptionsRequestContext = api
        
        self.client = http_client or AIOHTTPClient()
        self.data = bot_longpoll_data

    async def get_updates(self) -> List[Update]:
        updates = await self.data.get_updates(self.client, self.api)
        return updates

    async def event_by_event(self) -> AsyncGenerator[Update, None]:
        updates: List[Update] = []
        while True:
            while not updates:
                updates = await self.get_updates()
            for update in updates:
                yield update