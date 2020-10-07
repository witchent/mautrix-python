# Copyright (c) 2020 Tulir Asokan
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from typing import Dict, List

from mautrix.types import EventID

from .. import portal as po

from .handler import (HelpSection, HelpCacheKey, command_handler, CommandEvent, command_handlers,
                      SECTION_GENERAL)


@command_handler(help_section=SECTION_GENERAL,
                 help_text="Cancel an ongoing action.")
async def cancel(evt: CommandEvent) -> EventID:
    if evt.sender.command_status:
        action = evt.sender.command_status["action"]
        evt.sender.command_status = None
        return await evt.reply(f"{action} cancelled.")
    else:
        return await evt.reply("No ongoing command.")


@command_handler(help_section=SECTION_GENERAL,
                 help_text="Get the bridge version.")
async def version(evt: CommandEvent) -> None:
    if not evt.processor.bridge:
        await evt.reply("Bridge version unknown")
    else:
        await evt.reply(f"[{evt.processor.bridge.name}]({evt.processor.bridge.repo_url}) "
                        f"{evt.processor.bridge.markdown_version or evt.processor.bridge.version}")

@command_handler(needs_admin=True, needs_auth=False, name="set-pl",
                 help_section=SECTION_ADMIN,
                 help_args="<_level_> [_mxid_]",
                 help_text="Set a temporary power level without affecting the bridge.")
async def set_power_level(evt: CommandEvent) -> EventID:
    try:
        level = int(evt.args[0])
    except (KeyError, IndexError):
        return await evt.reply("**Usage:** `$cmdprefix+sp set-pl <level> [mxid]`")
    except ValueError:
        return await evt.reply("The level must be an integer.")
    portal = po.Portal.get_by_mxid(evt.room_id)
    if portal:
        levels = await portal.main_intent.get_power_levels(evt.room_id)
    else:
        levels = await evt.az.intent.get_power_levels(evt.room_id)
    mxid = evt.args[1] if len(evt.args) > 1 else evt.sender.mxid
    levels.users[mxid] = level
    try:
        if portal:
            return await portal.main_intent.set_power_levels(evt.room_id, levels)
        else:
            return await evt.az.intent.set_power_levels(evt.room_id, levels)
    except MatrixRequestError:
        evt.log.exception("Failed to set power level.")
        return await evt.reply("Failed to set power level.")

@command_handler()
async def unknown_command(evt: CommandEvent) -> EventID:
    return await evt.reply("Unknown command. Try `$cmdprefix+sp help` for help.")


help_cache: Dict[HelpCacheKey, str] = {}


async def _get_help_text(evt: CommandEvent) -> str:
    cache_key = await evt.get_help_key()
    if cache_key not in help_cache:
        help_sections: Dict[HelpSection, List[str]] = {}
        for handler in command_handlers.values():
            if handler.has_help and handler.has_permission(cache_key):
                help_sections.setdefault(handler.help_section, [])
                help_sections[handler.help_section].append(handler.help + "  ")
        help_sorted = sorted(help_sections.items(), key=lambda item: item[0].order)
        helps = ["#### {}\n{}\n".format(key.name, "\n".join(value)) for key, value in help_sorted]
        help_cache[cache_key] = "\n".join(helps)
    return help_cache[cache_key]


def _get_management_status(evt: CommandEvent) -> str:
    if evt.is_management:
        return "This is a management room: prefixing commands with `$cmdprefix` is not required."
    elif evt.is_portal:
        return ("**This is a portal room**: you must always prefix commands with `$cmdprefix`.\n"
                "Management commands will not be bridged.")
    return "**This is not a management room**: you must prefix commands with `$cmdprefix`."


@command_handler(name="help",
                 help_section=SECTION_GENERAL,
                 help_text="Show this help message.")
async def help_cmd(evt: CommandEvent) -> EventID:
    return await evt.reply(_get_management_status(evt) + "\n" + await _get_help_text(evt))
