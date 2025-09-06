-- bin/lua/app/talker.lua
-- This overrides the original TALKER mod's talker.lua
package.path = package.path .. ";./bin/lua/?.lua;"
local event_store = require('domain.repo.event_store')
local logger = require('framework.logger')
local AI_request = require('infra.AI.requests')
local game_adapter = require('infra.game_adapter')
local config = require('interface.config')

-- NEW: TTS integration
local tts_handler = require('infra.tts.tts_handler')

local talker = {}

function talker.register_event(event, is_important)
    logger.info("talker.register_event")
    event_store:store_event(event)
    if should_someone_speak(event, is_important) then
        talker.generate_dialogue(event)
    end
end

local TEN_SECONDS_ms = 10 * 1000

function talker.generate_dialogue(event)
    logger.debug("Getting all events since " .. event.game_time_ms - TEN_SECONDS_ms)
    local recent_events = event_store:get_events_since(event.game_time_ms - TEN_SECONDS_ms)
    
    AI_request.generate_dialogue(recent_events, function(speaker_id, dialogue)
        logger.info("talker.generate_dialogue: dialogue generated for speaker_id: " .. speaker_id .. ", dialogue: " .. dialogue)
        
        -- Display dialogue as before
        game_adapter.display_dialogue(speaker_id, dialogue)
        
        -- NEW: TTS Integration with better error handling
        local function try_tts()
            logger.info("TTS: Getting character info for speaker %s", speaker_id)
            
            -- Try to get character info, but don't fail if it's missing
            local character = nil
            local status, result = pcall(function()
                return AI_request.get_character_by_id(speaker_id)
            end)
            
            if status then
                character = result
            else
                logger.warn("TTS: Error getting character info: %s", tostring(result))
            end
            
            if not character then
                logger.warn("TTS: No character info for speaker %s, using fallback", speaker_id)
                -- Let tts_handler create a fallback - pass nil character
                character = nil
            end
            
            logger.info("TTS: Requesting audio generation...")
            -- The tts_handler will check MCM settings internally and handle nil character
            tts_handler.request_tts(speaker_id, dialogue, character, function(success)
                if success then
                    logger.info("TTS: Audio is playing through Windows")
                else
                    logger.warn("TTS: Generation or playback failed")
                end
            end)
        end
        
        -- Try TTS in protected call to not break original functionality
        local status, err = pcall(try_tts)
        if not status then
            logger.error("TTS error: " .. tostring(err))
        end
        
        local dialogue_event = game_adapter.create_dialogue_event(speaker_id, dialogue)
        talker.register_event(dialogue_event)
    end)
end

function should_someone_speak(event, is_important)
    if #event.witnesses == 1 and game_adapter.is_player(event.witnesses[1].game_id) then
        logger.warn("Only witness is player, not generating dialogue")
        return false
    end
    return is_important or math.random() < config.BASE_DIALOGUE_CHANCE
end

function talker.set_game_adapter(adapter)
    game_adapter = adapter
end

return talker