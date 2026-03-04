import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

import speech_recognition as sr
from openai import AzureOpenAI
import os

from gtts import gTTS
import pygame
import os
import time
import json


load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openaiClient = AzureOpenAI(
            azure_endpoint="endpoint",
            api_key="key",
            api_version="2025-01-01-preview",
        )

    # methods will go here

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using azure and available tools"""

        messages = [
            {
                "role": "system",
                "content": "Jsi Garfir. Sarkastický asistent a kouč, co pomůže se vším, ale jako by se mu nechtělo. Víš hodně o hře counter-strike 2, Sarkastický: Mistr suchého humoru. Svět vidí s dávkou skepticismu, málokdy ho něco skutečně nadchne (kromě jídla).Nesnášenlivý (vůči pondělí): Pondělí je jeho úhlavní nepřítel a symbol všeho špatného. Sebestředný: Je pevně přesvědčen, že se vesmír točí kolem něj. Odpovídá vcelku střučně souvislou větou nebo pár větami. Odpovídá stylem, jako by se mu nechtělo a je to pro něj fakt oprus.",
            },  # Osobnost
            {"role": "user", "content": f"{query}"},
        ]

        response = await self.session.list_tools()
        print("-Tools retrieved")
        available_tools = []
        for tool in response.tools:
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
            )
        print("-tools listed")
        # Azure API call
        azure_response = self.openaiClient.chat.completions.create(
            model="gpt-5-chat",
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
        )
        print("-Initial messsage created")
        message = azure_response.choices[0].message

        # Process response and handle tool calls
        final_text = []

        # Pokud Azure odpověděl rovnou textem, bez nastroje
        if message.content:
            final_text.append(message.content)

        # jestli si Azure vyžádal spuštění nástroje
        if message.tool_calls:
            # v puvodni zprave si rika o ty nastroje
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                final_text.append(
                    f"*(Garfir pouziva nastroj. Volám nástroj: {tool_name})*"
                )

                # Fyzické spuštění nástroje na MCP serveru
                result = await self.session.call_tool(tool_name, tool_args)

                # MCP vrací pole obsahu, extrahujeme z něj text
                tool_result_text = "\n".join(
                    [c.text for c in result.content if c.type == "text"]
                )

                # Přidáme výsledek z nástroje do historie zpráv (OpenAI vyžaduje roli 'tool')
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result_text,
                    }
                )

            # 4. Druhé volání Azure OpenAI (Garfire teď dostal data a vygeneruje sarkastickou odpověď)
            second_response = self.openaiClient.chat.completions.create(
                model="gpt-5-chat", messages=messages  # Stejný model
            )

            final_text.append(second_response.choices[0].message.content)

        return "\n\n".join(final_text)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    def _poslouchej_synchronne(self):
        """
        synchronous
        """
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("\n[Mikrofon] Kalibruji šum...")
            r.adjust_for_ambient_noise(source)
            print("[Mikrofon] Čekám na 'Garfir' nebo 'Garfield'...")

            while True:
                try:
                    audio = r.listen(source, phrase_time_limit=15)
                    text = r.recognize_google(audio, language="cs-CZ").lower()

                    if "garfir" in text or "garfield" in text:
                        print("\n👂 Garfir tě poslouchá (mluv)...")
                        audioNew = r.listen(source, timeout=None, phrase_time_limit=10)
                        textNew = r.recognize_google(audioNew, language="cs-CZ").lower()
                        return textNew
                except:
                    pass  # Ignoruj šum a chyby

    def mluv_synchronne(self, text):

        tts = gTTS(text=text, lang="cs")
        filename = "garfir_mluvi.mp3"
        tts.save(filename)

        # 2. Přehraje zvuk přes pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # Čeká, dokud Garfir nedomluví
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.quit()
        os.remove(filename)  # Uklidí po sobě
        # ZDE BY PAK PŘIŠLO TVOJE TEXT-TO-SPEECH (Hlasový výstup)

    async def voice_chat_loop(self):
        """
        Tohle nahradí původní textový 'chat_loop'.
        Tohle běží asynchronně a udržuje spojení s MCP serverem.
        """
        print("\n=== Garfir Voice Engine Spuštěn ===")

        while True:
            # Spustí synchronní poslouchání v jiném vlákně.
            # 'await' zajistí, že si kód počká na výsledek, ale nezmrazí MCP spojení.

            dotaz = await asyncio.to_thread(self._poslouchej_synchronne)
            # dotaz = "Najdi mi cs2 taktiku pro mapu Nuke."

            # Bezpečnostní pojistka pro vypnutí
            if "vypni se" in dotaz or "konec" in dotaz:
                print("Garfir: Konečně. Jdu spát.")
                break

            print(f"\n🗣️ Ty: {dotaz}")
            print("⚙️ Garfir přemýšlí (nebo tahá taktiky z databáze)...")

            try:
                # Zde se zavolá Azure OpenAI. Pokud bude potřeba nástroj,
                # proces_query si ho sám vyžádá od tvého FastMCP serveru.
                response = await self.process_query(dotaz)
                print(f"\n🐈 Garfir: {response} \n", type(response), len(response))
                self.mluv_synchronne(text=response)  # text to speech

            except Exception as e:
                print(f"Garfir se někde zasekl: {e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.voice_chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())

    """
    python garfirSetup.py "../server/mcpServer.py"
    """
