#!/usr/bin/env python3
import asyncio

try:
    from amicus_bot import main

    # Run the main function of the bot
    asyncio.get_event_loop().run_until_complete(main.main())
except ImportError as e:
    print("Unable to import amicus_bot.main:", e)
